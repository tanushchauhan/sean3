"""Run against the installed endpoint and ROS libraries inside the test image."""

import runpy
from pathlib import Path
import sys
import unittest

import rclpy
from rclpy.executors import SingleThreadedExecutor

script = sys.argv.pop(1)
sys.path.insert(0, str(Path(script).parent))
Server = runpy.run_path(script)['LifecycleServer']


class EndpointCompatibilityTests(unittest.TestCase):
    def setUp(self):
        rclpy.init()
        self.server = Server()
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.server)

    def tearDown(self):
        self.server.destroy_nodes()
        self.executor.shutdown()
        rclpy.shutdown()

    def test_replacement_and_removal_release_topic_nodes(self):
        commands = self.server.syscommands
        for register, remove, table in (
                (commands.publish, commands.remove_publisher, self.server.publishers_table),
                (commands.subscribe, commands.remove_subscriber, self.server.subscribers_table)):
            previous = None
            for _ in range(3):
                register('/lifecycle_test', 'std_msgs/Bool')
                self.assertEqual(len(table), 1)
                if previous is not None:
                    self.assertIs(table['/lifecycle_test'], previous)
                previous = table['/lifecycle_test']
                self.assertEqual(len(self.executor.get_nodes()), 2)
            remove('/lifecycle_test')
            remove('/lifecycle_test')
            self.assertEqual(table, {})
            self.assertEqual(self.executor.get_nodes(), [self.server])

    def test_wire_removal_command_is_supported(self):
        self.server.syscommands.subscribe('/lifecycle_test', 'std_msgs/Bool')
        self.server.handle_syscommand('__remove_subscriber', b'{"topic":"/lifecycle_test"}\0')
        self.assertEqual(self.server.subscribers_table, {})
        self.assertEqual(self.executor.get_nodes(), [self.server])

    def test_unknown_command_does_not_crash_client(self):
        errors = []
        self.server.send_unity_error = errors.append
        self.server.handle_syscommand('__not_supported', b'{}\0')
        self.assertEqual(len(errors), 1)


class EndpointProcessTests(unittest.TestCase):
    def test_interrupt_and_terminate_exit_without_a_forced_kill(self):
        import signal
        import socket
        import subprocess
        import time
        for interrupt in [signal.SIGINT, signal.SIGTERM]:
            with self.subTest(signal=interrupt):
                with socket.socket() as reservation:
                    reservation.bind(('127.0.0.1', 0))
                    port = reservation.getsockname()[1]
                process = subprocess.Popen([sys.executable, script, '--ros-args', '-p',
                    'ROS_IP:=127.0.0.1', '-p', f'ROS_TCP_PORT:={port}'],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                conn = None
                try:
                    deadline = time.monotonic()+10
                    while True:
                        try:
                            conn = socket.create_connection(('127.0.0.1', port), timeout=1)
                            break
                        except OSError:
                            if time.monotonic() > deadline or process.poll() is not None:
                                self.fail('Endpoint process did not start')
                            time.sleep(.05)
                    conn.settimeout(3)
                    self.assertEqual(EndpointTransportTests.read(conn)[0], '__handshake')
                    conn.sendall(EndpointTransportTests.wire('__disconnect'))
                    conn.shutdown(socket.SHUT_WR)
                    self.assertEqual(conn.recv(1), b'')
                    conn.close()
                    process.send_signal(interrupt)
                    output = process.communicate(timeout=3)[0].decode()
                    self.assertEqual(process.returncode, 0, output)
                    self.assertNotIn('[ERROR]', output)
                    self.assertNotIn('Traceback', output)
                finally:
                    if conn is not None:
                        conn.close()
                    if process.poll() is None:
                        process.kill()
                        process.communicate()


class EndpointTransportTests(unittest.TestCase):
    def setUp(self):
        import socket
        rclpy.init()
        self.server = Server()
        self.server.tcp_port = 0
        self.infos, self.warnings, self.errors = [], [], []
        self.server.loginfo = self.infos.append
        self.server.logwarn = self.warnings.append
        self.server.logerr = self.errors.append
        self.server.start()
        self.port = self.server.listener.getsockname()[1]

    def tearDown(self):
        self.server.stop()
        self.assertFalse(self.server.listener_thread.is_alive())
        if self.server.active_client is not None:
            self.assertFalse(self.server.active_client.is_alive())
        self.server.destroy_nodes()
        rclpy.shutdown()

    def connect(self):
        import socket
        conn = socket.create_connection(('127.0.0.1', self.port), timeout=3)
        self.assertEqual(self.read(conn)[0], '__handshake')
        return conn

    @staticmethod
    def wire(topic, payload=b'{}\0'):
        import struct
        name = topic.encode()
        return struct.pack('<I', len(name))+name+struct.pack('<I', len(payload))+payload

    @staticmethod
    def read(conn):
        import struct
        def exact(n):
            result = b''
            while len(result) < n:
                chunk = conn.recv(n-len(result))
                if not chunk:
                    raise EOFError()
                result += chunk
            return result
        n = struct.unpack('<I', exact(4))[0]
        topic = exact(n).decode().rstrip('\0')
        n = struct.unpack('<I', exact(4))[0]
        return topic, exact(n)

    def close_gracefully(self, conn):
        import socket
        conn.sendall(self.wire('__disconnect'))
        conn.shutdown(socket.SHUT_WR)
        try:
            while True:
                self.read(conn)
        except EOFError:
            pass
        conn.close()
        self.server.active_client.join(timeout=3)
        self.assertFalse(self.server.active_client.is_alive())

    def test_twenty_sessions_drain_traffic_and_release_sender_threads(self):
        import threading
        from std_msgs.msg import Bool
        halt = threading.Event()
        def traffic():
            while not halt.wait(.001):
                self.server.send_unity_message('/echo', Bool(data=True))
        worker = threading.Thread(target=traffic)
        worker.start()
        try:
            for _ in range(20):
                conn = self.connect()
                conn.sendall(self.wire('__publish', b'{"topic":"/transport_test","message_name":"std_msgs/Bool"}\0'))
                self.close_gracefully(conn)
                self.assertIsNone(self.server.unity_tcp_sender.queue)
                self.assertFalse(any(t.name == 'sean-sender' for t in threading.enumerate()))
            self.assertEqual(len(self.server.publishers_table), 1)
            self.assertEqual(sum('Graceful Unity disconnect' in s for s in self.infos), 20)
            self.assertEqual(self.warnings, [])
            self.assertEqual(self.errors, [])
        finally:
            halt.set()
            worker.join(timeout=3)

    def test_partial_frame_remains_an_error(self):
        import socket
        conn = self.connect()
        conn.sendall(b'\x04\x00')
        conn.shutdown(socket.SHUT_WR)
        self.assertEqual(conn.recv(1), b'')
        conn.close()
        self.server.active_client.join(timeout=3)
        self.assertTrue(any('Truncated' in s for s in self.errors))

    def test_unannounced_eof_is_visible(self):
        import socket
        conn = self.connect()
        conn.shutdown(socket.SHUT_WR)
        self.assertEqual(conn.recv(1), b'')
        conn.close()
        self.server.active_client.join(timeout=3)
        self.assertTrue(any('Unannounced Unity disconnect' in s for s in self.warnings))

    def test_replacement_joins_old_session_before_handshake(self):
        old = self.connect()
        new = self.connect()
        self.assertEqual(old.recv(1), b'')
        old.close()
        self.close_gracefully(new)
        self.assertEqual(sum('Replacing a still-active' in s for s in self.warnings), 1)
        self.assertEqual(self.errors, [])

    def test_service_response_and_disconnect_release_pending_requests(self):
        import json
        import threading
        from std_srvs.srv import SetBool
        from rclpy.serialization import serialize_message
        for respond in [True, False]:
            conn = self.connect()
            results, errors = [], []
            def request():
                try:
                    results.append(self.server.send_unity_service('/service', SetBool, SetBool.Request(data=True)))
                except ConnectionError as error:
                    errors.append(str(error))
            worker = threading.Thread(target=request, daemon=True)
            worker.start()
            command, params = self.read(conn)
            self.assertEqual(command, '__request')
            self.assertEqual(self.read(conn)[0], '/service')
            if respond:
                conn.sendall(self.wire('__response', params+b'\0') + self.wire('/service',
                    serialize_message(SetBool.Response(success=True, message='done'))))
                worker.join(timeout=3)
                self.assertFalse(worker.is_alive())
                self.assertTrue(results[0].success)
            self.close_gracefully(conn)
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            if not respond:
                self.assertEqual(len(errors), 1)
            self.assertFalse(self.server.unity_tcp_sender.services_waiting)
        self.assertEqual(self.errors, [])

    def test_server_stop_releases_idle_client_and_listening_port(self):
        import socket
        conn = self.connect()
        self.server.stop()
        self.assertEqual(conn.recv(1), b'')
        conn.close()
        with socket.socket() as rebound:
            rebound.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            rebound.bind(('127.0.0.1', self.port))
        self.assertEqual(self.errors, [])


if __name__ == '__main__':
    unittest.main()

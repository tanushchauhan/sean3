"""Run against the installed endpoint and ROS libraries inside the test image."""

import runpy
import sys
import unittest

import rclpy
from rclpy.executors import SingleThreadedExecutor

Server = runpy.run_path(sys.argv.pop(1))['LifecycleServer']


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


if __name__ == '__main__':
    unittest.main()

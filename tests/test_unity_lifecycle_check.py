import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('unity_lifecycle', Path(__file__).with_name('unity_lifecycle_check.py'))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class LifecycleResourceTests(unittest.TestCase):
    def test_each_resource_budget_is_enforced(self):
        baseline = {'rss_kib': 1000, 'threads': 12, 'fds': 20}
        for key, increment in [('rss_kib', 128 * 1024 + 1), ('threads', 5), ('fds', 9)]:
            current = dict(baseline)
            current[key] += increment
            with self.subTest(key=key), self.assertRaisesRegex(RuntimeError, 'resource growth'):
                check.check_growth(baseline, current, 128)

    def test_stable_resources_and_released_memory_pass(self):
        self.assertEqual(check.check_growth({'rss_kib': 2000, 'threads': 12, 'fds': 20},
                                           {'rss_kib': 1000, 'threads': 12, 'fds': 20}, 128),
                         {'rss_kib': -1000, 'threads': 0, 'fds': 0})

    def test_missing_player_cannot_silently_skip_resource_check(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(RuntimeError, 'Expected one player'):
                check.process_resources(root, '/player')

    def test_multiple_players_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            for pid in ('123', '456'):
                entry = Path(root) / pid
                entry.mkdir()
                (entry / 'exe').symlink_to('/player')
                (entry / 'status').write_text('VmRSS:\t2000 kB\nThreads:\t10\n')
                (entry / 'fd').mkdir()
            with self.assertRaisesRegex(RuntimeError, 'found 2'):
                check.process_resources(root, '/player')



class LifecycleLogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('lifecycle_logs', Path(__file__).with_name('lifecycle_log_check.py'))
        cls.logs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.logs)

    def test_endpoint_eof_and_closed_socket_errors_fail(self):
        report = self.logs.summarize('', '[ERROR] Exception: No more data available')
        self.assertFalse(report['passed'])
        self.assertEqual(report['endpoint_logger_warnings'], 0)
        self.assertEqual(report['endpoint_disconnect_eof'], 1)
        report = self.logs.summarize('', '[ERROR] Exception [Errno 9] Bad file descriptor\n'
                                    'Publisher already registered for provided node name')
        self.assertFalse(report['passed'])
        self.assertEqual(report['endpoint_closed_socket_writes'], 1)
        self.assertEqual(report['endpoint_logger_warnings'], 1)

    def test_announced_close_is_clean_but_faults_stay_visible(self):
        clean = 'Connection from host\nGraceful Unity disconnect from host\nDisconnected from host'
        report = self.logs.summarize('', clean)
        self.assertTrue(report['passed'])
        self.assertEqual(report['endpoint_graceful_disconnects'], 1)
        for message in ['Unannounced Unity disconnect', 'Replacing a still-active Unity connection',
                        '[ERROR] Unexpected Unity receive failure: Truncated frame']:
            self.assertFalse(self.logs.summarize('', message)['passed'])
        for message in ['ROS graceful disconnect timed out.', 'ROS connection worker did not stop',
                        'Native Crash Reporting', 'XIO: fatal IO error']:
            self.assertFalse(self.logs.summarize(message, '')['passed'])

    def test_each_player_lifecycle_error_fails(self):
        for message in ('HUDPanel already contains a header', 'Queue full!',
                        'Connection to localhost failed - System.IO.IOException',
                        'Reader 101 exception!', 'MissingReferenceException'):
            with self.subTest(message=message):
                self.assertFalse(self.logs.summarize(message, '')['passed'])

    def test_reset_socket_error_is_reported_as_unclean_transport(self):
        report = self.logs.summarize('Connection failed - System.IO.IOException: Unable to write '
                                    'data to the transport connection: Connection reset by peer.', '')
        self.assertFalse(report['passed'])
        self.assertFalse(report['transport_clean'])
        self.assertEqual(report['reset_by_peer_writes'], 1)

    def test_display_error_in_console_fails_the_completed_run(self):
        import json
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'player.log').write_text('')
            (root / 'player-console.log').write_text('')
            (root / 'endpoint.log').write_text('Connection from host\nGraceful Unity disconnect from host\nDisconnected from host')
            (root / 'endpoint-exit.json').write_text(json.dumps(dict(Running=False, OOMKilled=False, ExitCode=0)))
            (root / 'player-wrapper-exit.txt').write_text('0')
            (root / 'player-forced-pids.txt').write_text('')
            command = [sys.executable, str(Path(__file__).with_name('lifecycle_log_check.py')), str(root)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            (root / 'player-console.log').write_text('XIO: fatal IO error')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)
            self.assertEqual(json.loads((root / 'lifecycle-logs.json').read_text())['display_errors'], 1)

    def test_unexpected_endpoint_errors_fail(self):
        for message in ('[ERROR] Socket failed', 'Traceback (most recent call last)'):
            with self.subTest(message=message):
                self.assertFalse(self.logs.summarize('', message)['passed'])


if __name__ == '__main__':
    unittest.main()

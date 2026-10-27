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

    def test_orderly_endpoint_eof_remains_visible(self):
        report = self.logs.summarize('', '[ERROR] Exception: No more data available')
        self.assertTrue(report['passed'])
        self.assertEqual(report['endpoint_logger_warnings'], 0)
        self.assertEqual(report['endpoint_disconnect_eof'], 1)
        report = self.logs.summarize('', '[ERROR] Exception [Errno 9] Bad file descriptor\n'
                                    'Publisher already registered for provided node name')
        self.assertTrue(report['passed'])
        self.assertEqual(report['endpoint_closed_socket_writes'], 1)
        self.assertEqual(report['endpoint_logger_warnings'], 1)

    def test_each_player_lifecycle_error_fails(self):
        for message in ('HUDPanel already contains a header', 'Queue full!',
                        'Connection to localhost failed - System.IO.IOException',
                        'Reader 101 exception!', 'MissingReferenceException'):
            with self.subTest(message=message):
                self.assertFalse(self.logs.summarize(message, '')['passed'])

    def test_reset_socket_error_is_reported_as_unclean_transport(self):
        report = self.logs.summarize('Connection failed - System.IO.IOException: Unable to write '
                                    'data to the transport connection: Connection reset by peer.', '')
        self.assertTrue(report['passed'])
        self.assertFalse(report['transport_clean'])
        self.assertEqual(report['reset_by_peer_writes'], 1)

    def test_unexpected_endpoint_errors_fail(self):
        for message in ('[ERROR] Socket failed', 'Traceback (most recent call last)'):
            with self.subTest(message=message):
                self.assertFalse(self.logs.summarize('', message)['passed'])


if __name__ == '__main__':
    unittest.main()

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('lifecycle_check', HERE / 'nav2_lifecycle_check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class LifecycleCheckTests(unittest.TestCase):
    def test_failed_build_stops_before_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            colcon = root / 'colcon'
            colcon.write_text('#!/bin/sh\nexit 42\n')
            colcon.chmod(0o755)
            with patch.dict('os.environ', {'PATH': str(root) + ':' + check.os.environ['PATH']}):
                result = subprocess.run(['bash', str(HERE / 'nav2_lifecycle_check.sh'), directory])
            self.assertEqual(result.returncode, 42)

    def test_all_nodes_must_be_active(self):
        result = subprocess.CompletedProcess([], 0, 'inactive [2]\n', '')
        with patch.object(check.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'did not become active'):
                check.wait_for_active([], 0.01)

    def test_unresponsive_query_is_a_failure(self):
        with patch.object(check.subprocess, 'run', side_effect=subprocess.TimeoutExpired([], 1)):
            with self.assertRaisesRegex(RuntimeError, 'did not become active'):
                check.wait_for_active([], 0.01)

    def test_exit_during_startup_is_a_failure(self):
        process = Mock()
        process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, 'exited during startup'):
            check.wait_for_active([process], 1)

    def test_success_checks_every_node(self):
        result = subprocess.CompletedProcess([], 0, 'active [3]\n', '')
        with patch.object(check.subprocess, 'run', return_value=result) as run:
            check.wait_for_active([], 1)
        self.assertEqual({call.args[0][-1] for call in run.call_args_list},
                         {'/' + node for node in check.NODES})

    def test_cleanup_signals_owned_process_groups(self):
        process = Mock(pid=12345)
        with patch.object(check.os, 'killpg') as kill:
            check.stop_processes([process])
        self.assertEqual(kill.call_args_list[0].args, (12345, check.signal.SIGTERM))
        self.assertEqual(kill.call_args_list[1].args, (12345, check.signal.SIGKILL))
        self.assertTrue(process.wait.called)


if __name__ == '__main__':
    unittest.main()

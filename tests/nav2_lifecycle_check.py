"""Check Nav2 startup with synthetic clock and TF inputs, without Unity."""

import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time


NODES = (
    'map_server', 'controller_server', 'smoother_server', 'planner_server',
    'behavior_server', 'bt_navigator', 'waypoint_follower', 'velocity_smoother',
)


def publish_clock():
    import rclpy
    from rosgraph_msgs.msg import Clock

    rclpy.init()
    node = rclpy.create_node('lifecycle_test_clock')
    publisher = node.create_publisher(Clock, '/clock', 10)
    start = time.monotonic()

    def tick():
        nanoseconds = int((time.monotonic() - start) * 1_000_000_000)
        message = Clock()
        message.clock.sec, message.clock.nanosec = divmod(nanoseconds, 1_000_000_000)
        publisher.publish(message)

    node.create_timer(0.02, tick)
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def wait_for_active(processes, timeout):
    deadline = time.monotonic() + timeout
    states = {}
    while time.monotonic() < deadline:
        for process in processes:
            if process.poll() is not None:
                raise RuntimeError(f'Process exited during startup: {process.args}')
        for node in NODES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                result = subprocess.run(
                    ['ros2', 'lifecycle', 'get', '/' + node],
                    capture_output=True, text=True, timeout=min(3, remaining),
                )
                states[node] = result.stdout.strip() if result.returncode == 0 else 'unavailable'
            except subprocess.TimeoutExpired:
                states[node] = 'unavailable'
        if all(states.get(node) == 'active [3]' for node in NODES):
            return
        time.sleep(min(0.2, max(0, deadline - time.monotonic())))
    raise RuntimeError(f'Nav2 did not become active: {states}')


def stop_processes(processes):
    # Each child owns a process group, including nodes spawned by ros2 launch.
    for process in reversed(processes):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 5
    for process in reversed(processes):
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    log_dir = Path(tempfile.mkdtemp(prefix='sean3-nav2-', dir=os.environ.get('SEAN_TEST_LOG_DIR')))
    print(f'Logs: {log_dir}', flush=True)
    commands = [
        [sys.executable, __file__, '--clock'],
        ['ros2', 'run', 'tf2_ros', 'static_transform_publisher',
         '--frame-id', 'map', '--child-frame-id', 'base_link'],
        ['ros2', 'launch', 'social_sim_ros', 'nav2_jackal.launch.py',
         'scene:=' + os.environ.get('SEAN_SCENE', 'lab')],
    ]
    processes = []
    logs = []
    try:
        for index, command in enumerate(commands):
            log = (log_dir / f'{index}.log').open('w')
            logs.append(log)
            processes.append(subprocess.Popen(
                command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            ))
        wait_for_active(processes, float(os.environ.get('SEAN_STARTUP_TIMEOUT', '60')))
        for process in processes:
            if process.poll() is not None:
                raise RuntimeError(f'Process exited: {process.args}')
        for path in log_dir.glob('*.log'):
            if any(token in path.read_text() for token in ('[ERROR]', '[FATAL]')):
                raise RuntimeError(f'Startup errors in {path}')
        if '--check-commands' in sys.argv:
            from nav2_command_check import check_commands
            check_commands()
        print('All Nav2 lifecycle nodes are active. Unity navigation is not tested.')
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    finally:
        stop_processes(processes)
        for log in logs:
            log.close()


if __name__ == '__main__':
    if sys.argv[1:] == ['--clock']:
        publish_clock()
    else:
        sys.exit(main())

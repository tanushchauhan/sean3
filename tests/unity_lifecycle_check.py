"""Bounded live reset/reload checks; no Nav2 or camera-rendering claim."""

import argparse
import json
import math
from pathlib import Path
import time


def process_resources(proc_root, executable, command=False):
    matches = []
    for entry in Path(proc_root).iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if command:
                arguments = (entry / 'cmdline').read_bytes().decode().split('\0')
                if not any(Path(arg).name == executable for arg in arguments):
                    continue
            elif str((entry / 'exe').readlink()) != executable:
                continue
            status = dict(line.split(':', 1) for line in (entry / 'status').read_text().splitlines())
            matches.append({'pid': int(entry.name), 'rss_kib': int(status['VmRSS'].split()[0]),
                            'threads': int(status['Threads']), 'fds': len(list((entry / 'fd').iterdir()))})
        except (OSError, KeyError):
            continue
    if len(matches) != 1:
        raise RuntimeError(f'Expected one player/endpoint process for {executable}, found {len(matches)}')
    return matches[0]


def check_growth(baseline, current, rss_limit_mib):
    limits = {'rss_kib': rss_limit_mib * 1024, 'threads': 4, 'fds': 8}
    growth = {key: current[key] - baseline[key] for key in limits}
    for key, limit in limits.items():
        if growth[key] > limit:
            raise RuntimeError(f'Player resource growth exceeded {key} budget: {growth}')
    return growth


def main():
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import LaserScan
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import Bool
    from social_sim_ros.msg import TrialInfo

    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--resources', required=True)
    parser.add_argument('--pairs', type=int, default=6)
    parser.add_argument('--rss-growth-mib', type=int, default=128)
    args = parser.parse_args()
    if not 2 <= args.pairs <= 20 or args.rss_growth_mib <= 0:
        parser.error('pairs must be 2..20 and RSS budget must be positive')
    rclpy.init()
    node = rclpy.create_node('sean_lifecycle_check')
    latest, received, counts = {}, {}, {}
    report = {'passed': False, 'pairs': args.pairs, 'stages': [], 'clock_regressions': [],
              'limits': {'rss_growth_mib': args.rss_growth_mib, 'thread_growth': 4, 'fd_growth': 8}}
    last_clock = None

    def stamp(value):
        return value.sec + value.nanosec * 1e-9

    def receive(key, message):
        nonlocal last_clock
        if key == 'clock':
            now = stamp(message.clock)
            if last_clock is not None and now < last_clock:
                report['clock_regressions'].append([last_clock, now])
            last_clock = now
        latest[key] = message
        received[key] = time.monotonic()
        counts[key] = counts.get(key, 0) + 1

    for key, topic, cls in [('odom', '/robot_odom', Odometry), ('scan', '/laser_raycast', LaserScan),
                            ('clock', '/clock', Clock), ('trial', '/social_sim/metrics', TrialInfo)]:
        node.create_subscription(cls, topic, lambda msg, key=key: receive(key, msg), qos_profile_sensor_data)
    task = node.create_publisher(Bool, '/social_sim/control/task/new', 10)
    scene = node.create_publisher(Bool, '/social_sim/control/scene/reload', 10)
    command = node.create_publisher(Twist, '/mobile_base_controller/cmd_vel', 10)

    def wait(predicate, seconds, description):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if report['clock_regressions']:
                raise RuntimeError('Clock moved backwards')
            if predicate():
                return
        raise RuntimeError('Timed out: ' + description)

    def observe(seconds):
        deadline = time.monotonic() + seconds
        wait(lambda: time.monotonic() >= deadline, seconds + 1, 'observation window')

    def fresh(after=0):
        if not all(received.get(key, 0) > after and time.monotonic() - received.get(key, 0) < 2
                   for key in ('clock', 'scan', 'odom')):
            return False
        clock = stamp(latest['clock'].clock)
        return (all(-0.1 <= clock - stamp(latest[key].header.stamp) < 1 for key in ('scan', 'odom'))
                and latest['odom'].header.frame_id == 'map'
                and latest['odom'].child_frame_id == 'base_link')

    def graph():
        return {topic: {'publishers': node.count_publishers(topic), 'subscribers': node.count_subscribers(topic)}
                for topic in ('/clock', '/robot_odom', '/laser_raycast', '/social_sim/control/task/new',
                              '/social_sim/control/scene/reload', '/mobile_base_controller/cmd_vel')}

    try:
        wait(lambda: fresh() and 'trial' in latest and command.get_subscription_count() == 1,
             60, 'startup sensors and command subscriber')
        observe(3)
        initial_graph = graph()
        baseline = None
        endpoint_baseline = None
        for index in range(args.pairs * 2):
            kind = 'task' if index % 2 == 0 else 'scene'
            # Extend no command timeout: test that reset clears a recently accepted command.
            movement = Twist()
            movement.angular.z = 0.5
            command.publish(movement)
            wait(lambda: abs(latest['odom'].twist.twist.angular.z) > 0.1, 3, 'command reaches robot')
            previous_trial = latest['trial'].trial_number
            before_clock = last_clock
            before_counts = counts.copy()
            started = time.monotonic()
            (task if kind == 'task' else scene).publish(Bool(data=True))
            wait(lambda: received.get('trial', 0) > started and
                 (latest['trial'].trial_number == previous_trial + 1 if kind == 'task'
                  else latest['trial'].trial_number == 1), 45, kind + ' acknowledgement')
            acknowledged = time.monotonic()
            wait(lambda: fresh(acknowledged), 30, 'new sensors after acknowledgement')
            # Skip teleport-derived odometry, then check stationary state without sending zero.
            observe(0.3)
            wait(lambda: math.hypot(latest['odom'].twist.twist.linear.x,
                                   latest['odom'].twist.twist.linear.y) < 0.02 and
                 abs(latest['odom'].twist.twist.angular.z) < 0.02, 3, 'stationary after reset')
            position = latest['odom'].pose.pose.position
            x, y = position.x, position.y
            observe(2)
            if not fresh(acknowledged):
                raise RuntimeError('Sensors did not remain fresh')
            position = latest['odom'].pose.pose.position
            drift = math.hypot(position.x - x, position.y - y)
            if drift > 0.03:
                raise RuntimeError(f'Robot drift after reset: {drift}')
            if graph() != initial_graph:
                raise RuntimeError(f'ROS registrations changed: {graph()} != {initial_graph}')
            if latest['trial'].trial_number != (previous_trial + 1 if kind == 'task' else 1):
                raise RuntimeError('One reset request produced multiple tasks')
            elapsed_wall = time.monotonic() - started
            elapsed_clock = last_clock - before_clock
            if not 0 <= elapsed_clock <= elapsed_wall + 2:
                raise RuntimeError('Clock jumped during reset')
            resources = json.loads(Path(args.resources).read_text())
            if time.time() - resources['sampled_at'] > 3:
                raise RuntimeError('Player resource sample is stale')
            endpoint = process_resources('/proc', 'sean_tcp_endpoint', command=True)
            stage = {'kind': kind, 'index': index, 'clock_seconds': elapsed_clock,
                     'wall_seconds': elapsed_wall, 'drift_m': drift, 'resources': resources,
                     'endpoint_resources': endpoint,
                     'sensor_counts': {key: counts[key] - before_counts.get(key, 0) for key in counts},
                     'graph': graph()}
            report['stages'].append(stage)
            # First pair warms scene allocations before applying a fixed, reported budget.
            if index == 1:
                baseline = resources
                endpoint_baseline = endpoint
            elif baseline is not None:
                stage['growth'] = check_growth(baseline, resources, args.rss_growth_mib)
                stage['endpoint_growth'] = check_growth(endpoint_baseline, endpoint, args.rss_growth_mib)
            print(json.dumps(stage), flush=True)
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        command.publish(Twist())
        report['sensor_counts'] = counts
        Path(args.output).write_text(json.dumps(report, indent=2) + '\n')
        node.destroy_node()
        rclpy.shutdown()


def sample_player():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample-player', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    while True:
        try:
            resources = process_resources('/proc', args.sample_player)
            resources['sampled_at'] = time.time()
            temporary = output.with_suffix('.tmp')
            temporary.write_text(json.dumps(resources))
            temporary.replace(output)
        except RuntimeError:
            pass  # Startup and shutdown can temporarily have no matching player.
        time.sleep(0.5)


if __name__ == '__main__':
    import sys
    if '--sample-player' in sys.argv:
        sample_player()
    else:
        main()

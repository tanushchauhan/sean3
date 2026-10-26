"""Run a short Nav2 goal against a live Unity player and matching map."""

import argparse
import json
import math
from pathlib import Path
import signal
import subprocess
import time
import os

import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, OccupancyGrid
from nav2_msgs.action import NavigateToPose
from lifecycle_msgs.srv import GetState
from sensor_msgs.msg import LaserScan
from rosgraph_msgs.msg import Clock
from std_msgs.msg import Bool
from social_sim_ros.msg import TrialInfo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', default='warehouse')
    parser.add_argument('--output', default='/tmp/unity-navigation.json')
    parser.add_argument('--cycles', type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('sean_navigation_check', parameter_overrides=[Parameter('use_sim_time', value=True)])
    latest = {}
    received = {}
    counts = {}

    def receive(key, message):
        latest[key] = message
        received[key] = time.monotonic()
        counts[key] = counts.get(key, 0) + 1

    for key, topic, cls in [('odom', '/robot_odom', Odometry), ('scan', '/laser_raycast', LaserScan),
                             ('clock', '/clock', Clock), ('trial', '/social_sim/metrics', TrialInfo)]:
        node.create_subscription(cls, topic, lambda msg, key=key: receive(key, msg), qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/map', lambda msg: receive('map', msg),
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    reset = node.create_publisher(Bool, '/social_sim/control/task/new', 10)
    reload = node.create_publisher(Bool, '/social_sim/control/scene/reload', 10)
    client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    report = {'scene': args.scene, 'episodes': [], 'resets': []}
    process = None

    def wait(predicate, seconds, description):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if predicate():
                return
        raise RuntimeError('Timed out: ' + description)

    def fresh():
        if not all(time.monotonic() - received.get(key, 0) < 2 for key in ('odom', 'scan', 'clock')):
            return False
        clock = latest['clock'].clock.sec + latest['clock'].clock.nanosec * 1e-9
        for key in ('odom', 'scan'):
            stamp = latest[key].header.stamp
            if not -0.1 <= clock - (stamp.sec + stamp.nanosec * 1e-9) < 1:
                return False
        return latest['odom'].header.frame_id == 'map' and latest['odom'].child_frame_id == 'base_link'

    def free(x, y, radius=0.6):
        grid = latest['map']
        resolution = grid.info.resolution
        cx = int((x - grid.info.origin.position.x) / resolution)
        cy = int((y - grid.info.origin.position.y) / resolution)
        cells = math.ceil(radius / resolution)
        for dy in range(-cells, cells + 1):
            for dx in range(-cells, cells + 1):
                if dx * dx + dy * dy > cells * cells:
                    continue
                ix, iy = cx + dx, cy + dy
                if not (0 <= ix < grid.info.width and 0 <= iy < grid.info.height):
                    return False
                if grid.data[iy * grid.info.width + ix] != 0:
                    return False
        return True

    try:
        wait(lambda: fresh() and 'trial' in latest, 45, 'live Unity sensors and initial task')
        for cycle in range(args.cycles):
            if cycle:
                reset_started = time.monotonic()
                clock_before = latest['clock'].clock.sec + latest['clock'].clock.nanosec * 1e-9
                previous = latest.get('trial')
                previous_number = previous.trial_number if previous else None
                publisher = reset if cycle == 1 else reload
                wait(lambda: publisher.get_subscription_count() > 0, 10, 'reset subscriber')
                publisher.publish(Bool(data=True))
                if cycle == 1:
                    wait(lambda: latest.get('trial') is not previous and latest['trial'].trial_number != previous_number,
                         30, 'task reset')
                else:
                    wait(lambda: latest.get('trial') is not previous and latest['trial'].trial_number < previous_number,
                         45, 'scene reload')
                wait(fresh, 30, 'sensors after reset')
                elapsed_clock = latest['clock'].clock.sec + latest['clock'].clock.nanosec * 1e-9 - clock_before
                elapsed_wall = time.monotonic() - reset_started
                report['resets'].append({'kind': 'task' if cycle == 1 else 'scene',
                                         'clock_seconds': elapsed_clock, 'wall_seconds': elapsed_wall})
                if elapsed_clock < 0 or elapsed_clock > elapsed_wall + 2:
                    raise RuntimeError('Simulation clock jumped during reset')

            log_path = Path(args.output).with_suffix(f'.nav2-{cycle}.log')
            with log_path.open('w') as log:
                process = subprocess.Popen(['ros2', 'launch', 'social_sim_ros', 'nav2_jackal.launch.py',
                                             'scene:=' + args.scene], stdout=log, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                wait(lambda: client.server_is_ready() and 'map' in latest, 45, 'Nav2 and map')
                state_client = node.create_client(GetState, '/bt_navigator/get_state')
                wait(state_client.service_is_ready, 30, 'navigator lifecycle service')
                active_deadline = time.monotonic() + 30
                while True:
                    state = state_client.call_async(GetState.Request())
                    wait(state.done, 5, 'navigator lifecycle state')
                    if state.result().current_state.id == 3:
                        break
                    if time.monotonic() >= active_deadline:
                        raise RuntimeError('Navigator did not activate')
                    rclpy.spin_once(node, timeout_sec=0.2)
                node.destroy_client(state_client)
                rejected_starts = []
                for attempt in range(10):
                    pose = latest['odom'].pose.pose
                    x, y = pose.position.x, pose.position.y
                    q = pose.orientation
                    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
                    target = None
                    for index in range(16):
                        angle = yaw + index * math.pi / 8
                        tx, ty = x + math.cos(angle), y + math.sin(angle)
                        if all(free(x + (tx-x)*fraction/10, y + (ty-y)*fraction/10) for fraction in range(11)):
                            target = (tx, ty)
                            break
                    if target is not None:
                        break
                    rejected_starts.append([x, y])
                    previous_number = latest['trial'].trial_number
                    reset.publish(Bool(data=True))
                    wait(lambda: latest['trial'].trial_number != previous_number, 15, 'clear test placement')
                    wait(fresh, 15, 'sensors after placement')
                if target is None:
                    raise RuntimeError(f'No clear test placement after 10 resets: {rejected_starts}')
                goal = NavigateToPose.Goal()
                goal.pose = PoseStamped()
                goal.pose.header.frame_id = 'map'
                goal.pose.header.stamp = node.get_clock().now().to_msg()
                goal.pose.pose.position.x, goal.pose.pose.position.y = target
                goal.pose.pose.orientation = q
                print(f'Episode {cycle}: start=({x:.3f}, {y:.3f}), goal={target}', flush=True)
                future = client.send_goal_async(goal)
                wait(future.done, 10, 'goal acceptance')
                handle = future.result()
                if not handle.accepted:
                    raise RuntimeError('Nav2 rejected the goal')
                result = handle.get_result_async()
                wait(result.done, 120, 'navigation completion')
                final = latest['odom'].pose.pose.position
                error = math.hypot(final.x-target[0], final.y-target[1])
                distance = math.hypot(final.x-x, final.y-y)
                episode = {'status': result.result().status, 'start': [x,y], 'goal': target,
                           'final': [final.x, final.y], 'goal_error': error, 'displacement': distance,
                           'fresh_sensors': fresh(), 'rejected_starts': rejected_starts}
                report['episodes'].append(episode)
                print(json.dumps(episode), flush=True)
                if episode['status'] != 4 or error > 0.4 or distance < 0.5 or not fresh():
                    raise RuntimeError('Navigation did not meet success criteria')
            os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=15)
            process = None
        report['passed'] = True
    except Exception as error:
        report['passed'] = False
        report['error'] = str(error)
        raise
    finally:
        report['sensor_counts'] = counts
        Path(args.output).write_text(json.dumps(report, indent=2))
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            except ProcessLookupError:
                pass
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

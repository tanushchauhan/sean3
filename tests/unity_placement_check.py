"""Check real task placements against the ROS map, odometry, and laser scan."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from rclpy.action import ActionClient
from nav2_msgs.action import ComputePathToPose
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from nav_msgs.msg import Odometry, OccupancyGrid
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
from social_sim_ros.msg import TrialInfo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--audit')
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('sean_placement_check')
    latest, received = {}, {}

    def receive(key, msg):
        latest[key], received[key] = msg, time.monotonic()

    for key, topic, cls in [('odom', '/robot_odom', Odometry), ('scan', '/laser_raycast', LaserScan),
                            ('trial', '/social_sim/metrics', TrialInfo)]:
        node.create_subscription(cls, topic, lambda msg, key=key: receive(key, msg), qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/map', lambda msg: receive('map', msg),
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    reset = node.create_publisher(Bool, '/social_sim/control/task/new', 10)
    reload = node.create_publisher(Bool, '/social_sim/control/scene/reload', 10)
    planner = ActionClient(node, ComputePathToPose, '/compute_path_to_pose')
    report = {'placements': [], 'passed': False, 'clearance_radius_m': 0.6}
    process = None

    def wait(predicate, description, seconds=60):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if predicate():
                return
        raise RuntimeError('Timed out: ' + description)

    def blocked_cells(x, y):
        grid = latest['map']
        resolution = grid.info.resolution
        cx = math.floor((x - grid.info.origin.position.x) / resolution)
        cy = math.floor((y - grid.info.origin.position.y) / resolution)
        cells = math.ceil(0.6 / resolution)
        blocked = []
        for dy in range(-cells, cells + 1):
            for dx in range(-cells, cells + 1):
                if dx*dx + dy*dy > cells*cells:
                    continue
                ix, iy = cx + dx, cy + dy
                value = grid.data[iy*grid.info.width+ix] if 0 <= ix < grid.info.width and 0 <= iy < grid.info.height else -1
                if value != 0:
                    blocked.append([ix, iy, value])
        return blocked

    def inspect(kind):
        wait(lambda: all(time.monotonic() - received.get(k, 0) < 2 for k in ('odom', 'scan', 'trial')),
             'fresh sensors and task metrics')
        settled = time.monotonic() + 2
        wait(lambda: time.monotonic() >= settled, 'settled body', 10)
        p = latest['odom'].pose.pose.position
        goal = latest['trial'].robot_goal
        blocked = blocked_cells(p.x, p.y)
        goal_blocked = blocked_cells(goal.position.x, goal.position.y)
        wait(planner.server_is_ready, 'planner action')
        request = ComputePathToPose.Goal()
        request.goal.header.frame_id = 'map'
        request.goal.pose = goal
        request.start.header.frame_id = 'map'
        request.start.pose = latest['odom'].pose.pose
        request.use_start = True
        future = planner.send_goal_async(request)
        wait(future.done, 'planner acceptance', 15)
        handle = future.result()
        if not handle.accepted:
            raise RuntimeError('Planner rejected task goal')
        result = handle.get_result_async()
        wait(result.done, 'task path', 30)
        path = result.result().result.path
        path_ok = result.result().status == 4 and len(path.poses) > 1
        scan = latest['scan']
        ranges = [r for r in scan.ranges if math.isfinite(r) and scan.range_min <= r <= scan.range_max]
        minimum = min(ranges, default=scan.range_max)
        fresh = all(time.monotonic() - received.get(k, 0) < 2 for k in ('odom', 'scan', 'trial'))
        record = {'kind': kind, 'trial': latest['trial'].trial_number,
                  'position': [p.x, p.y, p.z], 'blocked_cells': blocked,
                  'laser_min_m': minimum, 'fresh': fresh, 'goal_blocked_cells': goal_blocked,
                  'goal': [goal.position.x, goal.position.y], 'path_poses': len(path.poses), 'path_passed': path_ok}
        record['passed'] = not blocked and not goal_blocked and path_ok and minimum >= 0.3 and abs(p.z - 0.04) < 0.05 and fresh
        report['placements'].append(record)
        print(json.dumps(record), flush=True)
        if not record['passed']:
            raise RuntimeError('Placement failed independent map/height/laser checks')

    try:
        with Path(args.output).with_suffix('.nav2.log').open('w') as log:
            process = subprocess.Popen(['ros2', 'launch', 'social_sim_ros', 'nav2_jackal.launch.py', 'scene:=warehouse'],
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        wait(lambda: all(k in latest for k in ('map', 'odom', 'scan', 'trial')), 'map and live task')
        if args.audit:
            wait(lambda: Path(args.audit).exists(), 'running-scene sampler audit')
            audit = json.loads(Path(args.audit).read_text())
            failures = []
            for index, pair in enumerate(audit['pairs']):
                if not pair['found'] or any(blocked_cells(pair[key]['z'], -pair[key]['x']) for key in ('start', 'goal')):
                    failures.append(index)
            report['audit_pairs'] = len(audit['pairs'])
            report['audit_failures'] = failures
            report['known_bad_start_rejected'] = not audit['knownBadStartClear']
            if failures or not report['known_bad_start_rejected']:
                raise RuntimeError('Sampled pairs failed independent map audit')
        inspect('startup')
        for kind in ['task']*10 + ['scene'] + ['task']*10 + ['scene']:
            publisher = reset if kind == 'task' else reload
            wait(lambda: publisher.get_subscription_count() > 0, 'control subscription')
            previous = latest['trial'].trial_number
            publisher.publish(Bool(data=True))
            wait(lambda: latest['trial'].trial_number > previous if kind == 'task'
                 else latest['trial'].trial_number < previous, 'acknowledged ' + kind)
            inspect(kind)
        report['passed'] = True
    except Exception as error:
        report['error'] = str(error)
        raise
    finally:
        Path(args.output).write_text(json.dumps(report, indent=2))
        if process is not None:
            os.killpg(process.pid, signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

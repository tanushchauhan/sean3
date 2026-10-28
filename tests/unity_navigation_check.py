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
from nav2_msgs.action import ComputePathToPose
from route_metrics import path_geometry, trajectory_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scene', default='warehouse')
    parser.add_argument('--output', default='/tmp/unity-navigation.json')
    parser.add_argument('--cycles', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--require-clear-start', action='store_true',
                        help='Fail rather than reset away a rejected placement')
    parser.add_argument('--task-goals', action='store_true', help='Drive generated task goals without substitute placements')
    parser.add_argument('--goal-timeout', type=float, default=300)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('sean_navigation_check', parameter_overrides=[Parameter('use_sim_time', value=True)])
    latest = {}
    received = {}
    counts = {}
    samples = []
    recording = False

    def receive(key, message):
        latest[key] = message
        received[key] = time.monotonic()
        counts[key] = counts.get(key, 0) + 1
        if recording and key == 'odom':
            p, q = message.pose.pose.position, message.pose.pose.orientation
            stamp = message.header.stamp
            t = stamp.sec + stamp.nanosec*1e-9
            if not samples or t < samples[-1][0] or t-samples[-1][0] >= 0.19:
                samples.append([t, p.x, p.y, math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))])

    for key, topic, cls in [('odom', '/robot_odom', Odometry), ('scan', '/laser_raycast', LaserScan),
                             ('clock', '/clock', Clock), ('trial', '/social_sim/metrics', TrialInfo)]:
        node.create_subscription(cls, topic, lambda msg, key=key: receive(key, msg), qos_profile_sensor_data)
    node.create_subscription(OccupancyGrid, '/map', lambda msg: receive('map', msg),
                             QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
    reset = node.create_publisher(Bool, '/social_sim/control/task/new', 10)
    reload = node.create_publisher(Bool, '/social_sim/control/scene/reload', 10)
    client = ActionClient(node, NavigateToPose, '/navigate_to_pose')
    planner = ActionClient(node, ComputePathToPose, '/compute_path_to_pose')
    report = {'scene': args.scene, 'task_goals': args.task_goals, 'episodes': [], 'resets': [], 'passed': False,
              'goal_timeout_wall_seconds': args.goal_timeout}
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
        cx = math.floor((x - grid.info.origin.position.x) / resolution)
        cy = math.floor((y - grid.info.origin.position.y) / resolution)
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

            if args.task_goals:
                settled = time.monotonic()+2
                wait(lambda: fresh() and time.monotonic() >= settled, 15, 'settled long-task placement')
            log_path = Path(args.output).with_suffix(f'.nav2-{cycle}.log')
            with log_path.open('w') as log:
                process = subprocess.Popen(['ros2', 'launch', 'social_sim_ros', 'nav2_kuri.launch.py',
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
                for attempt in range(1 if args.task_goals else 10):
                    pose = latest['odom'].pose.pose
                    x, y = pose.position.x, pose.position.y
                    q = pose.orientation
                    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y*q.y + q.z*q.z))
                    target = None
                    if args.task_goals:
                        task_goal = latest['trial'].robot_goal
                        target = (task_goal.position.x, task_goal.position.y)
                        if not free(x, y) or not free(*target) or math.dist((x, y), target) < 3:
                            raise RuntimeError('Generated long task failed map clearance or minimum separation')
                        q = task_goal.orientation
                        break
                    for index in range(16):
                        angle = yaw + index * math.pi / 8
                        tx, ty = x + math.cos(angle), y + math.sin(angle)
                        if all(free(x + (tx-x)*fraction/10, y + (ty-y)*fraction/10) for fraction in range(11)):
                            target = (tx, ty)
                            break
                    if target is not None:
                        break
                    rejected_starts.append([x, y])
                    if args.require_clear_start:
                        raise RuntimeError(f'Initial placement has no clear one metre path: {x}, {y}')
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
                episode = {'cycle': cycle, 'kind': ('startup', 'task', 'scene')[cycle],
                           'trial': latest['trial'].trial_number, 'start': [x, y], 'goal': target,
                           'rejected_starts': rejected_starts, 'passed': False}
                report['episodes'].append(episode)
                if args.task_goals:
                    wait(planner.server_is_ready, 20, 'planner action')
                    request = ComputePathToPose.Goal()
                    request.goal = goal.pose
                    request.start.header = goal.pose.header
                    request.start.pose = latest['odom'].pose.pose
                    request.use_start = True
                    planned = planner.send_goal_async(request)
                    wait(planned.done, 10, 'plan acceptance')
                    if not planned.result().accepted:
                        raise RuntimeError('Planner rejected generated goal')
                    planned_result = planned.result().get_result_async()
                    wait(planned_result.done, 30, 'initial global plan')
                    path = planned_result.result().result.path
                    points = [[p.pose.position.x, p.pose.position.y] for p in path.poses]
                    episode['plan'] = dict(path_geometry(points), points=points, status=planned_result.result().status)
                    episode['straight_corridor_clear_0_3m'] = all(free(x+(target[0]-x)*f/100, y+(target[1]-y)*f/100, .3) for f in range(101))
                    if episode['plan']['status'] != 4 or len(points) < 2:
                        raise RuntimeError('No global plan for generated goal')
                print(f'Episode {cycle}: start=({x:.3f}, {y:.3f}), goal={target}', flush=True)
                samples.clear()
                collision_fields = ('obj_collisions', 'robot_on_person_collisions', 'person_on_robot_collisions')
                collision_start = {k: getattr(latest['trial'], k) for k in collision_fields}
                collision_max = dict(collision_start)
                started = time.monotonic()
                recording = True
                feedback_samples = []
                def feedback(message):
                    value = message.feedback
                    feedback_samples.append({'wall_seconds': time.monotonic()-started,
                                             'distance_remaining_m': value.distance_remaining,
                                             'recoveries': value.number_of_recoveries})
                future = client.send_goal_async(goal, feedback_callback=feedback if args.task_goals else None)
                wait(future.done, 10, 'goal acceptance')
                handle = future.result()
                if not handle.accepted:
                    raise RuntimeError('Nav2 rejected the goal')
                result = handle.get_result_async()
                deadline = started + (args.goal_timeout if args.task_goals else 120)
                failure = None
                last_progress = started
                while not result.done():
                    rclpy.spin_once(node, timeout_sec=.05)
                    if time.monotonic()-last_progress >= 30:
                        p = latest['odom'].pose.pose.position
                        print(f'Episode {cycle}: {time.monotonic()-started:.1f}s, remaining Euclidean distance {math.dist((p.x,p.y), target):.2f}m', flush=True)
                        last_progress = time.monotonic()
                    if args.task_goals:
                        if latest['trial'].trial_number != episode['trial']:
                            failure = 'Task changed during navigation'
                        for key in collision_fields:
                            collision_max[key] = max(collision_max[key], getattr(latest['trial'], key))
                        if not fresh() or time.monotonic()-received.get('trial', 0) >= 3:
                            failure = 'Stale sensor or task stream during navigation'
                    if time.monotonic() >= deadline:
                        failure = 'Navigation wall timeout'
                    if failure:
                        canceled = handle.cancel_goal_async()
                        wait(canceled.done, 10, 'goal cancellation')
                        wait(result.done, 10, 'canceled navigation result')
                        break
                recording = False
                # Metrics publish at 1 Hz; collect the final counter update after stopping.
                settled = time.monotonic()+1.2
                wait(lambda: time.monotonic() >= settled, 5, 'final metrics')
                for key in collision_fields:
                    collision_max[key] = max(collision_max[key], getattr(latest['trial'], key))
                final = latest['odom'].pose.pose.position
                error = math.hypot(final.x-target[0], final.y-target[1])
                distance = math.hypot(final.x-x, final.y-y)
                episode.update({'status': result.result().status, 'start': [x,y], 'goal': target,
                           'final': [final.x, final.y], 'goal_error': error, 'displacement': distance,
                           'fresh_sensors': fresh(), 'rejected_starts': rejected_starts,
                           'wall_seconds': time.monotonic()-started, 'failure': failure})
                if args.task_goals:
                    episode.update(trajectory_metrics(samples))
                    episode.update(trajectory=samples.copy(), collision_start=collision_start, collision_max=collision_max,
                                   feedback=feedback_samples,
                                   max_recoveries=max((f['recoveries'] for f in feedback_samples), default=0))
                episode['passed'] = (not failure and episode['status'] == 4 and error <= .4 and distance >= .5 and fresh()
                                     and (not args.task_goals or (not any(collision_max.values()) and not episode['translation_stalls']
                                                                 and not episode['bounded_motion_stalls'] and episode['max_sample_gap_seconds'] <= 1)))
                print(json.dumps({k:v for k,v in episode.items() if k not in ('trajectory', 'plan', 'feedback')}), flush=True)
                Path(args.output).write_text(json.dumps(report, indent=2))
                if not episode['passed'] and not args.task_goals:
                    raise RuntimeError('Navigation did not meet success criteria')
            os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=15)
            process = None
        report['passed'] = all(episode['passed'] for episode in report['episodes'])
        if not report['passed']:
            raise RuntimeError('One or more generated routes failed acceptance; all outcomes preserved')
    except (Exception, KeyboardInterrupt) as error:
        if recording and report['episodes']:
            report['episodes'][-1].update(trajectory=samples.copy(), failure=str(error))
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
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()

"""Wait for the first real task and settled robot before saving camera samples."""
import argparse
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from social_sim_ros.msg import TrialInfo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('sean_capture_startup')
    latest = {}
    node.create_subscription(Odometry, '/robot_odom', lambda m: latest.update(odom=m), qos_profile_sensor_data)
    node.create_subscription(TrialInfo, '/social_sim/metrics', lambda m: latest.update(trial=m), qos_profile_sensor_data)
    ready_since = None
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if 'odom' not in latest or 'trial' not in latest:
                continue
            p, trial = latest['odom'].pose.pose.position, latest['trial']
            velocity = latest['odom'].twist.twist.linear
            ready = trial.trial_number > 0 and math.hypot(p.x-trial.robot_start.position.x,
                p.y-trial.robot_start.position.y) < 0.1 and abs(velocity.z) < 0.05
            ready_since = (ready_since or time.monotonic()) if ready else None
            if ready_since is not None and time.monotonic() - ready_since > 1:
                Path(args.output).write_text(json.dumps(dict(trial=trial.trial_number,
                    position=[p.x, p.y, p.z], passed=True), indent=2))
                return
        raise RuntimeError('No settled initial task before capture')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

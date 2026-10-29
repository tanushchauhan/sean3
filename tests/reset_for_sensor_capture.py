"""Request one normal task reset before collecting a second Warehouse view."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
from social_sim_ros.msg import TrialInfo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('sean_sensor_capture_reset')
    latest = {}
    node.create_subscription(Odometry, '/robot_odom', lambda m: latest.update(odom=m), qos_profile_sensor_data)
    node.create_subscription(TrialInfo, '/social_sim/metrics', lambda m: latest.update(trial=m), qos_profile_sensor_data)
    publisher = node.create_publisher(Bool, '/social_sim/control/task/new', 10)

    def wait(predicate, description):
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if predicate():
                return
        raise RuntimeError('Timed out waiting for ' + description)

    def position():
        p = latest['odom'].pose.pose.position
        return [p.x, p.y, p.z]

    report = {}
    try:
        wait(lambda: 'odom' in latest and 'trial' in latest and publisher.get_subscription_count() > 0,
             'startup odometry, metrics, and reset subscription')
        old = latest['trial'].trial_number
        report['before'] = position()
        publisher.publish(Bool(data=True))
        wait(lambda: latest['trial'].trial_number != old and
             sum((a-b)**2 for a, b in zip(position(), report['before'])) > 1,
             'a different task and robot placement')
        report.update(after=position(), trial_before=old, trial_after=latest['trial'].trial_number,
                      passed=True, note='One task reset; no free-space or view-quality acceptance asserted.')
    except Exception as error:
        report.update(passed=False, error=str(error))
        raise
    finally:
        Path(args.output).write_text(json.dumps(report, indent=2))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

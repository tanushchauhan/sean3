"""Capture a bounded diagnostic snapshot from an owned navigation graph."""
import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry, Path as NavPath
from sensor_msgs.msg import LaserScan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--seconds', type=float, default=3)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node('sean_navigation_snapshot')
    latest = {}

    def receive(topic, msg):
        latest[topic] = message_to_ordereddict(msg)
        if topic == '/plan' and msg.poses:
            start = msg.poses[0].pose.position
            point = next((p.pose.position for p in msg.poses
                          if math.hypot(p.pose.position.x-start.x, p.pose.position.y-start.y) >= .6), None)
            if point is not None:
                end = msg.poses[-1].pose.position
                latest.setdefault('_path_headings', []).append({
                    'heading': math.atan2(point.y-start.y, point.x-start.x),
                    'start': [start.x, start.y], 'goal': [end.x, end.y]})

    for topic, cls in [('/robot_odom', Odometry), ('/laser_raycast', LaserScan),
                       ('/plan', NavPath), ('/local_plan', NavPath),
                       ('/transformed_global_plan', NavPath), ('/cmd_vel_nav', Twist),
                       ('/mobile_base_controller/cmd_vel', Twist)]:
        node.create_subscription(cls, topic, lambda msg, topic=topic: receive(topic, msg), qos_profile_sensor_data)
    deadline = time.monotonic()+args.seconds
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.05)
        Path(args.output).write_text(json.dumps(latest, indent=2))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

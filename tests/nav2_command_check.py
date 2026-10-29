"""Check command routing and the smoother timeout without moving a Unity robot."""

import time


def check_commands():
    import rclpy
    from geometry_msgs.msg import Twist

    rclpy.init()
    node = rclpy.create_node('sean_command_check')
    samples = []
    output = '/mobile_base_controller/cmd_vel'
    publisher = node.create_publisher(Twist, '/cmd_vel_nav', 10)
    subscription = node.create_subscription(
        Twist, output, lambda message: samples.append((time.monotonic(), message.linear.x)), 10,
    )
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            producers = {info.node_name for info in node.get_publishers_info_by_topic('/cmd_vel_nav')}
            consumers = {info.node_name for info in node.get_subscriptions_info_by_topic('/cmd_vel_nav')}
            outputs = {info.node_name for info in node.get_publishers_info_by_topic(output)}
            if ({'controller_server', 'behavior_server'} <= producers
                    and 'velocity_smoother' in consumers and outputs == {'velocity_smoother'}
                    and publisher.get_subscription_count() > 0):
                break
        else:
            raise RuntimeError(f'Unexpected command graph: {producers}, {consumers}, {outputs}')

        command = Twist()
        command.linear.x = 0.04
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            publisher.publish(command)
            rclpy.spin_once(node, timeout_sec=0.05)
        if not any(abs(velocity - 0.04) < 0.001 for _, velocity in samples):
            raise RuntimeError('The requested velocity did not reach the Unity command topic')

        stopped_publishing = time.monotonic()
        deadline = stopped_publishing + 3
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
        if not any(stamp > stopped_publishing + 0.5 and abs(velocity) < 0.001
                   for stamp, velocity in samples):
            raise RuntimeError('The smoother did not stop after commands timed out')
        print('Command routing and velocity timeout passed.')
    finally:
        node.destroy_subscription(subscription)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    check_commands()

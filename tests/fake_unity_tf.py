"""Stand-in for Unity: registers a publisher with the ROS-TCP-Endpoint, then sends /tf."""
import json
import socket
import struct
import time

from geometry_msgs.msg import TransformStamped
from rclpy.serialization import serialize_message
from tf2_msgs.msg import TFMessage


def frame(dest, payload):
    d = dest.encode()
    return struct.pack('<I', len(d)) + d + struct.pack('<I', len(payload)) + payload


s = socket.create_connection(('127.0.0.1', 10000))
reg = json.dumps({'topic': '/tf', 'message_name': 'tf2_msgs/TFMessage', 'queue_size': 10, 'latch': False})
s.sendall(frame('__publish', reg.encode() + b'\0'))
time.sleep(1)
for i in range(5):
    t = TransformStamped()
    t.header.stamp.sec = 10 + i
    t.header.frame_id = 'map'
    t.child_frame_id = 'odom'
    t.transform.translation.x = 1.5
    t.transform.rotation.w = 1.0
    s.sendall(frame('/tf', serialize_message(TFMessage(transforms=[t]))))
    time.sleep(0.2)
print('sent')
time.sleep(1)

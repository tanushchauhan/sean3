import socket, struct, time, sys
import rclpy
from rclpy.serialization import serialize_message
from geometry_msgs.msg import PoseStamped

def frame(dest, payload):
    d = dest.encode()
    return struct.pack('<I', len(d)) + d + struct.pack('<I', len(payload)) + payload

s = socket.create_connection(('127.0.0.1', 10000))
for i in range(5):
    m = PoseStamped()
    m.header.stamp.sec = 10 + i
    m.header.frame_id = 'map'
    m.pose.position.x = 1.5
    m.pose.orientation.w = 1.0
    s.sendall(frame('/map_to_odom', serialize_message(m)))
    time.sleep(0.2)
print('sent')
time.sleep(1)

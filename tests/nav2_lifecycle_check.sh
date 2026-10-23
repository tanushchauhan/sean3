cd /sean3_ws_overlay && colcon build --packages-select social_sim_ros 2>&1 | tail -1
source install/setup.bash
python3 - <<'PY' &
import rclpy, time
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
rclpy.init(); n = Node('fake_clock'); p = n.create_publisher(Clock, '/clock', 10)
t = 0.0
while rclpy.ok():
    m = Clock(); m.clock.sec = int(t); m.clock.nanosec = int((t % 1) * 1e9); p.publish(m); t += 0.02; time.sleep(0.02)
PY
ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id base_link > /dev/null 2>&1 &
ros2 launch social_sim_ros nav2_jackal.launch.py > /tmp/nav2.log 2>&1 &
sleep 40
for n in map_server controller_server planner_server bt_navigator behavior_server; do echo $n $(ros2 lifecycle get /$n 2>&1 | tail -1); done
grep -iE "error|fatal" /tmp/nav2.log | head -15

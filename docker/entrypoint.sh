#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
source /opt/sean3_ws/install/setup.bash
[ -f /sean3_ws_overlay/install/setup.bash ] && source /sean3_ws_overlay/install/setup.bash
exec "$@"

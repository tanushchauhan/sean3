#!/usr/bin/env bash
set -eo pipefail

script_dir=$(cd "$(dirname "$0")" && pwd)
workspace=${1:-/sean3_ws_overlay}
cd "$workspace"
colcon build --packages-select social_sim_ros
source install/setup.bash
exec python3 "$script_dir/nav2_lifecycle_check.py"

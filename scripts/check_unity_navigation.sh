#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <player> <ros-workspace> <ros-repository> <results-directory>" >&2
    exit 2
fi
scripts=$(cd "$(dirname "$0")" && pwd)
player=$(realpath "$1")
workspace=$(realpath "$2")
repository=$(realpath "$3")
mkdir -p "$4"
results=$(realpath "$4")
if [ -e "$results/config.txt" ]; then
    echo "Use a new results directory to preserve previous runs." >&2
    exit 2
fi
image=${SEAN_ROS_IMAGE:-sean3-humble:dev}
port=${SEAN_TCP_PORT:-10321}
seed=${SEAN_SEED:-7}
mode=${SEAN_CHECK_MODE:-navigation}
check_status=0
case "$mode" in navigation|lifecycle) ;; *) echo "Unknown check mode: $mode" >&2; exit 2 ;; esac
container="sean3-navigation-$$"
sampler_pid=
player_pid=
container_started=false

cleanup() {
    if [ -n "$sampler_pid" ]; then
        kill "$sampler_pid" 2>/dev/null || true
        wait "$sampler_pid" 2>/dev/null || true
    fi
    if [ -n "$player_pid" ]; then
        kill -TERM -- "-$player_pid" 2>/dev/null || true
        wait "$player_pid" 2>/dev/null || true
    fi
    if [ "$container_started" = true ]; then
        docker logs "$container" > "$results/endpoint.log" 2>&1 || true
        docker rm -f "$container" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# DDS stays inside the container; only the TCP endpoint is exposed on localhost.
docker run --rm --network none \
    -v "$workspace:/sean3_ws_overlay" \
    -v "$repository:/sean3_ws_overlay/src/social_sim_ros:ro" \
    "$image" bash -c 'cd /sean3_ws_overlay && colcon build --packages-select social_sim_ros'

docker run -d --name "$container" -p "127.0.0.1:$port:10000" -e ROS_DOMAIN_ID=73 \
    -v "$workspace:/sean3_ws_overlay" \
    -v "$repository:/sean3_ws_overlay/src/social_sim_ros:ro" \
    -v "$scripts/../tests:/tests:ro" -v "$results:/results" \
    "$image" ros2 launch social_sim_ros sim_tcp_bridge.launch.py >/dev/null
container_started=true

setsid xvfb-run -a bash "$scripts/run_unity_player.sh" "$player" \
    -batchmode -nographics -scene SEAN/Warehouse -scenario None -task RandomABNav \
    -seed "$seed" -ros-tcp-port "$port" -task-timeout-seconds 3600 -external-goals \
    -logFile "$results/player.log" > "$results/player-console.log" 2>&1 &
player_pid=$!

printf 'scene=SEAN/Warehouse\nscenario=None\ntask=RandomABNav\nseed=%s\nmode=%s\n' "$seed" "$mode" > "$results/config.txt"
if [ "$mode" = lifecycle ]; then
    python3 "$scripts/../tests/unity_lifecycle_check.py" --sample-player "$player" \
        --output "$results/player-resources.json" > "$results/resource-sampler.log" 2>&1 &
    sampler_pid=$!
    docker exec "$container" bash -c \
        'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; python3 /tests/unity_lifecycle_check.py --output /results/lifecycle.json --resources /results/player-resources.json --pairs "$1"' \
        bash "${SEAN_LIFECYCLE_PAIRS:-6}" > "$results/check.log" 2>&1 || check_status=$?
else
strict=()
if [ "${SEAN_REQUIRE_CLEAR_START:-0}" = 1 ]; then strict=(--require-clear-start); fi
docker exec "$container" bash -c \
    'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; python3 /tests/unity_navigation_check.py --cycles 3 --output /results/navigation.json "$@"' \
    bash "${strict[@]}" > "$results/check.log" 2>&1
fi
cat "$results/check.log"
if [ "$mode" = lifecycle ]; then
    cleanup
    trap - EXIT
    python3 "$scripts/../tests/lifecycle_log_check.py" "$results" || check_status=1
fi
exit "$check_status"

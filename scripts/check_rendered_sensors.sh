#!/usr/bin/env bash
# Capture actual rendered ROS sensor output; analyze capture.json separately.
set -euo pipefail
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <player> <ros-workspace> <ros-repository> <new-results-directory>" >&2
    exit 2
fi
scripts=$(cd "$(dirname "$0")" && pwd)
player=$(realpath "$1")
workspace=$(realpath "$2")
repository=$(realpath "$3")
mkdir "$4"
results=$(realpath "$4")
image=${SEAN_ROS_IMAGE:-localhost/sean3-humble:dev}
port=${SEAN_TCP_PORT:-10322}
container="sean3-rendered-$$"
player_pid=
cleanup() {
    if [ -n "$player_pid" ]; then
        # Keep Xvfb alive until the GPU application has released its context.
        # Killing the whole group at once can crash NVIDIA/Mono during teardown.
        app_pids=$(pgrep -g "$player_pid" -x "$(basename "$player")" || true)
        printf '%s\n' "$app_pids" > "$results/player-app-pids.txt"
        for app_pid in $app_pids; do kill -TERM "$app_pid" 2>/dev/null || true; done
        for attempt in $(seq 1 100); do
            alive=false
            for app_pid in $app_pids; do
                if kill -0 "$app_pid" 2>/dev/null; then alive=true; fi
            done
            [ "$alive" = true ] || break
            sleep 0.1
        done
        for app_pid in $(pgrep -g "$player_pid" -x "$(basename "$player")" || true); do
            kill -KILL "$app_pid" 2>/dev/null || true
        done
        kill -TERM -- "-$player_pid" 2>/dev/null || true
        player_status=0
        wait "$player_pid" 2>/dev/null || player_status=$?
        printf '%s\n' "$player_status" > "$results/player-wrapper-exit.txt"
    fi
    docker logs "$container" > "$results/endpoint.log" 2>&1 || true
    docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
docker image inspect "$image" > "$results/container.json"
sha256sum "$player" > "$results/player.sha256"
docker run -d --name "$container" -p "127.0.0.1:$port:10000" -e ROS_DOMAIN_ID=74 \
    -v "$workspace:/sean3_ws_overlay" \
    -v "$repository:/sean3_ws_overlay/src/social_sim_ros:ro" \
    -v "$scripts/../tests:/tests:ro" -v "$results:/results" \
    "$image" ros2 launch social_sim_ros sim_tcp_bridge.launch.py > "$results/container-id.txt"
placement=()
if [ "${SEAN_PLACEMENT_AUDIT:-0}" = 1 ] || [ "${SEAN_PLACEMENT_RESETS:-0}" = 1 ]; then
    placement=(-placement-validation-output "$results/placement-audit.json")
fi
fixture=()
capture=()
if [ -n "${SEAN_SENSOR_HEADING:-}" ]; then
    fixture=(-sensor-validation-output "$results/fixture.json" -sensor-validation-heading "$SEAN_SENSOR_HEADING")
    capture=(--fixture /results/fixture.json)
fi
# WaitForEndOfFrame publishers need rendered frames: omit -batchmode/-nographics.
LP_NUM_THREADS=${SEAN_RENDER_THREADS:-4} setsid xvfb-run -a -s '-screen 0 1024x768x24' bash -c \
    'device=$1; log=$2; shift 2; if [ -n "$device" ]; then vglrun -d "$device" glxinfo -B > "$log"; exec vglrun -d "$device" bash "$@"; else glxinfo -B > "$log"; exec bash "$@"; fi' \
    bash "${SEAN_VGL_DEVICE:-}" "$results/glxinfo.txt" \
    "$scripts/run_unity_player.sh" "$player" -force-glcore \
    -screen-width 640 -screen-height 480 -screen-fullscreen 0 -job-worker-count 4 -frame-rate "${SEAN_FRAME_RATE:-30}" \
    -scene SEAN/Warehouse -scenario None -task RandomABNav -seed "${SEAN_SEED:-7}" \
    -ros-tcp-port "$port" -task-timeout-seconds 3600 -external-goals \
    "${fixture[@]}" "${placement[@]}" -logFile "$results/player.log" > "$results/player-console.log" 2>&1 &
player_pid=$!
printf '%s\n' "$player_pid" > "$results/player.pid"
printf 'seed=%s\nheading=%s\nport=%s\nrenderer=OpenGL under Xvfb\nvgl_device=%s\nframe_rate_target=%s\n' "${SEAN_SEED:-7}" "${SEAN_SENSOR_HEADING:-warehouse}" "$port" "${SEAN_VGL_DEVICE:-none}" "${SEAN_FRAME_RATE:-30}" > "$results/config.txt"
# Measured-target runs already wait for their fixture, which moves the robot.
if [ -z "${SEAN_SENSOR_HEADING:-}" ]; then
docker exec "$container" bash -c \
    'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; exec python3 /tests/wait_for_task_capture.py --output /results/startup.json' \
    > "$results/startup-console.log" 2>&1
fi
if [ "${SEAN_CAPTURE_RESET:-0}" = 1 ]; then
    docker exec "$container" bash -c \
        'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; exec python3 /tests/reset_for_sensor_capture.py --output /results/reset.json' \
        > "$results/reset-console.log" 2>&1
fi
docker exec "$container" bash -c \
    'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; exec python3 /tests/capture_rendered_sensors.py --output /results/capture --seconds "$@"' \
    bash "${SEAN_CAPTURE_SECONDS:-35}" "${capture[@]}" > "$results/capture-console.log" 2>&1

if [ "${SEAN_PLACEMENT_RESETS:-0}" = 1 ]; then
    docker exec "$container" bash -c \
        'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; exec python3 /tests/unity_placement_check.py --output /results/placements.json --audit /results/placement-audit.json' \
        > "$results/placements-console.log" 2>&1
fi

cleanup
trap - EXIT
if rg -q 'Native Crash Reporting|Got a SIGSEGV' "$results/player.log"; then
    echo 'Native player crash found during capture or shutdown' > "$results/shutdown-check.txt"
    exit 1
fi
echo 'No native crash marker in the complete player log; endpoint teardown is a separate check.' > "$results/shutdown-check.txt"

#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <player> <ros-workspace> <ros-repository> <results-directory>" >&2
    exit 2
fi
scripts=$(cd "$(dirname "$0")" && pwd)
source "$scripts/cleanup_validation.sh"
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
case "$mode" in navigation|lifecycle|long-navigation) ;; *) echo "Unknown check mode: $mode" >&2; exit 2 ;; esac
profile_mount=()
if [ -n "${SEAN_NAV2_PARAMS_FILE:-}" ]; then
    profile=$(realpath "$SEAN_NAV2_PARAMS_FILE")
    profile_mount=(-v "$profile:/sean3_ws_overlay/install/social_sim_ros/share/social_sim_ros/params/kuri/nav2_params.yaml:ro")
fi
laser=${SEAN_LASER_NO_RETURN:-PositiveInfinity}
scenario=${SEAN_SCENARIO:-None}
visible=${SEAN_VISIBLE:-0}
container="sean3-navigation-$$"
sampler_pid=
load_pid=
player_pid=
container_started=false

cleanup() {
    if [ -n "$load_pid" ]; then
        kill "$load_pid" 2>/dev/null || true
        wait "$load_pid" 2>/dev/null || true
        load_pid=
    fi
    if [ -n "$sampler_pid" ]; then
        kill "$sampler_pid" 2>/dev/null || true
        wait "$sampler_pid" 2>/dev/null || true
    fi
    if [ -n "$player_pid" ]; then
        stop_unity_player "$player_pid" "$player" "$results" || check_status=1
        player_pid=
    fi
    if [ "$container_started" = true ]; then
        stop_ros_container "$container" "$results" || check_status=1
        container_started=false
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

docker run -d --stop-signal SIGINT "${profile_mount[@]}" --name "$container" -p "127.0.0.1:$port:10000" -e ROS_DOMAIN_ID=73 \
    -v "$workspace:/sean3_ws_overlay" \
    -v "$repository:/sean3_ws_overlay/src/social_sim_ros:ro" \
    -v "$scripts/../tests:/tests:ro" -v "$results:/results" \
    "$image" ros2 launch social_sim_ros sim_tcp_bridge.launch.py >/dev/null
container_started=true
wait_ros_endpoint "$container" "$results"

task_options=()
if [ "$mode" = long-navigation ]; then
    # Nav2 owns completion. A zero distance disables the legacy 1.2 m / 5 s
    # auto-reset which would teleport the robot before precise goal arrival.
    task_options=(-completion-distance 0)
fi
task_options+=(-laser-no-return "$laser")
read -r -a extra_args <<< "${SEAN_PLAYER_ARGS:-}"
player_args=(-scene SEAN/Warehouse -scenario "$scenario" -task RandomABNav \
    -seed "$seed" -ros-tcp-port "$port" -task-timeout-seconds 3600 -external-goals "${task_options[@]}" \
    "${extra_args[@]}" -logFile "$results/player.log")
if [ "$visible" = 1 ]; then
    # Rendered window under Xvfb, recorded from the display. The recorder stops
    # after Unity exits so the video is finalized before display cleanup.
    LP_NUM_THREADS=${SEAN_RENDER_THREADS:-4} setsid xvfb-run -a -s '-screen 0 1280x720x24' bash -c \
        'device=$1; results=$2; shift 2; vgl=(); [ -n "$device" ] && vgl=(vglrun -d "$device")
         "${vgl[@]}" glxinfo -B > "$results/glxinfo.txt" 2>&1
         ffmpeg -nostdin -loglevel error -f x11grab -framerate 10 -video_size 1280x720 -i "$DISPLAY" \
             -c:v libx264 -preset veryfast -pix_fmt yuv420p "$results/screen.mkv" > "$results/ffmpeg.log" 2>&1 &
         recorder=$!
         "${vgl[@]}" bash "$@"; status=$?
         kill -INT "$recorder" 2>/dev/null; wait "$recorder"
         exit "$status"' \
        bash "${SEAN_VGL_DEVICE:-}" "$results" "$scripts/run_unity_player.sh" "$player" -force-glcore \
        -screen-width 1280 -screen-height 720 -screen-fullscreen 0 -frame-rate "${SEAN_FRAME_RATE:-30}" \
        "${player_args[@]}" > "$results/player-console.log" 2>&1 &
    player_pid=$!
else
    setsid xvfb-run -a bash "$scripts/run_unity_player.sh" "$player" -batchmode -nographics \
        "${player_args[@]}" > "$results/player-console.log" 2>&1 &
    player_pid=$!
fi
# Cumulative CPU ticks (utime+stime) of the TCP endpoint and Unity every 5 s;
# differences between samples give relay headroom.
( endpoint=; unity=
  while sleep 5; do
    [ -n "$endpoint" ] || endpoint=$(pgrep --ns "$(docker inspect -f '{{.State.Pid}}' "$container")" --nslist pid \
        -f 'sean_tcp_endpoint' | head -1)
    [ -n "$unity" ] || unity=$(pgrep -g "$player_pid" -x "$(basename "$player")" | head -1)
    printf '%s %s %s\n' "$(date +%s.%N)" \
        "$(awk '{print $14+$15}' "/proc/$endpoint/stat" 2>/dev/null || echo -)" \
        "$(awk '{print $14+$15}' "/proc/$unity/stat" 2>/dev/null || echo -)"
  done ) > "$results/cpu-ticks.txt" 2>/dev/null &
load_pid=$!

printf 'scene=SEAN/Warehouse\nscenario=%s\ntask=RandomABNav\nseed=%s\nmode=%s\n' "$scenario" "$seed" "$mode" > "$results/config.txt"
printf 'visible=%s\nvgl_device=%s\nframe_rate_target=%s\nplayer_args=%s\n' "$visible" "${SEAN_VGL_DEVICE:-none}" "${SEAN_FRAME_RATE:-30}" "${SEAN_PLAYER_ARGS:-}" >> "$results/config.txt"
printf 'laser_no_return=%s\nnav2_override=%s\n' "$laser" "${SEAN_NAV2_PARAMS_FILE:-default}" >> "$results/config.txt"
if [ -n "${SEAN_NAV2_PARAMS_FILE:-}" ]; then sha256sum "$profile" > "$results/nav2-profile.sha256"; cp "$profile" "$results/nav2-profile.yaml"; fi
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
if [ "$mode" = long-navigation ]; then strict+=(--task-goals --goal-timeout "${SEAN_GOAL_TIMEOUT:-300}"); fi
docker exec "$container" bash -c \
    'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; python3 /tests/unity_navigation_check.py --cycles 3 --output /results/navigation.json "$@"' \
    bash "${strict[@]}" > "$results/check.log" 2>&1 || check_status=$?
fi
cat "$results/check.log"
cleanup
trap - EXIT
if [ "$mode" = long-navigation ] && ! rg -q '^SEAN velocity-controlled robot: Kuri, body:' "$results/player.log"; then
    echo 'Long navigation requires the identified Kuri fixture.' >&2
    check_status=1
fi
python3 "$scripts/../tests/lifecycle_log_check.py" "$results" || check_status=1
exit "$check_status"

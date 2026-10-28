#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 4 ]; then
    echo 'Usage: check_pedestrian_avoidance.sh <player> <ros-workspace> <ros-repository> <new-results-directory>' >&2
    exit 2
fi
scripts=$(cd "$(dirname "$0")" && pwd)
source "$scripts/cleanup_validation.sh"
player=$(realpath "$1")
workspace=$(realpath "$2")
repository=$(realpath "$3")
mkdir "$4"
results=$(realpath "$4")
container="sean3-pedestrians-$$"
player_pid=
started=false
status=0
cleanup() {
    if [ -n "$player_pid" ]; then
        stop_unity_player "$player_pid" "$player" "$results" || status=1
        player_pid=
    fi
    if [ "$started" = true ]; then
        stop_ros_container "$container" "$results" || status=1
        started=false
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
image=${SEAN_ROS_IMAGE:-localhost/sean3-humble:dev}
port=${SEAN_TCP_PORT:-10331}
seeds=${SEAN_PEDESTRIAN_SEEDS:-7,42}
step=${SEAN_PEDESTRIAN_STEP:-0.02}
model=${SEAN_PEDESTRIAN_MODEL:-ColliderV1}
printf 'fixture=open floor in Warehouse player\nseeds=%s\nstep=%s\nmodel=%s\n' "$seeds" "$step" "$model" > "$results/config.txt"
docker run -d --stop-signal SIGINT --name "$container" -p "127.0.0.1:$port:10000" -e ROS_DOMAIN_ID=75 \
    -v "$workspace:/sean3_ws_overlay" -v "$repository:/sean3_ws_overlay/src/social_sim_ros:ro" \
    "$image" ros2 launch social_sim_ros sim_tcp_bridge.launch.py > "$results/container-id.txt"
started=true
wait_ros_endpoint "$container" "$results"
setsid xvfb-run -a bash "$scripts/run_unity_player.sh" "$player" -batchmode -nographics \
    -scene SEAN/Warehouse -scenario None -task RandomABNav -seed 7 -ros-tcp-port "$port" \
    -completion-distance 0 -task-timeout-seconds 3600 -external-goals \
    -pedestrian-validation-output "$results/pedestrians.json" \
    -pedestrian-validation-model "$model" -pedestrian-validation-seeds "$seeds" -pedestrian-validation-step "$step" \
    -logFile "$results/player.log" > "$results/player-console.log" 2>&1 &
player_pid=$!
# Bound failures independently of simulated time; preserve partial output.
for attempt in $(seq 1 900); do
    if [ -f "$results/pedestrians.json" ] && python3 -c 'import json,sys; sys.exit(not json.load(open(sys.argv[1])).get("complete"))' "$results/pedestrians.json"; then break; fi
    if ! kill -0 "$player_pid" 2>/dev/null; then status=1; break; fi
    sleep 1
done
cleanup
trap - EXIT
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert d["model"]==sys.argv[2] and d["seeds"]==list(map(int,sys.argv[3].split(","))) and abs(d["step"]-float(sys.argv[4]))<1e-6' "$results/pedestrians.json" "$model" "$seeds" "$step" || status=1
python3 "$scripts/../tests/analyze_pedestrian_avoidance.py" "$results/pedestrians.json" || status=1
python3 "$scripts/../tests/lifecycle_log_check.py" "$results" || status=1
exit "$status"

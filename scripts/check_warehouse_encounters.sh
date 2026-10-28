#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 4 ]; then
    echo 'Usage: check_warehouse_encounters.sh <player> <ros-workspace> <ros-repository> <new-results-directory>' >&2
    exit 2
fi
scripts=$(cd "$(dirname "$0")" && pwd)
source "$scripts/cleanup_validation.sh"
player=$(realpath "$1"); workspace=$(realpath "$2"); repository=$(realpath "$3")
mkdir "$4"; results=$(realpath "$4")
container="sean3-warehouse-$$"; player_pid=; driver_pid=; started=false; status=0
cleanup() {
    if [ -n "$player_pid" ]; then stop_unity_player "$player_pid" "$player" "$results" || status=1; player_pid=; fi
    if [ "$started" = true ]; then stop_ros_container "$container" "$results" || status=1; started=false; fi
    if [ -n "$driver_pid" ]; then wait "$driver_pid" || status=1; driver_pid=; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
image=${SEAN_ROS_IMAGE:-localhost/sean3-humble:dev}; port=${SEAN_TCP_PORT:-10333}
seeds=${SEAN_ENCOUNTER_SEEDS:-7,42}; step=${SEAN_ENCOUNTER_STEP:-0.02}
laser=${SEAN_LASER_NO_RETURN:-PositiveInfinity}
layouts=${SEAN_ENCOUNTER_LAYOUTS:-aisle,rack_end}; modes=${SEAN_ENCOUNTER_MODES:-absent,parked,yielding,oblivious,nav2}
printf 'scene=Warehouse\nseeds=%s\nstep=%s\nlayouts=%s\nmodes=%s\n' "$seeds" "$step" "$layouts" "$modes" > "$results/config.txt"
docker run -d --stop-signal SIGINT --name "$container" -p "127.0.0.1:$port:10000" -e ROS_DOMAIN_ID=76 \
    -v "$workspace:/sean3_ws_overlay" -v "$repository:/sean3_ws_overlay/src/social_sim_ros:ro" \
    -v "$scripts/../tests:/tests:ro" -v "$results:/results" \
    "$image" ros2 launch social_sim_ros sim_tcp_bridge.launch.py > "$results/container-id.txt"
started=true
wait_ros_endpoint "$container" "$results"
docker exec "$container" bash -c 'source /opt/ros/humble/setup.bash; source /sean3_ws_overlay/install/setup.bash; python3 /tests/warehouse_navigation_check.py /results/encounters.json' > "$results/navigation-console.log" 2>&1 &
driver_pid=$!
setsid xvfb-run -a bash "$scripts/run_unity_player.sh" "$player" -batchmode -nographics \
    -scene SEAN/Warehouse -scenario None -task RandomABNav -seed 7 -ros-tcp-port "$port" \
    -completion-distance 0 -task-timeout-seconds 3600 -external-goals -laser-no-return "$laser" \
    -warehouse-encounter-output "$results/encounters.json" -warehouse-encounter-step "$step" \
    -warehouse-encounter-seeds "$seeds" -warehouse-encounter-layouts "$layouts" -warehouse-encounter-modes "$modes" \
    -logFile "$results/player.log" > "$results/player-console.log" 2>&1 &
player_pid=$!
for attempt in $(seq 1 "${SEAN_ENCOUNTER_WALL_LIMIT:-2400}"); do
    if [ -f "$results/encounters.json" ] && python3 -c 'import json,sys;sys.exit(not json.load(open(sys.argv[1])).get("complete"))' "$results/encounters.json"; then break; fi
    if ! kill -0 "$player_pid" 2>/dev/null; then status=1; break; fi
    if ! kill -0 "$driver_pid" 2>/dev/null; then status=1; break; fi
    if [ "$attempt" -gt 180 ] && [ ! -f "$results/encounters.json" ]; then status=1; break; fi
    if [ -f "$results/player.log" ] && rg -q 'NullReferenceException|InvalidOperationException|IndexOutOfRangeException|ArgumentException' "$results/player.log"; then status=1; break; fi
    sleep 1
done
# The driver owns Nav2 and shuts it down before Unity/endpoint closure.
if [ -f "$results/encounters.json" ] && python3 -c 'import json,sys;sys.exit(not json.load(open(sys.argv[1])).get("complete"))' "$results/encounters.json"; then
    wait "$driver_pid" || status=1; driver_pid=
else
    status=1
fi
cleanup; trap - EXIT
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));assert d["seeds"]==list(map(int,sys.argv[2].split(","))) and d["layouts"]==sys.argv[3].split(",") and d["modes"]==sys.argv[4].split(",") and abs(d["step"]-float(sys.argv[5]))<1e-6 and d["laserNoReturn"]==sys.argv[6]' "$results/encounters.json" "$seeds" "$layouts" "$modes" "$step" "$laser" || status=1
python3 "$scripts/../tests/analyze_warehouse_encounters.py" "$results/encounters.json" --navigation "$results/warehouse-navigation.json" || status=1
python3 "$scripts/../tests/lifecycle_log_check.py" "$results" || status=1
python3 "$scripts/../tests/audit_simulation_logs.py" "$results" || status=1
exit "$status"

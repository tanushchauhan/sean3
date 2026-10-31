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
container="sean3-warehouse-$$"; player_pid=; driver_pid=; worker_pid=; started=false; status=0
cleanup() {
    if [ -n "$player_pid" ]; then stop_unity_player "$player_pid" "$player" "$results" || status=1; player_pid=; fi
    if [ "$started" = true ]; then stop_ros_container "$container" "$results" || status=1; started=false; fi
    if [ -n "$driver_pid" ]; then wait "$driver_pid" || status=1; driver_pid=; fi
    if [ -n "$worker_pid" ]; then
        for attempt in $(seq 1 50); do kill -0 "$worker_pid" 2>/dev/null || break; sleep .1; done
        forced_worker_stop=false
        if kill -0 "$worker_pid" 2>/dev/null; then forced_worker_stop=true; kill "$worker_pid" 2>/dev/null || true; fi
        worker_status=0; wait "$worker_pid" 2>/dev/null || worker_status=$?; worker_pid=
        printf 'exit_status=%s\nforced_stop=%s\n' "$worker_status" "$forced_worker_stop" > "$results/worker-exit.txt"
        if [ "$worker_status" != 0 ] || [ "$forced_worker_stop" = true ]; then status=1; fi
    fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
image=${SEAN_ROS_IMAGE:-localhost/sean3-humble:dev}; port=${SEAN_TCP_PORT:-10333}
seeds=${SEAN_ENCOUNTER_SEEDS:-7,42}; step=${SEAN_ENCOUNTER_STEP:-0.02}
laser=${SEAN_LASER_NO_RETURN:-PositiveInfinity}
layouts=${SEAN_ENCOUNTER_LAYOUTS:-aisle,rack_end}; modes=${SEAN_ENCOUNTER_MODES:-absent,parked,yielding,oblivious,nav2}
pedestrian_controller=${SEAN_PEDESTRIAN_CONTROLLER:-social_forces}
pedestrian_actuation=${SEAN_PEDESTRIAN_ACTUATION:-root_motion}
if [ "$pedestrian_controller" != social_forces ] && [ -z "${SEAN_PEDESTRIAN_ACTUATION:-}" ]; then pedestrian_actuation=velocity_body; fi
case "$pedestrian_actuation" in root_motion|velocity_body) ;; *) echo 'Unsupported pedestrian actuator' >&2; exit 2 ;; esac
if [ "$pedestrian_controller" != social_forces ] && [ "$pedestrian_actuation" != velocity_body ]; then echo 'Joint controllers require velocity_body actuation' >&2; exit 2; fi
case "$pedestrian_controller" in social_forces|orca|stars) ;; *) echo 'Unsupported encounter pedestrian controller' >&2; exit 2 ;; esac
orca_options=()
if [ "$pedestrian_controller" = orca ]; then
    orca_options=(-orca-decision-period "${SEAN_ORCA_DECISION_PERIOD:-0.1}"
        -orca-neighbor-distance "${SEAN_ORCA_NEIGHBOR_DISTANCE:-5}"
        -orca-max-neighbors "${SEAN_ORCA_MAX_NEIGHBORS:-64}"
        -orca-agent-horizon "${SEAN_ORCA_AGENT_HORIZON:-2.5}"
        -orca-obstacle-horizon "${SEAN_ORCA_OBSTACLE_HORIZON:-2.5}")
fi
printf 'scene=Warehouse\nseeds=%s\nstep=%s\nlayouts=%s\nmodes=%s\n' "$seeds" "$step" "$layouts" "$modes" > "$results/config.txt"
if [ "$pedestrian_controller" = stars ]; then
    : "${SEAN_STARS_CHECKPOINT:?External forecasting checkpoint required}"
    : "${SEAN_STARS_EXTENSION:?Pinned external model checkout required}"
    : "${SEAN_WORKER_PYTHON:?Dedicated model Python required}"
    "$SEAN_WORKER_PYTHON" -u "$scripts/../runtime/stars_bridge.py" \
        --checkpoint "$SEAN_STARS_CHECKPOINT" --extension "$SEAN_STARS_EXTENSION" \
        --allow-dirty-training-source --threads 1 --port 0 --observation-steps 8 --dt .4 \
        > "$results/worker.log" 2> "$results/worker-errors.log" &
    worker_pid=$!
    for attempt in $(seq 1 60); do
        [ ! -s "$results/worker.log" ] || break
        kill -0 "$worker_pid" 2>/dev/null || { echo 'STARS worker exited during startup' >&2; exit 1; }
        sleep 1
    done
    head -n 1 "$results/worker.log" > "$results/worker-startup.json"
    read -r worker_port checkpoint_sha extension_revision < <(python3 - "$results/worker-startup.json" "$SEAN_STARS_CHECKPOINT" <<'PY'
import hashlib,json,sys
d=json.load(open(sys.argv[1])); p=d['provenance']
assert d['model']=='stars_ma' and d['observation_steps']==8 and d['dt']==.4
assert p['checkpoint_sha256']==hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
assert p['extension_commit']=='d72eb2295c3336f0674932796cf41b60636cde3e'
print(d['port'],p['checkpoint_sha256'],p['extension_commit'])
PY
    )
    orca_options=(-stars-worker-port "$worker_port" -stars-checkpoint-sha256 "$checkpoint_sha" -stars-extension-revision "$extension_revision")
fi
printf 'pedestrian_controller=%s\n' "$pedestrian_controller" >> "$results/config.txt"
printf 'pedestrian_actuation=%s\n' "$pedestrian_actuation" >> "$results/config.txt"
if [ "${#orca_options[@]}" -gt 0 ]; then printf '%s\n' "${orca_options[@]}" >> "$results/config.txt"; fi
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
    -pedestrian-controller "$pedestrian_controller" -pedestrian-actuation "$pedestrian_actuation" "${orca_options[@]}" \
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
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));assert d.get("pedestrianController","social_forces")==sys.argv[2]' "$results/encounters.json" "$pedestrian_controller" || status=1
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));expected={"root_motion":"AnimatedRootMotionV1","velocity_body":"VelocityTargetsV1"}[sys.argv[2]];assert d.get("actuationModel","AnimatedRootMotionV1")==expected' "$results/encounters.json" "$pedestrian_actuation" || status=1
if [ "$pedestrian_controller" = orca ]; then
    python3 -c 'import json,sys;d=json.load(open(sys.argv[1]))["orcaSettings"];keys=("decisionPeriod","neighborDistance","maxNeighbors","agentHorizon","obstacleHorizon");assert all(abs(d[k]-float(v))<1e-6 for k,v in zip(keys,sys.argv[2:]))' \
        "$results/encounters.json" "${SEAN_ORCA_DECISION_PERIOD:-0.1}" "${SEAN_ORCA_NEIGHBOR_DISTANCE:-5}" \
        "${SEAN_ORCA_MAX_NEIGHBORS:-64}" "${SEAN_ORCA_AGENT_HORIZON:-2.5}" "${SEAN_ORCA_OBSTACLE_HORIZON:-2.5}" || status=1
fi
python3 "$scripts/../tests/analyze_warehouse_encounters.py" "$results/encounters.json" --navigation "$results/warehouse-navigation.json" || status=1
python3 "$scripts/../tests/lifecycle_log_check.py" "$results" || status=1
python3 "$scripts/../tests/audit_simulation_logs.py" "$results" || status=1
exit "$status"

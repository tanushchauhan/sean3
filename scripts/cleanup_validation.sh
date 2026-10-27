#!/usr/bin/env bash
# Source from a validation runner so wait can reap its own children.
stop_unity_player() {
    local wrapper=$1 executable=$2 results=$3 app_pid alive attempt status=0
    local app_pids forced_pids
    app_pids=$(pgrep -g "$wrapper" -x "$(basename "$executable")" || true)
    printf '%s\n' "$app_pids" > "$results/player-app-pids.txt"
    # Keep Xvfb alive while Unity releases graphics and closes ROS transport.
    for app_pid in $app_pids; do kill -TERM "$app_pid" 2>/dev/null || true; done
    for attempt in $(seq 1 120); do
        alive=false
        for app_pid in $app_pids; do
            if kill -0 "$app_pid" 2>/dev/null; then alive=true; fi
        done
        [ "$alive" = true ] || break
        sleep 0.1
    done
    forced_pids=$(pgrep -g "$wrapper" -x "$(basename "$executable")" || true)
    printf '%s\n' "$forced_pids" > "$results/player-forced-pids.txt"
    for app_pid in $forced_pids; do kill -KILL "$app_pid" 2>/dev/null || true; done
    # Give xvfb-run time to reap Unity and finish its own display cleanup.
    sleep 0.3
    kill -TERM -- "-$wrapper" 2>/dev/null || true
    wait "$wrapper" 2>/dev/null || status=$?
    printf '%s\n' "$status" > "$results/player-wrapper-exit.txt"
    [ -z "$forced_pids" ] && [ "$status" -eq 0 ]
}

stop_ros_container() {
    local container=$1 results=$2 status=0
    docker stop --time 10 "$container" > "$results/endpoint-stop.txt" 2>&1 || status=1
    docker inspect --format '{{json .State}}' "$container" > "$results/endpoint-exit.json" || status=1
    docker logs "$container" > "$results/endpoint.log" 2>&1 || status=1
    docker rm "$container" > "$results/endpoint-remove.txt" 2>&1 || status=1
    return "$status"
}

wait_ros_endpoint() {
    local container=$1 results=$2 attempt
    # A forwarded host port can accept and reset TCP before the process inside
    # the container has bound its socket. Use the post-bind ready log instead
    # of making an extra connection that would alter the lifecycle counters.
    for attempt in $(seq 1 100); do
        docker logs "$container" > "$results/endpoint-startup.log" 2>&1 || return 1
        if rg -q 'Starting server on .*:10000' "$results/endpoint-startup.log"; then return 0; fi
        if [ "$(docker inspect --format '{{.State.Running}}' "$container")" != true ]; then return 1; fi
        sleep 0.1
    done
    echo 'Endpoint did not become ready before starting Unity' >&2
    return 1
}

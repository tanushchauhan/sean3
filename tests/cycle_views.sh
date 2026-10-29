#!/usr/bin/env bash
# Run inside the player's X display: after the task starts, screenshot each
# on-screen view and press the view key between them.
#   cycle_views.sh <xdotool-root> <results> <presses> <seconds-between>
set -uo pipefail
xdo_root=$1 results=$2 presses=$3 interval=$4
xdotool() { LD_LIBRARY_PATH="$xdo_root/usr/lib/x86_64-linux-gnu" "$xdo_root/usr/bin/xdotool" "$@"; }
mkdir -p "$results/views"
for attempt in $(seq 1 300); do
    [ -f "$results/startup.json" ] && break
    sleep 1
done
sleep "$interval"
window=$(xdotool search --onlyvisible --class sean | head -1)
echo "window=$window" > "$results/views/keys.log"
for i in $(seq 0 "$presses"); do
    ffmpeg -nostdin -loglevel error -f x11grab -video_size 640x480 -i "$DISPLAY" -frames:v 1 "$results/views/view-$i.png"
    echo "$(date +%s.%N) screenshot $i" >> "$results/views/keys.log"
    [ "$i" -lt "$presses" ] || break
    xdotool windowfocus --sync "$window" key c >> "$results/views/keys.log" 2>&1
    echo "$(date +%s.%N) pressed c" >> "$results/views/keys.log"
    sleep "$interval"
done

#!/usr/bin/env bash
# Build the SEAN Linux player headlessly.
#   scripts/build_unity_player.sh <unity-editor-binary> <social_sim_unity-checkout> <output-dir>
# Needs a Unity license activated for the current user. The first build imports every asset
# (it can take an hour); later builds reuse the project's Library.
set -euo pipefail
unity=$1 project=$2 out=$3

# Unity fetches packages from GitHub over https; ignore personal git config such as an
# https-to-ssh rewrite. Unity's C# compiler aborts without ICU unless globalization is invariant.
export GIT_CONFIG_GLOBAL=/dev/null
export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

mkdir -p "$out"
xvfb-run -a "$unity" -batchmode -quit -projectPath "$project" -buildTarget Linux64 \
    -buildLinux64Player "$out/sean.x86_64" -logFile "$out/build.log"
[ -x "$out/sean.x86_64" ] || { echo "no player built; see $out/build.log" >&2; exit 1; }

{
    echo "built: $(date -u +%FT%TZ)"
    echo "unity_sha256: $(sha256sum "$unity" | cut -d' ' -f1)"
    echo "social_sim_unity: $(git -C "$project" rev-parse HEAD)"
} > "$out/manifest.txt"
echo "player: $out/sean.x86_64"

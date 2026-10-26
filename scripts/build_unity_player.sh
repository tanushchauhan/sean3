#!/usr/bin/env bash
# Build the SEAN Linux player headlessly.
#   scripts/build_unity_player.sh <unity-editor-binary> <social_sim_unity-checkout> <output-dir>
# Requires an activated Unity license and Linux build support.
set -euo pipefail
unity=$1 project=$2 out=$3

# Keep package fetching independent of personal Git rewrites.
export GIT_CONFIG_GLOBAL=/dev/null
export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

mkdir -p "$out"
xvfb-run -a "$unity" -batchmode -quit -projectPath "$project" -buildTarget Linux64 \
    -buildLinux64Player "$out/sean.x86_64" -logFile "$out/build.log"
[ -x "$out/sean.x86_64" ] || { echo "no player built; see $out/build.log" >&2; exit 1; }

git -C "$project" diff --binary --submodule=diff > "$out/source.patch"
git -C "$project" status --porcelain > "$out/source-status.txt"
git -C "$project" submodule status --recursive > "$out/submodules.txt"

{
    echo "built: $(date -u +%FT%TZ)"
    echo "unity_sha256: $(sha256sum "$unity" | cut -d' ' -f1)"
    echo "social_sim_unity: $(git -C "$project" rev-parse HEAD)"
    echo "source_patch_sha256: $(sha256sum "$out/source.patch" | cut -d' ' -f1)"
} > "$out/manifest.txt"
echo "player: $out/sean.x86_64"

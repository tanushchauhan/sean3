#!/usr/bin/env bash
# Build a Linux player and retain enough evidence to diagnose success or failure.
#   scripts/build_unity_player.sh <unity-editor-binary> <project> <new-or-empty-output-dir>
set -euo pipefail

if [ "$#" -ne 3 ]; then
    echo "usage: $0 <unity-editor-binary> <project> <output-dir>" >&2
    exit 2
fi
unity=$1 project=$2 out=$3
if [ ! -x "$unity" ] || [ ! -d "$project" ]; then
    echo "Unity editor must be executable and project must be a directory" >&2
    exit 2
fi
if [ -e "$out" ] && { [ ! -d "$out" ] || [ -n "$(find "$out" -mindepth 1 -maxdepth 1 -print -quit)" ]; }; then
    echo "refusing to reuse non-empty output directory: $out" >&2
    exit 2
fi
mkdir -p "$out"
unity="$(cd "$(dirname "$unity")" && pwd -P)/$(basename "$unity")"
project=$(cd "$project" && pwd -P)
out=$(cd "$out" && pwd -P)

# Keep package fetching independent of personal Git rewrites. Unity's C# compiler
# also needs invariant globalization in minimal Linux environments.
export GIT_CONFIG_GLOBAL=/dev/null
export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1

manifest="$out/manifest.txt"
capture_status() {
    local label=$1
    git -C "$project" status --porcelain=v2 --untracked-files=all > "$out/$label-source-status.txt" 2>&1 || true
    git -C "$project" submodule status --recursive > "$out/$label-submodules.txt" 2>&1 || true
    git -C "$project" submodule foreach --quiet --recursive \
        'printf "[%s]\n" "$displaypath"; git status --porcelain=v2 --untracked-files=all' \
        > "$out/$label-submodule-status.txt" 2>&1 || true
    git -C "$project" diff --binary --submodule=diff > "$out/$label-source.diff" 2>&1 || true
    git -C "$project" diff --cached --binary --submodule=diff > "$out/$label-source-staged.diff" 2>&1 || true
    git -C "$project" submodule foreach --quiet --recursive \
        'printf "[%s]\n" "$displaypath"; git diff --binary' \
        > "$out/$label-submodule-diff.txt" 2>&1 || true
    if [ -d "$project/Assets" ]; then
        find "$project/Assets" -type f ! -name '*.meta' ! -name '.DS_Store' -print0 |
            while IFS= read -r -d '' asset; do
                [ -f "$asset.meta" ] || printf '%s\n' "${asset#"$project"/}"
            done > "$out/$label-assets-missing-meta.txt"
    else
        : > "$out/$label-assets-missing-meta.txt"
    fi
}
hash_if_file() {
    local path=$1
    if [ -f "$path" ]; then sha256sum "$path" | awk '{print $1}'; else printf 'missing'; fi
}
write_interrupted_failure() {
    local rc=$?
    if [ -f "$manifest" ] && ! grep -q '^status: success$\|^status: failed$' "$manifest"; then
        printf 'status: failed\nfinished_utc: %s\nscript_exit_code: %s\n' "$(date -u +%FT%TZ)" "$rc" >> "$manifest"
    fi
}

editor_sha=$(hash_if_file "$unity")
editor_version=$("$unity" -version 2>&1 | head -n 1 || true)
source_commit=$(git -C "$project" rev-parse HEAD 2>/dev/null || printf 'unavailable')
capture_status before
lock_hash=$(hash_if_file "$project/Packages/packages-lock.json")
manifest_tmp="$manifest.tmp"
{
    printf 'status: building\n'
    printf 'started_utc: %s\n' "$(date -u +%FT%TZ)"
    printf 'project: %s\n' "$(cd "$project" && pwd -P)"
    printf 'source_commit: %s\n' "$source_commit"
    printf 'host_platform: %s\n' "$(uname -srm)"
    printf 'unity_editor: %s\n' "$(cd "$(dirname "$unity")" && pwd -P)/$(basename "$unity")"
    printf 'unity_editor_version: %s\n' "$editor_version"
    printf 'unity_editor_sha256: %s\n' "$editor_sha"
    printf 'packages_manifest_sha256: %s\n' "$(hash_if_file "$project/Packages/manifest.json")"
    printf 'packages_lock_sha256: %s\n' "$lock_hash"
    if [ -n "${UNITY_LICENSE:-}" ]; then license_configured=yes; else license_configured=no; fi
    printf 'environment_unity_license_configured: %s\n' "$license_configured"
    printf 'environment_ci: %s\n' "${CI:-unset}"
    printf 'started_git_config_global: %s\n' "${GIT_CONFIG_GLOBAL:-unset}"
    printf 'started_dotnet_system_globalization_invariant: %s\n' "${DOTNET_SYSTEM_GLOBALIZATION_INVARIANT:-unset}"
    printf 'unity_build_command: xvfb-run -a UNITY -batchmode -quit -projectPath PROJECT -buildTarget Linux64 -buildLinux64Player OUTPUT/sean.x86_64\n'
    printf 'untracked_content_capture: not captured; use clean_build_unity_player.sh for committed-source-only provenance\n'
} > "$manifest_tmp"
mv "$manifest_tmp" "$manifest"
trap write_interrupted_failure EXIT

build_rc=0
xvfb-run -a "$unity" -batchmode -quit -projectPath "$project" -buildTarget Linux64 \
    -buildLinux64Player "$out/sean.x86_64" -logFile "$out/build.log" || build_rc=$?
capture_status after

player_state=missing
player_sha=missing
player_size=0
if [ -f "$out/sean.x86_64" ]; then
    player_state=present
    player_sha=$(hash_if_file "$out/sean.x86_64")
    player_size=$(stat -c %s "$out/sean.x86_64" 2>/dev/null || stat -f %z "$out/sean.x86_64")
fi
find "$out" -type f \
    ! -name 'build.log' ! -name 'manifest.txt' ! -name 'manifest.txt.tmp' \
    ! -name 'player-tree.sha256' ! -name '*-source-status.txt' \
    ! -name '*-submodule-status.txt' ! -name '*-submodule-diff.txt' ! -name '*-submodules.txt' \
    ! -name '*-assets-missing-meta.txt' ! -name '*.diff' -print0 |
    sort -z | xargs -0 -r sha256sum > "$out/player-tree.sha256"
final_status=failed
if [ "$build_rc" -eq 0 ] && [ -x "$out/sean.x86_64" ]; then final_status=success; fi
{
    printf 'status: %s\n' "$final_status"
    printf 'finished_utc: %s\n' "$(date -u +%FT%TZ)"
    printf 'unity_exit_code: %s\n' "$build_rc"
    printf 'source_commit_after: %s\n' "$(git -C "$project" rev-parse HEAD 2>/dev/null || printf 'unavailable')"
    printf 'player_state: %s\n' "$player_state"
    printf 'player_sha256: %s\n' "$player_sha"
    printf 'player_size_bytes: %s\n' "$player_size"
    printf 'packages_manifest_sha256_after: %s\n' "$(hash_if_file "$project/Packages/manifest.json")"
    printf 'packages_lock_sha256_after: %s\n' "$(hash_if_file "$project/Packages/packages-lock.json")"
} >> "$manifest"

if [ "$final_status" != success ]; then
    echo "Unity player build failed (exit $build_rc); evidence is in $out" >&2
    if [ "$build_rc" -eq 0 ]; then build_rc=1; fi
    exit "$build_rc"
fi
echo "player: $out/sean.x86_64"

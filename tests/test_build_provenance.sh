#!/usr/bin/env bash
# Regression checks for stale-output refusal and failure evidence.
set -euo pipefail
repo_root=$(cd "$(dirname "$0")/.." && pwd -P)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/bin" "$tmp/source/Assets" "$tmp/source/Packages"
cat > "$tmp/bin/xvfb-run" <<'SH'
#!/usr/bin/env bash
shift # -a
exec "$@"
SH
cat > "$tmp/bin/fake-unity" <<'SH'
#!/usr/bin/env bash
if [ "${1:-}" = -version ]; then echo 'Unity 2022.3.test'; exit 0; fi
mode=${FAKE_UNITY_MODE:-failure}
output=''
while [ "$#" -gt 0 ]; do
    if [ "$1" = -logFile ]; then printf 'synthetic Unity %s\n' "$mode" > "$2"; fi
    if [ "$1" = -buildLinux64Player ]; then output=$2; fi
    shift
    if [ "$#" -gt 0 ] && [ "${1:-}" = -buildLinux64Player ]; then output=$2; fi
done
case "$mode" in
    failure) exit 17 ;;
    no-player) exit 0 ;;
    success)
        printf '#!/bin/sh\nexit 0\n' > "$output"
        chmod +x "$output"
        mkdir -p "${output%/*}/sean_Data"
        printf 'payload\n' > "${output%/*}/sean_Data/data.bin"
        printf 'runtime\n' > "${output%/*}/UnityPlayer.so"
        printf 'crash handler\n' > "${output%/*}/UnityCrashHandler64"
        exit 0
        ;;
esac
SH
chmod +x "$tmp/bin/xvfb-run" "$tmp/bin/fake-unity"
printf '{"dependencies":{}}\n' > "$tmp/source/Packages/manifest.json"
printf '{"dependencies":{}}\n' > "$tmp/source/Packages/packages-lock.json"
printf 'committed source\n' > "$tmp/source/Assets/scene.txt"
mkdir -p "$tmp/submodule"
git -C "$tmp/submodule" init -q
printf 'pinned submodule\n' > "$tmp/submodule/content.txt"
git -C "$tmp/submodule" -c user.name=test -c user.email=test@example.invalid add .
git -C "$tmp/submodule" -c user.name=test -c user.email=test@example.invalid commit -qm 'submodule fixture'
git -C "$tmp/source" init -q
git -C "$tmp/source" -c user.name=test -c user.email=test@example.invalid add .
git -C "$tmp/source" -c user.name=test -c user.email=test@example.invalid commit -qm 'fixture'
git -c protocol.file.allow=always -C "$tmp/source" submodule add -q "$tmp/submodule" Assets/ExternalAssets/Fixture
git -C "$tmp/source" -c user.name=test -c user.email=test@example.invalid commit -qam 'add local submodule'
commit=$(git -C "$tmp/source" rev-parse HEAD)

# Dirty source files and an existing Library are not copied into the clean clone.
mkdir -p "$tmp/source/Library"
printf 'must not be cloned\n' > "$tmp/source/Library/cache.bin"
printf 'untracked source\n' > "$tmp/source/untracked.txt"
printf 'dirty edit\n' >> "$tmp/source/Assets/scene.txt"
sed -i.bak 's#'"$tmp/submodule"'#https://invalid.example/fixture.git#' "$tmp/source/.gitmodules"
rm -f "$tmp/source/.gitmodules.bak"
cat >> "$tmp/source/.gitmodules" <<'EOF'

[submodule "dirty-only"]
	path = bogus
	url = https://invalid.example/bogus.git
EOF
if PATH="$tmp/bin:$PATH" "$repo_root/scripts/clean_build_unity_player.sh" \
    "$tmp/bin/fake-unity" "$tmp/source" "$commit" "$tmp/clean-build"; then
    echo 'expected synthetic Unity failure' >&2
    exit 1
fi
test -f "$tmp/clean-build/build/manifest.txt"
grep -q '^status: failed$' "$tmp/clean-build/build/manifest.txt"
grep -q '^unity_exit_code: 17$' "$tmp/clean-build/build/manifest.txt"
test -f "$tmp/clean-build/build/build.log"
grep -q 'synthetic Unity failure' "$tmp/clean-build/build/build.log"
test -f "$tmp/clean-build/source-origin-status.txt"
grep -q 'untracked.txt' "$tmp/clean-build/source-origin-status.txt"
grep -q '.gitmodules' "$tmp/clean-build/source-origin-status.txt"
test ! -e "$tmp/clean-build/project/Library"
test ! -e "$tmp/clean-build/project/untracked.txt"
test ! -e "$tmp/clean-build/project/Assets/scene.txt.meta"
test "$(git -C "$tmp/clean-build/project/Assets/ExternalAssets/Fixture" rev-parse HEAD)" = \
    "$(git -C "$tmp/source" ls-tree HEAD Assets/ExternalAssets/Fixture | awk '{print $3}')"
grep -q 'https://invalid.example' "$tmp/clean-build/project/.gitmodules" && exit 1

# Success hashes include the player binary, Unity data files, and runtime library.
FAKE_UNITY_MODE=success PATH="$tmp/bin:$PATH" "$repo_root/scripts/build_unity_player.sh" \
    "$tmp/bin/fake-unity" "$tmp/clean-build/project" "$tmp/success-build"
grep -q '^status: success$' "$tmp/success-build/manifest.txt"
grep -q 'sean_Data/data.bin' "$tmp/success-build/player-tree.sha256"
grep -q 'UnityPlayer.so' "$tmp/success-build/player-tree.sha256"
grep -q 'UnityCrashHandler64' "$tmp/success-build/player-tree.sha256"

# A zero exit without a player is still a failed build and returns nonzero.
if FAKE_UNITY_MODE=no-player PATH="$tmp/bin:$PATH" "$repo_root/scripts/build_unity_player.sh" \
    "$tmp/bin/fake-unity" "$tmp/clean-build/project" "$tmp/no-player-build"; then
    echo 'expected missing-player build failure' >&2
    exit 1
fi
grep -q '^status: failed$' "$tmp/no-player-build/manifest.txt"

# A prior player must be rejected before any build can overwrite it.
mkdir -p "$tmp/stale-output"
printf 'old player\n' > "$tmp/stale-output/sean.x86_64"
if PATH="$tmp/bin:$PATH" "$repo_root/scripts/build_unity_player.sh" \
    "$tmp/bin/fake-unity" "$tmp/source" "$tmp/stale-output"; then
    echo 'expected stale output refusal' >&2
    exit 1
fi
grep -q 'old player' "$tmp/stale-output/sean.x86_64"

echo 'build provenance regression checks passed'

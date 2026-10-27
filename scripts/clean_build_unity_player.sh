#!/usr/bin/env bash
# Clone committed source locally, validate a fresh Unity checkout, then build.
#   clean_build_unity_player.sh <unity-editor> <source-unity-repo> <expected-commit> <new-output-dir>
set -euo pipefail

if [ "$#" -ne 4 ]; then
    echo "usage: $0 <unity-editor> <source-unity-repo> <expected-commit> <new-output-dir>" >&2
    exit 2
fi
unity=$1 source=$2 expected=$3 out=$4
if [ ! -x "$unity" ] || [ ! -d "$source" ] || ! git -C "$source" rev-parse --git-dir >/dev/null 2>&1; then
    echo "Unity editor must be executable and source must be a Git checkout" >&2
    exit 2
fi
if [ -e "$out" ]; then
    echo "refusing to reuse output directory: $out" >&2
    exit 2
fi
unity="$(cd "$(dirname "$unity")" && pwd -P)/$(basename "$unity")"
source=$(cd "$source" && pwd -P)
mkdir -p "$(dirname "$out")"
out="$(cd "$(dirname "$out")" && pwd -P)/$(basename "$out")"
source_head=$(git -C "$source" rev-parse HEAD)
if [ "$source_head" != "$expected" ]; then
    echo "source HEAD $source_head does not match expected commit $expected" >&2
    exit 2
fi

mkdir "$out"
project="$out/project"
mkdir "$project"

# Keep provenance for the existing source checkout. Dirty working files are
# recorded, but never copied: the clone below contains committed objects only.
git -C "$source" status --porcelain=v2 --untracked-files=all > "$out/source-origin-status.txt"
git -C "$source" submodule status --recursive > "$out/source-origin-submodules.txt" 2>&1 || true
git -C "$source" submodule foreach --quiet --recursive \
    'printf "[%s]\n" "$displaypath"; git status --porcelain=v2 --untracked-files=all' \
    > "$out/source-origin-submodule-status.txt" 2>&1 || true
git -C "$source" diff --binary --submodule=diff > "$out/source-origin.diff"
git -C "$source" submodule foreach --quiet --recursive \
    'printf "[%s]\n" "$displaypath"; git diff --binary' \
    > "$out/source-origin-submodule.diff" 2>&1 || true

git clone --no-hardlinks --no-checkout "$source" "$project" > "$out/clone.log" 2>&1
git -C "$project" checkout --detach "$expected" >> "$out/clone.log" 2>&1

# Populate every pinned gitlink from its already-present local source checkout.
# This avoids relying on GitHub URLs or SSH credentials during the clean build.
populate_submodules() {
    local source_repo=$1 destination_repo=$2 config_line key name path gitlink source_submodule dest_head
    [ -f "$destination_repo/.gitmodules" ] || return 0
    while IFS= read -r config_line; do
        key=${config_line%% *}
        path=${config_line#* }
        name=${key#submodule.}
        name=${name%.path}
        source_submodule="$source_repo/$path"
        if [ ! -d "$source_submodule" ] || ! git -C "$source_submodule" rev-parse --git-dir >/dev/null 2>&1; then
            echo "source submodule is not initialized: $source_submodule" >&2
            return 1
        fi
        gitlink=$(git -C "$destination_repo" ls-tree HEAD -- "$path" | awk '$1 == "160000" {print $3}')
        if [ -z "$gitlink" ]; then
            echo "submodule path is not a pinned gitlink: $path" >&2
            return 1
        fi
        source_head=$(git -C "$source_submodule" rev-parse HEAD)
        if [ "$source_head" != "$gitlink" ]; then
            echo "source submodule $path is at $source_head, expected $gitlink" >&2
            return 1
        fi
        git -C "$destination_repo" config "submodule.$name.url" "$source_submodule"
        git -c protocol.file.allow=always -C "$destination_repo" submodule update --init -- "$path" >> "$out/clone.log" 2>&1
        dest_head=$(git -C "$destination_repo/$path" rev-parse HEAD)
        if [ "$dest_head" != "$gitlink" ]; then
            echo "cloned submodule $path is at $dest_head, expected $gitlink" >&2
            return 1
        fi
        populate_submodules "$source_submodule" "$destination_repo/$path"
    done < <(git -C "$destination_repo" config -f .gitmodules --get-regexp '^submodule\..*\.path$' || true)
}
populate_submodules "$source" "$project"

actual_head=$(git -C "$project" rev-parse HEAD)
if [ "$actual_head" != "$expected" ]; then
    echo "fresh checkout is at $actual_head, expected $expected" >&2
    exit 1
fi
if [ -n "$(git -C "$project" status --porcelain=v2 --untracked-files=all)" ]; then
    echo "fresh checkout is dirty before Unity import; see $out/project status" >&2
    git -C "$project" status --short --untracked-files=all >&2
    exit 1
fi
if ! git -C "$project" submodule foreach --quiet --recursive \
    'test -z "$(git status --porcelain=v2 --untracked-files=all)"'; then
    echo "fresh checkout has a dirty submodule" >&2
    exit 1
fi
if git -C "$project" submodule status --recursive | grep -Eq '^[+-U]'; then
    echo "fresh checkout has an uninitialized or mismatched submodule" >&2
    exit 1
fi
if find "$project" -type d -name Library -print -quit | grep -q .; then
    echo "fresh checkout unexpectedly contains a Unity Library directory" >&2
    exit 1
fi
if find "$project" -type d -name UserSettings -print -quit | grep -q .; then
    echo "fresh checkout unexpectedly contains Unity UserSettings" >&2
    exit 1
fi

{
    printf 'expected_commit: %s\n' "$expected"
    printf 'fresh_checkout_commit: %s\n' "$actual_head"
    printf 'source_dirty_files_recorded: %s\n' "$(wc -l < "$out/source-origin-status.txt" | tr -d ' ')"
    printf 'fresh_checkout_status: clean\n'
    printf 'fresh_checkout_library: absent\n'
    printf 'fresh_checkout_submodules: matched\n'
} > "$out/clean-checkout.txt"

set +e
"$(dirname "$0")/build_unity_player.sh" "$unity" "$project" "$out/build"
build_rc=$?
set -e
printf 'build_wrapper_exit_code: %s\n' "$build_rc" >> "$out/clean-checkout.txt"
exit "$build_rc"

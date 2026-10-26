#!/usr/bin/env bash
set -euo pipefail

player=$1
shift
compat=$(mktemp -d)
trap 'rm -rf "$compat"' EXIT

# Older AssimpNet builds request the unversioned Linux loader library.
loader=$(ldconfig -p | awk '$1 == "libdl.so.2" && /x86-64/ && !path {path=$NF} END {print path}')
if [ -n "$loader" ]; then
    ln -s "$loader" "$compat/libdl.so"
    export LD_LIBRARY_PATH="$compat${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
"$player" "$@"

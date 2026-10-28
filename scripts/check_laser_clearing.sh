#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then echo 'Usage: check_laser_clearing.sh <new-results-directory>' >&2; exit 2; fi
scripts=$(cd "$(dirname "$0")" && pwd)
mkdir "$1"; results=$(realpath "$1")
image=${SEAN_ROS_IMAGE:-localhost/sean3-humble:dev}
docker inspect --format '{{.Id}}' "$image" > "$results/image-id.txt"
for profile in legacy-zero infinity-disabled infinity-full-marking infinity-clearing split-clearing; do
    docker run --rm --network none -e ROS_DOMAIN_ID=91 -v "$scripts/../tests:/tests:ro" -v "$results:/results" \
        "$image" bash -c 'source /opt/ros/humble/setup.bash; python3 /tests/laser_clearing_check.py "/results/$1" --profile "$1"' \
        bash "$profile" > "$results/$profile-console.log" 2>&1
done
python3 - "$results" <<'PY'
import json,pathlib,sys
root=pathlib.Path(sys.argv[1]);profiles=['legacy-zero','infinity-disabled','infinity-full-marking','infinity-clearing','split-clearing']
a=[json.loads((root/p/p/'summary.json').read_text()) for p in profiles]
passed=(all(e['clean_shutdown'] for e in a) and not a[0]['cleared'] and not a[1]['cleared'] and a[2]['cleared'] and not a[2]['no_artificial_ring']
        and a[3]['cleared'] and a[3]['no_artificial_ring'] and not a[3]['far_finite_return_marked']
        and a[4]['cleared'] and a[4]['no_artificial_ring'] and a[4]['far_finite_return_marked'])
result=dict(passed=passed,profiles=a);(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(result);assert passed
PY

# Controller integration: first execution milestone — October 29, 2026

Phase A's bounded baseline is runtime validated on robovision. Phase B's
scene-level boundary core and draft configuration schema are implemented and
tested, with production avatar/ROS wiring still pending. ORCA and STARS have
not been implemented; the three-controller milestone remains incomplete.

## Sources and changes

| Repository | Branch | Starting/current HEAD |
| --- | --- | --- |
| Workspace | `feature/ros2-environment` | `cf69676f9e7f3183ba464498fcd27456cd8b7704` |
| Unity sibling | `feature/unity-2022-upgrade` | `537ec00d06864e15611c804daf01437c11aa85e9` |
| ROS sibling | `feature/ros2-port` | `234262d28f7f426020fa198aa3f0dedefb04e117` |

Changes are uncommitted and synced explicitly to robovision. Unity adds
`Assets/Scripts/SEAN/Scenario/Controllers/` (standalone assembly, immutable
snapshot/decision types, scene controller core), `SceneControllerTests.cs`,
their metadata, and the test assembly reference. No production scene, avatar,
SF controller, ROS code, package version or workspace component pin changed.
The workspace adds the [contract](../protocols/scene-controller-contract.md),
[decision record](../decisions/controller-integration.md),
`configs/experiments/schema.json`, a frozen historical crowd reference, and
`scripts/capture_source_inventory.py`. The README/validation and root plan
record the bounded progress.

The remote workspace was one commit behind and was fast-forwarded using a Git
bundle. Component HEADs already matched. All seven new Unity source/metadata
files have matching local/remote SHA-256 values; the modified test assembly
reference matches as well. The remote Unity checkout retains previously dirty
Rocketbox child metadata/UserSettings, so its aggregate dirty digest differs
from local. The inventory records the child repository separately. Remote
workspace crash blobs/AppleDouble files and local ROS `.DS_Store`, child state,
and historical `REVIEW_2026-10-26.md` were preserved.

## Runtime baseline and validation

Robovision: Linux x86_64, eight Quadro RTX 6000 GPUs, driver 580.178.04, Python
3.12.3, rootless Podman (also exposed as docker), licensed Unity 2022.3.62f3.
No GPU training was performed. Port 10000 was occupied; all new runtime checks
used the available port 10371 and the existing runners' isolated containers.

Reused accepted player:
`/scratch/tchauhan/sean3/fresh-20261029/sean3/builds/537ec00-20261029-102715/sean.x86_64`.
Its manifest records source `537ec00`, successful build, editor/package hashes
and executable hash
`0bfe51325720c950b4ad75ce7c3b65595fd7e939908520ec33600919919327a8`.
All 175 payload checksums were reverified. The original fresh-setup report
supplies build acceptance; the build helper's manifest explicitly warns that
untracked source content was not captured. No new candidate player was built.
ROS image `localhost/sean3-humble:local`, ID
`17c76881dfafd5b587cd12e5c28f712b172ec714d930f7b7e689f296f9687afd`.
The documented setup/build was already available; `doctor` with explicit
player/ROS source/port passed every check, so no rebuild was needed for Phase A.

| Check | Outcome | Scope |
| --- | --- | --- |
| Python harness, local and remote | 54/54 pass on each | Existing analysis/harness regressions |
| Final Unity EditMode suite | 66/66 pass | 47 existing + 19 new boundary tests |
| Existing navigation smoke | 3/3 pass | Startup, task reset, scene reload; seed 7 |
| Existing four-person encounter subset | 4/4 pass | Aisle, seed 7, both mirrors, parked + Nav2 |
| Encounter person-goal completions | 16/16 | Existing 45 simulation-second deadline |
| Actual Nav2 encounter actions | 2/2 pass | Goal error 0.336/0.347 m from action results |
| Physical encounter contacts | 0 | All recorded person/robot/obstacle categories |
| Minimum sampled robot-body clearance | 0.309 m | Four selected episodes only |
| Transport/process cleanup | Pass | Navigation + encounters, no forced player termination |
| Draft JSON schema | Valid | Local Draft202012Validator schema check only |

Navigation goal errors were 0.326, 0.330 and 0.326 m. Encounter durations were
16.26, 16.22, 38.82 and 30.88 simulation seconds. `headroom_demonstrated=false`
is retained: this subset contains no yielding/oblivious pairs and establishes
no policy advantage. No thresholds or deadlines were changed. This is a small
development baseline, not another full qualification or held-out evaluation.

The first Unity invocation passed 65 tests but logged the existing Assimp
`libdl.so` loader exception. It remains as `unity-tests.*`. After adding the
clock-regression fail-stop test, the final 66-test invocation used the existing
`run_unity_player.sh` compatibility wrapper; its separate `unity-final.*`
artifacts are authoritative. Core tests exercise a deterministic planar sink,
not animation or production physical following.

## Commands and evidence

From `/scratch/tchauhan/sean3/sean3`, with the installed editor/player above:

```sh
./sean3 doctor --headless --port 10371 --ros-source ../social_sim_ros \
  --player ../fresh-20261029/sean3/builds/latest/sean.x86_64
python3 -m unittest discover -s tests -p 'test_*.py'

SEAN_ROS_IMAGE=localhost/sean3-humble:local SEAN_TCP_PORT=10371 \
  bash scripts/check_unity_navigation.sh \
  /scratch/tchauhan/sean3/fresh-20261029/sean3/builds/latest/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros NEW_NAV_RESULTS

SEAN_ROS_IMAGE=localhost/sean3-humble:local SEAN_TCP_PORT=10371 \
  SEAN_ENCOUNTER_SEEDS=7 SEAN_ENCOUNTER_LAYOUTS=aisle \
  SEAN_ENCOUNTER_MODES=parked,nav2 bash scripts/check_warehouse_encounters.sh \
  /scratch/tchauhan/sean3/fresh-20261029/sean3/builds/latest/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros NEW_ENCOUNTER_RESULTS

GIT_CONFIG_GLOBAL=/dev/null DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 \
  bash scripts/run_unity_player.sh \
  /scratch/tchauhan/sean3/unity/unity-2022.3.62f3/Editor/Unity \
  -batchmode -nographics -projectPath /scratch/tchauhan/sean3/social_sim_unity \
  -runTests -testPlatform EditMode -assemblyNames SEAN.Editor.Tests \
  -testResults NEW_TEST_RESULTS.xml -logFile NEW_TEST_RESULTS.log

python3 scripts/capture_source_inventory.py . ../social_sim_unity ../social_sim_ros
```

Always use new output paths, inspect current port/process occupancy, and
serialize players/editors/overlay jobs. Runtime evidence is under
`/scratch/tchauhan/sean3/validation/controller-integration-20261029/`:
`doctor.log`, `navigation/`, `encounters/`, `unity-final.xml/log`, source
inventory, and payload verification. Local copies of XML, JSON and doctor/build
provenance are in `sean3/.sean3/evidence/controller-integration-20261029/`.
Raw video/logs remain on robovision. The
[manifest](2026-10-29-controller-integration-manifest.json) records artifact and
changed-source hashes. The inventory helper is read-only; it does not include
ignored files or recursively fingerprint dirty submodule contents unless those
child repositories are explicitly supplied.

The [frozen crowded reference](../../configs/experiments/regressions/crowded-seed1001.json)
retains configuration, route summaries, contact line and SHA-256 hashes for
original metrics/log/video in
`/scratch/tchauhan/sean3/validation/nav2-tolerance-20261029/pedestrians/t-seed1001/`.
This preserves the recorded stationary-Kuri/Agent_10 contact as a development
diagnostic. It is not a deterministic replay, a new failure reproduction, or
an assertion about its cause.

## Remaining gates and next task

Phase B still needs the opt-in production capture and batch sink, animation
following/reset tests, synchronous simulation owner, bounded worker transport
and exclusive robot command enforcement. The schema is a design contract;
the launcher does not consume it. Do not treat the fake sink as full-contract
runtime acceptance.

Next executable task: connect a fake scene controller to actual animated
pedestrians at one physics boundary, without allowing `Base.Update` to integrate
them a second time; validate reset/expiry/worker loss and the default SF path.
Then select and integrate one scene-wide ORCA solver. STARS learned validation
requires a designated trained checkpoint with matching preprocessing/config,
hashes and reuse terms. The inspected source/runtime limits and durable model
checkouts are recorded in the decision record. No STARS replacement, PPO
training or first three-controller comparison is claimed.

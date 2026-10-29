# Animated controller integration and ORCA pilot — October 29, 2026

The scene-level contract now drives production animated pedestrians through
physical velocity targets. ORCA is implemented as an explicit controller choice.
The final matched-actuator pilot is complete: Social Forces passes 4/4 strict
encounters; ORCA passes 3/4. Both complete all sixteen pedestrian routes with
zero recorded physical contacts. One mirrored ORCA/Nav2 encounter fails the
robot goal gate. This is an experimental integration result, not qualification
of ORCA as a replacement or a three-controller comparison.

## Sources and implementation

| Component | Executed revision |
| --- | --- |
| Unity, `feature/unity-2022-upgrade` | `aa7bf262fd977ddfa2bde04b15e867a0cf289173` |
| Workspace runner, `feature/ros2-environment` | `9878c7d243c81b01249df9832c0de2da3149f0ca` (full revision verified in manifest) |
| ROS, `feature/ros2-port` | `234262d28f7f426020fa198aa3f0dedefb04e117` |
| RVO2-CS | `v2.0.1`, `5b7147d36d5cc6310c8e74c6955145c0fdc5fe06` |

Implementation was committed and pushed incrementally: `aec5d38` adds the
boundary core, `60e8f8c` adds the joint animated path, `67d97af` adds the ORCA
solver/geometry adapter, and `aa7bf26` fixes the actuator. Workspace commits
`bfff3ef`, `0b66a41`, and `9878c7d` record the baseline, expose explicit controller
selection, and separate pedestrian actuation. Repository versions were synced
to robovision using incremental bundles, verified matching files, and
fast-forwards. Recovery stashes and unrelated Rocketbox metadata, UserSettings,
crash blobs, AppleDouble files and the local historical review were retained.

Unity changes include joint snapshots/decisions, one coordinated solver update,
stable actor registration, actual-state feedback, task/population reset hooks,
expiry/failure stopping, a direct velocity actuator, audited NavMesh boundary
construction, the ORCA adapter, and animated/core/geometry tests. Workspace
changes add explicit controller/actuator options, old-player confirmation,
matched encounter support, provenance/lifecycle validation and motion diagnostics.
No ROS or unrelated package upgrade was required.

The Apache-2.0 managed solver is vendored with original notices, source hashes
and declared patches. A serial joint solve avoids worker/wait-handle allocation;
pedestrians take full avoidance responsibility against the externally controlled
robot and inactive context actors. Active pedestrians remain reciprocal.
Solver-integrated positions and robot outputs are discarded. See the
[controller protocol](../protocols/pedestrian-controllers.md) for exact settings,
geometry conventions and limitations.

## Actuator defect and correction

The first committed pilot (`67d97af`) passed the original contact/goal gates
with SF 4/4 and ORCA 4/4, but raw ORCA traces contained large uncommanded
position/rigidbody-velocity changes. The initial following-error analysis reached
7.386 m/s. Those passes are retained as diagnostic evidence, not current
actuator acceptance or evidence of good motion quality.

`VelocityTargetsV1` disables animation's translation and applies the controller's
planar rigidbody velocity, retaining gravity and collision response. Animation
still supplies appearance. It adds no independent position integration,
teleportation, clipping or corrective avoidance. The actuator is independently
selected for **both** SF and ORCA in the final comparison. SF's ordinary
`AnimatedRootMotionV1` default remains available and unchanged in intent.

Before the final pilot, the animated regression required actual planar speed
at most 0.61 m/s for a 0.6 m/s target, plus immediate reset/failure stopping and
less than 0.005 m residual planar drift after worker loss. The stronger failure
test injects the exception while avatars have nonzero targets, without disabling
or clearing the owner first. All these tests pass. In final runtime traces,
maximum measured rigidbody planar speed was 0.6000001 m/s on each controller;
position-derived speed was at most 0.600113 m/s. Maximum moving target-following
error was 0.000148 m/s for SF and 0.000139 m/s for ORCA in this fixture.

Moving/stationary error strata use a 0.01 m/s cutoff on either target or achieved
speed. Post-physics interval-ending targets are aligned with position-derived
velocities. The old root-motion pilot and its original analyzer outputs remain
unchanged; do not pool its actuator condition with this comparison.

## Final bounded results

The existing aisle fixture uses seed 7, both lateral mirrors, parked and actual
Nav2 robot modes, the same four avatars/starts/goals/footprints/contact material,
0.02-second physics, and the unchanged 45 simulation-second deadline. ORCA uses
0.1-second decisions, 5 m neighbour distance, 64 neighbours, and 2.5-second actor
and obstacle horizons. This is development data, not a fresh held-out seed.

| Measure | Social Forces + VelocityTargetsV1 | ORCA + VelocityTargetsV1 |
| --- | --- | --- |
| Strict episode passes | 4/4 | 3/4 |
| Pedestrian goal completions | 16/16 | 16/16 |
| Actual Nav2 actions passing | 2/2 | 1/2 |
| All recorded physical contact categories | 0 | 0 |
| Minimum sampled robot/body clearance | 0.343 m | 0.0665 m |
| Minimum sampled person/person clearance | 0.688 m | 0.693 m |
| Parked episode durations, mirrors -1/+1 | 13.42 / 13.42 s | 12.58 / 12.58 s |
| Nav2 episode durations, mirrors -1/+1 | 36.26 / 36.86 s | 34.42 / 45.00 s |

The failing ORCA case is seed 7, aisle, mirror +1, Nav2, episode 3. Nav2 reports
status 6 (aborted); the robot remains 6.711 m from its goal at the fixture's
45-second limit. All four pedestrians reached their goals by 12.58 s. Minimum
robot/body clearance is positive (0.0665 m), and no contacts were recorded.
The longest 0.1 m robot-anchor pause is 26.94 s. No cause is assigned from this
pilot alone. The failed case is retained in raw results and summary, without
retries, substituted placements or changed gates.

All eight expected episodes are attributable, finite and complete, with
controller identities/sequences and actual requested parameters. ORCA has no
worker fault. Both encounter runs pass full transport/script-log audits and
clean shutdown, with no forced player kills or leftover test containers.
The strict ORCA encounter runner correctly exits 1 because of the behavioral
failure; the combined validation sequence records that failure rather than
claiming an overall pass. `headroom_demonstrated=false` is retained on both
conditions; this subset has no yielding/oblivious pairs.

The final committed candidate also passes 77 Unity tests, 60 harness tests,
three ordinary default-actuator navigation stages (startup/task/scene reset),
and all 177 player payload checksums. Navigation goal errors are 0.322, 0.331
and 0.322 m. The player was built successfully from the committed source in the
existing cached Unity project; this is not another clean-source asset import.

## Reproduction and evidence

Robovision player:
`/scratch/tchauhan/sean3/sean3/builds/aa7bf26-20261029-154253/sean.x86_64`.
Unity is 2022.3.62f3; ROS is Humble in the existing
`localhost/sean3-humble:local` image. The container image observed during the
final SF run and build/source/artifact hashes are recorded in the manifest.
Both model and actual robot geometry assumptions are explicit: ORCA captured
seven `NavMeshBoundaryV1` loops and a 0.226274 m conservative robot-body radius.
These boundaries include baked navigation clearance; physical metrics still
use the actual capsules/wheels. No collision-freedom guarantee follows.

The exact validation sequence is saved on robovision as
`/scratch/tchauhan/sean3/sean3-validate-velocity-actuator.sh`; it uses the
established launcher and validation runners. The matched command is:

```sh
# Run separately for controller=social_forces and controller=orca;
# use a fresh result directory each time.
SEAN_ROS_IMAGE=localhost/sean3-humble:local SEAN_TCP_PORT=10371 \
  SEAN_PEDESTRIAN_CONTROLLER="$controller" SEAN_PEDESTRIAN_ACTUATION=velocity_body \
  SEAN_ENCOUNTER_SEEDS=7 SEAN_ENCOUNTER_LAYOUTS=aisle \
  SEAN_ENCOUNTER_MODES=parked,nav2 bash scripts/check_warehouse_encounters.sh \
  /scratch/tchauhan/sean3/sean3/builds/aa7bf26-20261029-154253/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros NEW_RESULTS
```

Final raw data, latencies, reports, Nav2 evidence, logs, XML, source inventory,
payload verification and progress are under
`/scratch/tchauhan/sean3/validation/velocity-actuator-final-20261029/`.
Local JSON/XML/build-provenance copies are under
`sean3/.sean3/evidence/velocity-actuator-final-20261029/`. Original root-motion
pilot evidence is under `validation/orca-committed-20261029/` on robovision and
the corresponding local evidence directory. Earlier animated/default-path
validation is retained under `validation/joint-avatar-20261029/`.
The [machine-readable manifest](2026-10-29-orca-controller-manifest.json)
identifies exact versions, source and raw evidence hashes and per-case results.
Large raw data and players are kept out of Git.

## Scope and next dependencies

This is a bounded, one-seed engineering/behavioral pilot. No human-realism,
dense-crowd, cross-machine, deterministic-replay, or statistical superiority
claim is supported. Runtime doorways/head-on/open-floor matrices, independent
seeds, recordings, real-time factor and per-episode wall timing remain broader
evaluation work. ORCA decision p95 latency is about 21–22 ms and maximum 29.88 ms
in this run, including solver-state/obstacle rebuilding; an otherwise shared
host is not an isolated performance benchmark. Nav2 remains asynchronous.

The STARS source already includes graphs, model/decoder code, training,
checkpoint saving/loading, evaluation, preprocessing and configuration. What is
not present in the inspected checkout is a trained `stars_ma` **forecast**
checkpoint. Its save format embeds encoder/decoder recipes, graph/window
settings, dataset entries and run configuration; an SSL-only encoder checkpoint
cannot drive the forecaster by itself. Data and training outputs are deliberately
Git-ignored. The base STARS reference is pinned but unpopulated, and a separate
Python environment/live Unity adapter still needs preparation. Raw datasets are
needed for training/reproducing offline evaluation, not inherently for live
inference from Unity histories. No trained STARS run or three-controller
milestone is claimed.

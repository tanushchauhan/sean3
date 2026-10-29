# Longer Warehouse navigation result: October 27, 2026

The bounded Kuri Warehouse milestone passes: six generated routes across seeds
7 and 42 completed at startup, after task reset, and after scene reload. All six
passed the predeclared position, freshness, contact, sampling, and stall checks.
No placements were replaced. Both runners exited zero, with four announced
connection closes, zero transport errors, normal player/endpoint exits, and no
forced player kills. Runs finished October 27 in America/Chicago (October 28 UTC).

This is a two-seed static-fixture result, not a general navigation reliability
estimate or a pedestrian-controller comparison. The configured Unity robot is
**Kuri**. Earlier reports inferred Jackal from `nav2_jackal.launch.py`; that was a
ROS profile name, not the live robot identity. Historical results do not qualify
the Jackal model.

## Tested sources and environment

- Unity: `99110a72e87d18a26961d832a2d7b47780cb4799` on `feature/unity-2022-upgrade`.
  Runtime fixes are in `e0335e383b8eb9a748f0534383fd9e618cf5bfa0`;
  the later commit strengthens the Editor-only geometry audit.
- ROS: `d5dd5eecd36c0d4b61a5edbceeba49afdcb2b91c` on `feature/ros2-port`.
  Includes executor/registration synchronization (`fdb04d5`) and the dedicated
  Kuri navigation profile. The original Jackal launch and DWB YAML are unchanged.
- Coordination tooling: the commit containing this report on
  `feature/ros2-environment`. Exact executed snapshots are retained with evidence;
  all six changed tooling files and sixteen component files matched local source.
- Unity 2022.3.62f3, Linux x86_64 on robovision, ROS 2 Humble / Ubuntu 22.04.
- Existing `localhost/sean3-humble:dev` image:
  `1f928d87cafe30ae9feb382a107a1e559d35f19ddc448a2f21fb0b42f59cb8da`.
  No image rebuild or immutable-environment claim.
- Nav2 BT navigator `1.1.20-1jammy.20260915.232207`;
  RPP `1.1.20-1jammy.20260915.232155`.
- Installed stock tree:
  `nav_to_pose_with_consistent_replanning_and_if_path_becomes_invalid.xml`,
  SHA-256 `e3a313e714fb45cbf440fab64b36d0ce42706d20e2486f8c87463ffd823ab7ee`.
  The executed XML expires paths at 10 simulation seconds and checks validity
  at 2 Hz; its comment's 15-second description is inaccurate.

Player: `/scratch/tchauhan/sean3/builds/long-navigation-20261027-candidate9/sean.x86_64`.
The existing cached checkout built successfully from 23:36:51 to 23:37:38 UTC
on October 27, with exit zero. Its recorded HEAD was
`4e9371c7fb3c0344cce130f2ce5c11dea8c78b7b` plus the runtime source subsequently
committed as `e0335e3`. It was **not** built from a fresh clean checkout or at the
later `99110a7` commit. The later geometry test is Editor-only. Source hashes,
tracked diffs, untracked-source inventories, and the saved source snapshots
explain this provenance; remote Git metadata was aligned afterward without
replacing source. Existing Rocketbox metadata and UserSettings were preserved.

All 175 player payload checksums verified after the final runs. Editor SHA-256:
`1ab357c16a84816ec7d4399d174f1e40769964879fa813a5c1139f63349f1f96`.
Package manifest/lock hashes remained:
`ae9c2b53760a9b9e0e17d7721ef6757ada6aff2082878551207e9284a5a36e97` /
`47744304bf01af280ab2f94f29f5a5913d231fa6d68ebac68ea0b99012a412ed`.
The earlier clean-source milestone remains specific to its earlier source pins.

## Behavior changes and acceptance

See [long-navigation protocol](../protocols/long-navigation.md) for the complete protocol and run
command. The player uses Warehouse / None / RandomABNav with Nav2 owning the
actual generated goal. `-completion-distance 0` disables the legacy 1.2 m /
five-second automatic reset; the task timeout remains 3,600 seconds and each
Nav2 goal has a 300-wall-second deadline. No substitute start/goal is used.

The active velocity body now receives a zero-friction resource material.
Previously, floor friction cancelled small velocity commands and caused a
near-stationary robot despite nonzero commands. Regressions reproduce the
default-material deadzone, verify child-collider material ownership, and confirm
that physical walls still block the configured body. This models an ideal
velocity actuator, not wheel traction or a real robot's dynamics.

The object metric now counts physical nonpedestrian side/overhead collision
entries instead of personal-space trigger overlaps. Upward support contacts are
excluded. Continued contact counts once, and a separate reimpact counts again.
Pedestrian metrics retain legacy proximity semantics. New physical-contact
counts are not directly comparable with earlier object proximity counts.

The dedicated Kuri profile uses collision-checked Regulated Pure Pursuit,
0.3 m/s desired speed, a 0.60 m circle with no extra padding, 1.0 m inflation,
and the stock consistent-replanning tree with normal recovery enabled. Its
physical horizontal envelope audit measures 0.2262742 m and includes explicit
wheel radius/suspension bounds. Both costmaps mark and clear finite returns
through the laser's full 3.5 m range. Earlier shorter observation limits omitted
visible obstacles and coincided with alternating path headings/circling; the
accepted combination resolves the observed failures, without isolating every
parameter's causal contribution.

One long-run scene reload exposed destruction of a QoS event while the endpoint
executor constructed its wait set. Registration and executor access now share
a lock, and an active-registration gate prevents idle-spin starvation. The
fix retains visible error diagnostics and has deterministic lock and live
50-cycle registration/removal regressions.

Every route requires a free 0.6 m start/goal map footprint, separation of at least
3 m, a successful initial global plan, action status 4, final position error
at most 0.4 m, displacement at least 0.5 m, fresh streams, zero reported contacts,
and sample gaps at most one simulation second. The stall gates reject 20 seconds
without 0.05 m translation or 15 seconds confined within 0.5 m of an anchor.
Those measures include rotations and intentional waits. Reset checks compare
clock continuity around each reset; this is not an audit of every clock message.

## Final six routes

| Seed | Stage | Actual path m | Wall s | Goal error m | Recoveries | Longest 0.05 m pause s | Longest 0.5 m confinement s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 7 | startup | 42.02 | 145.40 | 0.259 | 0 | 2.0 | 3.6 |
| 7 | task | 12.72 | 45.77 | 0.328 | 0 | 1.6 | 3.2 |
| 7 | scene | 42.51 | 145.54 | 0.317 | 0 | 1.2 | 3.0 |
| 42 | startup | 50.71 | 172.83 | 0.328 | 0 | 2.0 | 3.4 |
| 42 | task | 15.84 | 56.68 | 0.327 | 0 | 1.4 | 3.0 |
| 42 | scene | 30.41 | 106.48 | 0.322 | 0 | 2.0 | 3.4 |

All six action statuses were 4, collision baselines/maxima were zero, neither
stall detector fired, and maximum odometry sample gaps were 0.200013 simulation
seconds. Wall times include action submission and the final 1.2-second metric
settlement. Path length is accumulated sampled odometry, not displacement or
initial planned path length; it can include noise. Raw poses, plans, feedback,
trajectories, reset timings, and counter samples remain in `navigation.json`.
The pause request arrived around the end of these runs; inspection confirmed
both had completed normally before a stop signal was issued. Neither run was
interrupted or relabelled from a partial result.

## Regression checks

| Check on robovision | Outcome |
| --- | --- |
| Unity suite, candidate13 XML | 33 passed, zero failures/skips |
| Python harness suite, final source | 22 passed |
| Endpoint tests, candidate15 | 12 passed, including two executor concurrency checks |
| Final generated-route stages | 6 / 6 passed |
| Announced closes / expected connections | 4 / 4 |
| Forced player termination, transport errors | 0 / 0 |
| Player payload checksums | 175 / 175 matched |
| Final component/tooling source comparison | 22 / 22 matched |

The Unity suite ran 00:44:38-00:44:42 UTC October 28. Its runtime physics source
matches the player; the geometry audit is test-only. The twelve endpoint tests
ran before the final profile adjustment, with unchanged endpoint/test source.
The six-pair resource-growth and rendered sensor suites were not rerun on this
candidate; earlier results remain historical.

## Preserved failed attempts

Every directory is retained under `validation/long-navigation/`; no unsuccessful
run contributes to the six accepted cases above.

| Attempt | Observed outcome / disposition |
| --- | --- |
| `20261027-attempt1` | Original DWB completed 2/3 actions but all failed strict criteria: long pauses, old proximity counts, final timeout and teardown errors. |
| candidates1,3,5,6,8 | Preparatory/fixture/material experiments; no accepted final route sequence. Standalone Jackal fixture assumptions and material enum mistakes were corrected; failed diagnostics remain. |
| candidate2 | Reduced DWB rollout/horizon timed out with 14 recoveries; stopped. Old interruption JSON/log-checker weakness retained in evidence. |
| candidate4 | Rotation shim first route timed out with 14 recoveries; subsequent task completed; run stopped, clean transport. |
| candidate7 | Material applied to the wrong standalone Jackal asset; live Kuri small-command deadzone remained. Stopped; unrelated Jackal asset change reverted. |
| candidate9 | Active Kuri material fixed. Seed7 passed 3/3; seed42 aborted all three after 263-288 seconds and 15 recoveries each. Build retained for later profile trials. |
| candidate10 | RPP with the mismatched Jackal rectangle/old inflation failed all three seed42 routes through collision prediction. Initial path clearance about 0.495 m versus padded rectangle corner radius 0.690 m. |
| candidate11 | Increased inflation: startup/scene passed, task timed out at 301 seconds. |
| candidates12-13 | Audited Kuri circle: startup passed; task timed out with approximately 180-degree path-heading alternation. Scene reset exposed endpoint QoS-handle destruction race. |
| candidate14 | Lock-only endpoint fix starved registration; 15-second stress timeout. Replaced by registration-ready gate. |
| candidate15 | All three seed42 actions completed with stock consistent replanning, but task had 46 seconds of bounded circling and correctly failed strict acceptance. Clean transport. |
| candidate16 | Custom goal/failure-only route retention passed startup/task, then scene aborted with 12 recoveries and bounded-motion stalls. Custom tree removed from final source. |
| candidate17 | Stock tree plus full 3.5 m marking/clearing; both seeds passed all three stages and clean shutdown. Only this directory supplies final live acceptance. |

These experiments changed infrastructure/profile behavior, not pedestrian
controllers. They are diagnostic iterations, not a randomized controller study.

## Evidence and limitations

Authoritative remote root: `/scratch/tchauhan/sean3/`:

- `validation/long-navigation/20261028-candidate17/seed7/` and `seed42/`:
  route JSON, exact configuration, full player/endpoint/Nav2 logs, lifecycle audit,
  endpoint/player exit records, and return codes.
- `20261028-candidate17/ros-source/`, `tooling/`, `runtime-profile.txt`, and
  `payload-verification.txt`: final runtime snapshots/parameter proof and hashes.
- `20261028-candidate13/unity-tests.xml` and
  `20261028-candidate15/endpoint-tests.log`: regression results.
- `builds/long-navigation-20261027-candidate9/`: player, manifest, full build log,
  source diffs/status, submodule state, and payload checksum inventory.

Local ignored copy: `results/long-navigation-20261027/evidence/` retains all
attempt directories. `final-source-hashes.json` and `source-verification.txt`
record the 22-file comparison; `build-provenance/` retains build metadata/logs.
Generated evidence is not committed to the public repository.

Scope is two seeds in static Warehouse / None with the configured Kuri body.
Zero recorded contacts does not prove collision freedom or detect every missed
physics callback. Physical side-contact semantics, conservative circular
geometry, and an ideal velocity actuator do not certify real wheel dynamics,
all visual/camera-boom clearance, or map accuracy. This milestone does not
establish statistical reliability, bit-identical trajectories, cross-machine
repeatability, arbitrary network-fault recovery, GPU resource growth, a new
clean-source import, populated encounters, participant recording/replay, ORCA,
GDC reconstruction, or STEPS alignment.

The next development step is to review the existing Michal/Howard interfaces
before selecting a participant control/recording/replay slice. Preserve this
static navigation baseline for later populated-scenario comparisons.

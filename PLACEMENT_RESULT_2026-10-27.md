# Warehouse placement result — October 27, 2026

The bounded Warehouse random-task placement milestone passes on robovision.
The supported None / RandomABNav / Kuri configuration now chooses starts and
goals compatible with both live geometry and the pinned ROS navigation map.
No fallback placement reset was needed in any of the nine driving episodes.
This is not participant readiness or a broad navigation benchmark.

Robot identity correction, October 28: this report originally inferred Jackal
from the `nav2_jackal.launch.py` ROS profile name. The configured Unity Warehouse
robot is Kuri. The saved commands, source pins and measured outcomes are unchanged;
these results do not qualify the Jackal model.

## What changed and why

The legacy sampler interpolated between unrelated navigation-mesh vertices,
ignored sampling failure, and attempted recursive retries without advancing
its depth counter. RandomABNav also replaced sampled elevations with fixed
world heights. The new task-specific sampler selects a point inside a single
area-weighted triangle, checks boundary and collider clearance, retains surface
elevation, and requires a complete Unity navigation path between endpoints at
least three metres apart. It stops after 256 candidate pairs. Failure leaves
the task unchanged, retries after five seconds, and never publishes an
uninitialized periodic goal. Other task and pedestrian samplers are unchanged.

Geometry checks alone were insufficient: the previously rejected start at ROS
(1.6129, -7.7117) has navigation-mesh clearance and no collider overlap in the
checked column, but the saved ROS map marks its footprint occupied. An initial
geometry-only candidate likewise failed the independent map check. Warehouse
placement therefore also uses a versioned free-cell mask of the supported ROS
map, with a 0.7 m footprint. The runtime ROS check independently uses the actual
map-server grid and a 0.6 m footprint. Map source hashes are stored with the mask:

- YAML: `da746446181e8366238852158926192afacbfe7ad75c854b95371019cf125e13`
- Image: `ebd76fd8cb3aa1547c4c2287a4e7410d245904ece534fd5a926adf53488e5d9e`

The earlier sensor report's first three normal-start image samples were saved
before the first task initialized. Their shelving occlusion does not locate the
subsequent sampled task start inside shelving. Its rejection against the ROS
map was independently recorded. The capture runner now waits for an acknowledged,
settled initial task before saving normal Warehouse images. Measured-target
captures retain their own fixture-readiness gate. No scene geometry or ROS map
was modified to make these checks pass.

## Source and build record

Unity placement commit `69190d6afd384035e07d8c7dde94e721090af281` follows the sensor
revision `23da99e3e1ddd9a99550665535935487ecc935d4`. Final candidate
`fa6386105302338edbda0420d486df80d2f7908c` adds the initial-goal publication guard
and its regression test. ROS remains `2ac78a303d323fbce0caad83555dbe940cc40435`;
Rocketbox remains `8aa27b9765284e01be88b1eed18ece55af5b7c5c` from the approved fork.

The final player build ran 20:36:16–20:36:49 UTC with source HEAD `fa63861` before
and after, exited zero, and reported success. All 175 payload hashes verified.
All thirteen changed/new source and metadata files were verified byte-for-byte
before aligning the remote branch/index; working files were retained. Existing
Rocketbox child-model metadata changes and generated UserSettings remain
uncommitted. The final build is an incremental build from the existing cached
checkout, not a new clean-source import. The earlier clean-source milestone
remains specific to its own source revision.

Unity 2022.3.62f3 editor SHA256:
`1ab357c16a84816ec7d4399d174f1e40769964879fa813a5c1139f63349f1f96`.
Package manifest/lock hashes remain
`ae9c2b53760a9b9e0e17d7721ef6757ada6aff2082878551207e9284a5a36e97` and
`47744304bf01af280ab2f94f29f5a5913d231fa6d68ebac68ea0b99012a412ed`.
The existing `localhost/sean3-humble:dev` image and ROS overlay were reused.
Rendered checks used NVIDIA OpenGL through VirtualGL device egl4 with an
application target of 30 fps; no achieved-throughput claim is made.

## Results

| Check | Result |
| --- | --- |
| Final Unity EditMode suite | 23 passed, zero failed/skipped/inconclusive |
| Python harness regressions | 14 passed |
| Unity known-start/map/empty-mesh/blocked/disconnected/elevation/RNG/initial-goal regressions | Passed |
| Live sampler audits, five seeds per audit | 100 pairs per run, both runs passed independent ROS-map checks |
| Startup + twenty task resets + two scene reloads, seed 7 | All 23 placements and generated-goal global plans passed |
| Same full sequence on final candidate, seed 42 | All 23 placements and generated-goal global plans passed |
| Lowest observed laser minimum across 46 placements | 1.151 m; acceptance limit 0.3 m |
| Settled height and fresh sensors at all 46 placements | Passed; height 0.04 ±0.05 m |
| Startup/task-reset/scene-reload driving, placement build, seeds 7 and 42 | All six short goals passed; zero rejected starts |
| Same three driving stages on final guarded build, seed 7 | All three passed; zero rejected starts |
| Normal rendered startup captures, seeds 7 and 42 | 963 image payloads decoded, zero failures; calibration/timing checks passed |
| Final runner, measured sensor target at heading 0° | Passed geometry and payload checks; 424 further images decoded |
| Rendered complete player logs and shutdown wrappers | No native crash marker; all three wrappers exited zero |

The seed-7 full reset sequence and first six driving episodes used the placement
code before the final periodic-publication guard. The second full sequence,
three final driving stages, and measured-target regression used `fa63861`.
The placement implementation is identical across those two source commits.

All 46 real starts and goals passed the 0.6 m ROS-map check, and every actual
generated task goal received a successful Nav2 global plan with more than one
pose. This checks planning, not execution of those long routes. The nine driven
smoke-test goals were one metre from their starts: displacements were
0.6503–0.6548 m and goal errors 0.3453–0.3498 m. Their acceptance thresholds were
at least 0.5 m displacement and at most 0.4 m final error.

First-, third-person, and overhead samples were visually inspected for both
normal startup seeds. Seed 7 shows the open Warehouse/table area; seed 42 faces
an exterior wall from a clear position. Neither inspected pose is inside a
shelf or has a blocked camera origin. This does not certify useful framing for
every random heading or all third-person camera-boom positions.

## Diagnostics and limits

Transport remains unclean during scene reload and exit. The final rendered
seed-42 endpoint log records three end-of-stream messages, one bad file
descriptor, and one broken pipe. The final headless navigation player records a
reset-by-peer write; its unsupported-shader messages are expected under
`-nographics`. The two full reset sequences also retain 64 and 90 transient
Nav2 sensor-origin/out-of-map warnings while rolling costmaps catch up with
teleports. All subsequently checked paths and sensor-freshness checks passed.
These diagnostics are preserved, not classified as a clean lifecycle result.

This result covers the configured Warehouse robot, saved map, and None behavior.
It does not establish physical map accuracy, arbitrary map overrides, other
scenes/tasks/robots, pedestrian occupied-space handling in populated scenarios,
all camera-boom orientations, long-task driving, collision metrics, resource
stability, standard ROS metric-depth consumption, or participant workflows.
A changed ROS map requires regenerating and validating the placement snapshot.
Random task sequences intentionally differ from the legacy sampler.

Initial geometry probes, the failed geometry-only candidate, the failed
camera-column-only regression, and the missing audit caused by LoadingScene
replacement remain in separate evidence directories. The audit now survives
LoadingScene and restores the application RNG state. These earlier attempts are
not accepted results.

## Evidence and reproduction

See [PLACEMENT.md](PLACEMENT.md) for constraints, snapshot regeneration, commands,
and acceptance criteria. Authoritative evidence on robovision:

- `/scratch/tchauhan/sean3/validation/placement/20261027-probe/` through `20261027-probe4/`
- `/scratch/tchauhan/sean3/validation/placement/20261027-candidate1/`
- `/scratch/tchauhan/sean3/validation/placement/20261027-candidate2/`
- `/scratch/tchauhan/sean3/validation/placement/20261027-candidate3/`
- `/scratch/tchauhan/sean3/builds/placement-20261027-goal-guard/`

The accepted directory contains full logs, camera captures, JSON verdicts,
source verification, build-payload verification, exact executed tooling, and
preserved incremental source bundles. Local copies are under ignored
`results/placement-20261027/`. Existing unrelated local and remote changes were
preserved. Validation players and containers are removed after each run.

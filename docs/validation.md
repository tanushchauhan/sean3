# Migration validation

## Controller integration baseline: October 29

On robovision, the accepted fresh `537ec00` player passes three navigation
stages and a four-case, seed-7 aisle subset (both mirrors, parked and Nav2):
16 person goals and two actual Nav2 actions complete with zero contacts and
clean transport/process shutdown. All 175 player payload hashes verify. The
uncommitted scene-level controller core passes the final 66-test Unity suite
(19 new tests); the existing Python harness passes 54 tests locally and remotely.
The live checks use the existing baseline player. Production contract wiring,
ORCA, STARS and three-controller comparison remain pending. See
[the result](results/2026-10-29-controller-integration.md) for source hashes,
exact commands, diagnostic evidence and limits.

## Launcher and fresh setup: October 29

`./sean3` sets up, checks and runs SEAN 3, with a task driver that sends each
task goal to Nav2 once. A fresh clone on robovision went through `setup` (including
the first from-scratch ROS image build), `build-player`, `doctor` and a 5-minute
`run` with no manual steps: three tasks succeeded and Ctrl+C stopped everything
cleanly. Controls, crash handling and startup errors were also checked. See
[the result](results/2026-10-29-launcher.md).

## Visual experience: October 28

On the long-route stack (Unity `1fec526` c01 player, image
`localhost/sean3-humble:tf2-0.25.24`), the 80-case encounter matrix passes again
(16/16 Nav2 actions, zero contacts) and the rendered sensor fixture passes at
three headings on NVIDIA OpenGL. A visible empty-Warehouse run passes 3 of 3
routes. Visible and headless runs with 65 `Random` pedestrians pass 3 of 9
routes: crowd blockage, Nav2 success beyond the 0.4 m gate, and two contacts.
Receipt lag stayed below 0.17 s and transport was clean throughout. Unity
`da6edb0` adds view switching and contact logging (47 EditMode tests pass) and
ROS `fe9bd37` tightens the Kuri planner tolerance; campaign q03 passes 36 of 36
routes on both. See [the result](results/2026-10-28-visual-experience.md).

## Long-route reliability: October 28

Unity `1fec526`, ROS `cceff5b`, tooling `e6320a2` and image
`localhost/sean3-humble:tf2-0.25.24` pass 12 of 12 long-route sequences (36
routes, seeds 7 and 42 three times each plus 1001, 2002, 3003, 4004, 5005 and
6006). All routes had zero recoveries and contacts, goal error at most 0.342 m
and receipt-lag growth at most 0.059 s. Unity EditMode (46), harness (54),
endpoint (12), Nav2 lifecycle and five laser-clearing controls pass on this
image. The player is a cached, not clean-source, build. Earlier failures and
diagnostic runs are retained. See
[the result](results/2026-10-28-long-navigation-reliability.md).

## Multi-person Warehouse candidate: October 28

At Unity `3033ba1fb63a01698d543c16f6b21a0e210db85e`, ROS
`cceff5bd54ce52787fa47595fdff8b9c9775527f` and executed encounter tooling
`1e6cad48298aa6dfbecae7659ccd389e118e90b9`, the new clean-source player passes
80 controlled four-person cases: 40 development, 20 on a fresh seed, and 20
at a larger step. All 320 person routes and sixteen actual Nav2 actions complete
within 45 simulation seconds with zero recorded physical contacts and no sampled
body overlaps. All 45 Unity tests, 53 harness regressions, five installed costmap
controls, three ordinary navigation stages and 175 payload checksums pass.

**The full follow-up pipeline failed sustained normal navigation.** The older
accepted executable also failed an identical historical route with its old
profile. No deadline or stall gate was relaxed. The controlled population result
is valid separately; it does not establish broad reliability. Yielding clearance
headroom is layout-dependent and fails the declared threshold in the aisle;
no contact-rate advantage is demonstrated. See
[warehouse-encounter result (2026-10-28)](results/2026-10-28-warehouse-encounters.md)
for all outcomes, rejected attempts, source/build provenance and remaining work;
[warehouse-encounter protocol](protocols/warehouse-encounters.md) gives the protocol. Historical
results below retain their own versions and must not be read as later coverage.

## Pedestrian response to Kuri milestone: October 28

The bounded open-floor diagnostic passes at Unity `aeaa7d247bc99fab12eacc95b22b3ad230d8f207`
and ROS `d5dd5eecd36c0d4b61a5edbceeba49afdcb2b91c` (unchanged). The final player passes 60 fixed-model checks:
36 development, twelve on a fresh seed, and twelve at a larger time step. Fifty
contain a robot and ten are no-robot controls. All complete within the unchanged
18-simulation-second deadline with no physical callbacks or negative sampled
body clearance. The matched Legacy comparison and normal three-stage Warehouse
navigation are recorded separately. All 42 Unity tests, 26 harness tests and
175 final player payload checksums pass; every accepted run passes clean shutdown.

See [pedestrian-avoidance result (2026-10-28)](results/2026-10-28-pedestrian-avoidance.md)
for exact counts, contact-material ablation, source/build provenance, the failed first independent seed,
rejected candidates and limitations; [pedestrian-avoidance protocol](protocols/pedestrian-avoidance.md)
gives the protocol. This is a single-person open-floor response check using
production Kuri, animated SFAgent and physics. It does not qualify populated
Warehouse navigation or human realism. The player was built incrementally in
the cached checkout. Earlier milestones below retain their own source pins;
the earlier six-route, rendered and resource-growth suites were not rerun here.

## Longer Warehouse navigation milestone

The bounded October 27 Kuri result passes at Unity `99110a72e87d18a26961d832a2d7b47780cb4799`
and ROS `d5dd5eecd36c0d4b61a5edbceeba49afdcb2b91c`. All six generated routes (seeds 7 and 42;
startup, task reset, scene reload) completed with zero recorded contacts,
zero recovery actions, and no translation or bounded-motion stalls. Both runs
passed clean shutdown. The final source passes 33 Unity, 22 harness, and 12
endpoint tests; all 175 player payload checksums verified.

See [long-navigation result (2026-10-27)](results/2026-10-27-long-navigation.md)
for exact metrics, source/build provenance, failed attempts, and limitations;
[long-navigation protocol](protocols/long-navigation.md) gives the protocol. The actual robot is
Kuri; previous Jackal labels came from the ROS profile name. This candidate uses
an ideal velocity body, physical object-contact counting, a dedicated RPP
profile, full finite laser observations, and endpoint executor synchronization.
It was built incrementally in the cached checkout, not through a new clean-source
import. Earlier reports below retain their original source pins and outcomes.
Participant workflows, populated scenarios, and general reliability remain open.

## Connection reload and shutdown milestone

The bounded October 27 transport result passes at Unity
`4e9371c7fb3c0344cce130f2ce5c11dea8c78b7b` and ROS
`bf0ea37a4f1eac53ae8a995d7a7d5276ecdc7712`, with Rocketbox unchanged.
All 28 Unity tests, 16 Python harness tests, and 10 endpoint tests pass. Across
headless lifecycle, driving, and rendered runs, twelve connections have twelve
announced closes and disconnects, zero transport errors, normal process exits,
and no forced player kills. Six task resets and six scene reloads also pass the
recorded graph, clock, drift, and resource-growth limits. Twenty further task
resets and two scene reloads pass in the rendered placement sequence.

See [transport result (2026-10-27)](results/2026-10-27-transport.md) and
[transport-lifecycle protocol](protocols/transport-lifecycle.md) for evidence and reproduction.
This resolves the earlier expected reload/exit transport diagnostics for the
new paired pins. Historical reports below retain their original outcomes.
General network-fault recovery, overload, full RPC interoperability, GPU resource
growth, broader scenarios, long-task driving, and participant workflows remain
outside the bounded result.

## Warehouse placement milestone

The bounded October 27 placement result passes at Unity
`fa6386105302338edbda0420d486df80d2f7908c`, with ROS and Rocketbox unchanged.
All 23 Unity tests and 14 Python harness tests pass. Across two full rendered
sequences, 46 real starts and goals pass independent ROS-map, height, freshness,
and global-planning checks. Nine short driving episodes pass with zero fallback
placement resets. Normal startup image capture now waits for task initialization.

See [placement result (2026-10-27)](results/2026-10-27-placement.md) for source,
results, preserved failures, and limits; [placement protocol](protocols/placement.md) documents
reproduction and the pinned ROS-map constraint. Transport reload/exit errors,
map/collider accuracy, arbitrary camera-boom clearance, long-task driving,
populated scenarios, and participant workflows remain open.

## Rendered camera and sensor milestone

The bounded October 27 sensor baseline passes for Unity
`23da99e3e1ddd9a99550665535935487ecc935d4`, with ROS and Rocketbox unchanged.
Six measured-target runs (0°, 90°, 180° on Mesa and NVIDIA OpenGL), two normal
Warehouse captures, and a post-reset GPU view pass. All 2,820 received image
payloads decoded; optical frames, calibration/timestamp pairing, depth, and five
laser bearings met the recorded limits. All 16 Unity tests, 14 Python harness
tests, 175 payload hashes, and three navigation stages pass.

See [rendered-sensor result (2026-10-27)](results/2026-10-27-rendered-sensors.md)
for evidence and limits and [rendered-sensor protocol](protocols/rendered-sensors.md) for commands.
This candidate was built from verified source diffs in the existing cached
checkout; the clean-source result below remains specific to its earlier commit.
The placement follow-up above corrects pre-task image sampling and constrains
random starts/goals. Transport teardown errors, camera throughput,
standard ROS 2 metric-depth consumption, and participant workflows remain open.

## Clean-source Unity build milestone

**Accepted on October 27 for the configured Warehouse fixture in the recorded
existing environment.** Unity commit
`7ae54bab2297bc263e0bb22fbd9dac8035f376df` pins the guarded Rocketbox importer at
`8aa27b9765284e01be88b1eed18ece55af5b7c5c`. ROS remains at
`2ac78a303d323fbce0caad83555dbe940cc40435`. The runner is from coordination
commit `2559138`, executed from `14a56c2` with unchanged script hashes.

On robovision, the clean checkout checks, build provenance regressions, 14 Python
harness tests, Linux player build, all 12 Unity EditMode tests (the previous 11
plus an importer regression), and startup/task-reset/scene-reload navigation
checks passed. All 175 recorded player payload hashes verified. The complete
log has zero Rocketbox callback exceptions after the guarded importer fix;
the first resumed run had 544, including callbacks on required models.

See [clean-build result (2026-10-27)](results/2026-10-27-clean-build.md) for the
source/environment record, diagnostic classification, generated metadata review,
functional results, and resume procedure. Authoritative accepted evidence:

- `/scratch/tchauhan/sean3/validation/clean-source/20261027T184537Z/`
- `/scratch/tchauhan/sean3/builds/clean-source-20261027T184537Z/`

Both earlier attempts remain separate: the interrupted `20261027T002705Z`
output is unaccepted, and `20261027T182807Z` built and passed functional checks
but failed import acceptance. All three used separate fresh checkout/output
paths, with no pre-existing Library or UserSettings before import.

Remaining diagnostics include broken unused legacy prefabs, missing legacy
resource scripts, rig/animation warnings, and editor/shader warnings. Static
LoadingScene/Warehouse traversal found no missing script references; runtime
checks cover `None` pedestrian behavior, `RandomABNav`, and headless sensors.
Import changed four Rocketbox child-model metadata files without changing GUIDs;
those diffs and generated Search settings are preserved, not committed silently.
Transport teardown remains unclean: the accepted run recorded one reset-by-peer
write and two endpoint EOF errors.

This is not an all-asset or all-scenario validation. It reuses the existing host,
editor, package cache, and ROS image, and does not establish an immutable
environment, bit-identical builds, rendered camera correctness, participant
workflows, or broad navigation performance. The historical lifecycle results
below are separate; their six-pair stress check was not rerun for this candidate.

## Lifecycle follow-up on October 26, 2026

The candidate pins now include connector destruction cleanup and the ROS
endpoint compatibility wrapper. The original navigation results below remain
historical evidence; they did not check repeated registration or resource growth.

| Check | Result |
| --- | --- |
| Unity EditMode suite | 11 passed |
| Harness regression suite | 14 passed |
| Endpoint compatibility tests against installed ROS libraries | 3 passed |
| Final Nav2 startup / task reset / scene reload | 3 goals passed |
| Repeated task resets / scene reloads | 6 / 6 passed |
| Post-reset translation drift | 0 m measured in each two-second window |
| Clock regressions | 0 observed |
| ROS graph | Stable single sensor publishers and control subscribers |
| Player RSS growth after first pair | 1,120 KiB maximum |
| Endpoint RSS growth after first pair | 396 KiB maximum |
| Player / endpoint thread and descriptor growth | 0 / 0 after warm-up |
| Transport teardown | Not clean; details below |

The final navigation run measured displacements of 0.654, 0.651, and 0.654 m,
with goal errors of 0.346, 0.349, and 0.346 m. One startup placement was rejected.
These remain clear-path smoke tests, not benchmark results.

The original `integration-final` player failed the new check after its first
scene reload: sensor publishers and control subscribers doubled. Its failed
run remains in `validation/lifecycle/baseline-host-sampling/` on robovision.
The first baseline attempt in `baseline/` failed because container isolation
prevented inspecting the host player. Resource sampling now runs on the host.

Fixes tested:

- The embedded connector cancels its connection worker and unregisters its HUD
  header when destroyed. Repeated `Connect` calls do not replace a live worker.
- The ROS wrapper implements the connector's removal commands. The pinned
  upstream endpoint previously crashed its client thread on `remove_subscriber`.
- Registration changes are serialized, and unchanged topic registrations are
  reused across reconnects. Topic nodes retain their individual names. The
  bridge uses wall time while Unity still supplies sensor timestamps.

The final lifecycle log audit found no duplicate HUD headers, duplicate logger
warnings, queue overflows, missing references, unregistered topics, reader
exceptions, or endpoint tracebacks. It observed exactly seven connections:
startup plus six scene reloads. **Transport teardown is still not clean:** one
Unity reset-by-peer write, three endpoint writes to already-closed sockets, and
seven endpoint EOF messages remain. `lifecycle-logs.json` reports
`transport_clean: false`. These exact diagnostics are counted separately from
unexpected failures. Reset-by-peer writes are bounded by the number of reloads;
extra connections fail the audit. This is a recovery check, not proof of graceful
socket teardown or a leak-free long-running session.

Run the bounded check with the existing runner:

```sh
SEAN_ROS_IMAGE=localhost/sean3-humble:dev SEAN_CHECK_MODE=lifecycle \
SEAN_LIFECYCLE_PAIRS=6 bash scripts/check_unity_navigation.sh \
  /path/to/sean.x86_64 "$PWD/ros_ws" "$PWD/sources/social_sim_ros" \
  "$PWD/results/lifecycle"
```

`SEAN_LIFECYCLE_PAIRS` accepts 2 through 20 pairs. Each stage checks new sensor
messages after the reset acknowledgement, timestamp freshness, every received
clock sample for regressions, a single task transition, stationary odometry,
and unchanged graph counts. It issues an angular command before resetting.
The stationary live check also permits the existing command timeout to stop the
robot; an EditMode test separately checks immediate clearing of velocity targets
and rigidbody velocities. Neither check establishes participant-input behavior.

Resources are sampled after a two-second observation window. The first reset /
reload pair is the warm-up baseline; subsequent stages enforce budgets of
128 MiB RSS, four threads, and eight descriptors for each process. These budgets
catch large regressions, not all leaks, and do not measure transient peak memory.
Player sampling requires Linux `/proc` access for the same host user. The
container sees only the resulting samples; DDS stays isolated inside it.

Run endpoint regression tests inside the existing ROS image:

```sh
docker run --rm --network none \
  -v "$PWD/tests:/tests:ro" \
  -v "$PWD/sources/social_sim_ros/social_sim_ros/scripts:/scripts:ro" \
  localhost/sean3-humble:dev \
  python3 /tests/endpoint_compat_check.py /scripts/sean_tcp_endpoint
```

Remote evidence under `/scratch/tchauhan/sean3/`:

- Player: `builds/lifecycle-final/sean.x86_64`.
- Repeated lifecycle data and logs: `validation/lifecycle/final-run/`.
- Unity XML and harness output: `validation/lifecycle/final-tests/`.
- Final navigation smoke test: `validation/lifecycle/final-navigation/`.
- Exact component source commits: `validation/lifecycle/sean-*-lifecycle.bundle`.

The source bundles preserve the embedded connector, which was untracked when
building and therefore absent from the original build's tracked-file patch.
`builds/lifecycle-final/commit-provenance.txt` records the subsequent source
verification against the commits. Existing Rocketbox metadata and UserSettings
were preserved. This work does **not** establish a clean-source asset import,
immutable container rebuild, rendered camera correctness, or participant
recording. Those are the next milestones; ORCA remains deferred.

## Initial results on October 26, 2026

Checks ran on a Linux x86_64 host using the existing SEAN workspace and editor.
The previous agent's source changes were saved before updating the checkouts.

| Check | Result |
| --- | --- |
| Startup-check regression suite | 6 passed |
| Unity EditMode suite | 9 passed |
| ROS interface package build | Passed |
| Nav2 lifecycle activation | All 8 nodes active |
| Navigation and recovery command graph | Both feed the velocity smoother |
| Velocity output | Test command reached `/mobile_base_controller/cmd_vel` |
| Command timeout | Smoother output returned to zero |
| Live Unity navigation | 3 goals passed: startup, task reset, scene reload |
| Participant control and recording | Not tested |

The lifecycle-only Nav2 check supplies synthetic clock and TF inputs. It does
not validate
Unity's sensors, robot motion, collision handling, or map alignment. The Unity
suite tests connection replacement, camera copying, body-frame velocity,
rotation wraparound, and sensor mounts at several robot headings. Full scene
reload and navigation are covered separately by the live runner below.

The Nav2 run exposed an inflation radius smaller than the padded robot
footprint. Both costmaps now use 0.50 m, above the 0.465 m inscribed radius.
The stopped-speed threshold is now 0.01 m/s, below the original maximum
forward speed of 0.05 m/s. A live motion probe showed that the original
0.05 m/s command produced only 0.0012 m of displacement in three seconds,
while 0.3 m/s produced 0.70 m. The forward limit is now 0.3 m/s in both DWB
and the velocity smoother. This is a smoke-test configuration, not a physical
robot calibration or a navigation-performance claim.

## Versions

Component commits are pinned by the `sources/` submodules.

- Unity: 2022.3.62f3.
- ROS-TCP-Connector: v0.7.0.
- ROS: Humble on Ubuntu 22.04.
- Nav2 bringup package: `1.1.20-1jammy.20260916.005516`.
- Installed ROS-TCP-Endpoint commit: `54c1a64b6d5ef6ffa0a0431570bb74329b79b15b`.
- Test image ID: `1f928d87cafe30ae9feb382a107a1e559d35f19ddc448a2f21fb0b42f59cb8da`.

The existing test image was reused, not rebuilt during these checks. The
Dockerfile now pins the endpoint commit above, but its base image and apt
packages can still change. Rebuild and record the resulting image before
publishing experimental results. The remote Unity checkout also contains
editor-generated asset metadata changes, including Rocketbox import metadata;
these tests do not establish that all assets import identically from a clean clone.

## ROS checks

From this repository, with the `sources/` submodules checked out:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
docker build -t sean3-humble:dev -f docker/Dockerfile.humble docker
mkdir -p ros_ws/src/social_sim_ros results

docker run --rm --network none \
  -e ROS_DOMAIN_ID=73 -e SEAN_TEST_LOG_DIR=/results \
  -v "$PWD/ros_ws:/sean3_ws_overlay" \
  -v "$PWD/sources/social_sim_ros:/sean3_ws_overlay/src/social_sim_ros:ro" \
  -v "$PWD/tests:/tests:ro" \
  -v "$PWD/results:/results" \
  sean3-humble:dev \
  bash /tests/nav2_lifecycle_check.sh /sean3_ws_overlay --check-commands
```

`SEAN_STARTUP_TIMEOUT` sets the readiness deadline in seconds, defaulting to 60.
`SEAN_SCENE` selects the ROS map, defaulting to `lab`. Logs are kept in a unique
subdirectory of `SEAN_TEST_LOG_DIR`, or the system temporary directory when unset.
Run synthetic command checks only in an isolated test environment.

## Unity checks

Use the pinned editor with a valid Unity license. Open the project and run
`SEAN.Editor.Tests` in Window > General > Test Runner > EditMode, or on Linux:

```sh
mkdir -p results
GIT_CONFIG_GLOBAL=/dev/null DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 \
  xvfb-run -a /path/to/2022.3.62f3/Editor/Unity \
  -batchmode -nographics -projectPath "$PWD/sources/social_sim_unity" \
  -runTests -testPlatform EditMode -assemblyNames SEAN.Editor.Tests \
  -testResults "$PWD/results/unity-tests.xml" \
  -logFile "$PWD/results/unity-tests.log"
```

Check the XML result as well as the process exit code. A successful editor
launch alone does not establish that tests ran.

## Live navigation and resets

On Linux, build a fresh player and run the isolated integration check:

```sh
bash scripts/build_unity_player.sh /path/to/2022.3.62f3/Editor/Unity \
  "$PWD/sources/social_sim_unity" "$PWD/build/navigation-check"
mkdir -p ros_ws/src/social_sim_ros
bash scripts/check_unity_navigation.sh \
  "$PWD/build/navigation-check/sean.x86_64" "$PWD/ros_ws" \
  "$PWD/sources/social_sim_ros" "$PWD/results/navigation-check"
```

The results directory must be new. Set `SEAN_ROS_IMAGE` to select an existing
image, `SEAN_TCP_PORT` to change the host localhost port, and `SEAN_SEED` to
change the default seed of 7. DDS remains inside the container. Do not add
`ROS_LOCALHOST_ONLY=1` to the loopback CycloneDDS configuration; that combination
caused duplicate-interface initialization errors in this environment.

The player runs Warehouse with `None` pedestrian behavior and `RandomABNav`.
Task-generated goals are disabled so the test action client owns navigation.
The runner checks a one-metre goal at startup, after task reset, and after scene
reload. It requires Nav2 success, at least 0.5 m of measured motion, final goal
error below 0.4 m, correct odometry frames, fresh clock/scan/odometry data, and
clock continuity across resets. Nav2's configured goal tolerance remains 0.35 m.

Random starts without a clear one-metre path and 0.6 m map clearance are rejected
before sending a goal. Up to ten placements are attempted; rejected positions
are recorded rather than counted as navigation failures. This selects a simple
smoke-test fixture and must not be used as an unbiased navigation benchmark.
The seed and actual poses are recorded; bit-for-bit trajectory determinism has
not been established.

The final seed-7 run produced:

| Stage | Robot displacement | Goal error | Result |
| --- | --- | --- | --- |
| Startup | 0.654 m | 0.346 m | Passed |
| Task reset | 0.656 m | 0.344 m | Passed |
| Scene reload | 0.655 m | 0.345 m | Passed |

One initial placement was rejected. Task reset advanced the clock by 1.20 s
and scene reload by 3.55 s; neither reset restarted its epoch. An earlier
three-episode run also passed. These checks establish basic integration, not
collision fidelity, pedestrian realism, study usability, or real-time guarantees.

`navigation.json` contains outcomes, poses, placement rejections, reset timing,
and sensor counts. The runner saves player, endpoint, and Nav2 logs and removes
only its own container and player process group. The build includes a source
patch, dirty-state listing, submodule revisions, and manifest. The Linux launcher
provides a temporary `libdl.so` alias for the bundled AssimpNet importer; it does
not modify system libraries. Headless shader warnings are expected with
`-nographics`; camera images are not validated by this test.

The logs contain transport disconnect exceptions around connection replacement
and shutdown, duplicate ROS logger registrations, and a duplicate HUD header
after reload. Sensor freshness and the subsequent navigation goal passed, but
repeated reloads and connection cleanup still need a longer stress test. No
connector queue overflow or Nav2 error-level messages appeared in the final run.

## Remaining work

Validate participant control and recording, camera rendering, sensor geometry
against known obstacles, collision metrics, and repeatability across machines.
Then add ORCA behind the shared pedestrian interface. GDC reconstruction and
aligned STEPS visualization remain deferred.

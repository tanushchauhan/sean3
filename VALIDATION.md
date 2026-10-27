# Migration validation

## Rendered camera and sensor milestone

The bounded October 27 sensor baseline passes for Unity
`23da99e3e1ddd9a99550665535935487ecc935d4`, with ROS and Rocketbox unchanged.
Six measured-target runs (0°, 90°, 180° on Mesa and NVIDIA OpenGL), two normal
Warehouse captures, and a post-reset GPU view pass. All 2,820 received image
payloads decoded; optical frames, calibration/timestamp pairing, depth, and five
laser bearings met the recorded limits. All 16 Unity tests, 14 Python harness
tests, 175 payload hashes, and three navigation stages pass.

See [RENDERED_SENSOR_RESULT_2026-10-27.md](RENDERED_SENSOR_RESULT_2026-10-27.md)
for evidence and limits and [RENDERED_SENSORS.md](RENDERED_SENSORS.md) for commands.
This candidate was built from verified source diffs in the existing cached
checkout; the clean-source result below remains specific to its earlier commit.
Startup shelving occlusion, transport teardown errors, camera throughput,
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

See [CLEAN_BUILD_RESULT_2026-10-27.md](CLEAN_BUILD_RESULT_2026-10-27.md) for the
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

Component commits are pinned in `sean3-candidate.repos`.

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

From this repository, with components imported into `sources/`:

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

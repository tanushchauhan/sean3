# Migration validation

## Results on October 26, 2026

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

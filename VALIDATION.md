# Migration validation

## Results on October 26, 2026

Checks ran on a Linux x86_64 host using the existing SEAN workspace and editor.
The previous agent's source changes were saved before updating the checkouts.

| Check | Result |
| --- | --- |
| Startup-check regression suite | 6 passed |
| Unity EditMode suite | 8 passed |
| ROS interface package build | Passed |
| Nav2 lifecycle activation | All 8 nodes active |
| Navigation and recovery command graph | Both feed the velocity smoother |
| Velocity output | Test command reached `/mobile_base_controller/cmd_vel` |
| Command timeout | Smoother output returned to zero |
| Unity-to-ROS navigation goal | Not tested |
| Participant control, recording, repeated episodes | Not tested |

The Nav2 check supplies synthetic clock and TF inputs. It does not validate
Unity's sensors, robot motion, collision handling, or map alignment. The Unity
suite tests connection replacement, camera copying, body-frame velocity,
rotation wraparound, and sensor mounts at several robot headings. It does not
perform a full scene reload or navigation episode.

The Nav2 run exposed an inflation radius smaller than the padded robot
footprint. Both costmaps now use 0.50 m, above the 0.465 m inscribed radius.
The stopped-speed threshold is now 0.01 m/s, below the configured 0.05 m/s
maximum forward speed. Navigation behavior still needs evaluation before
changing these inherited low-speed limits.

## Versions

Component commits are pinned in `sean3-candidate.repos`.

- Unity: 2022.3.62f3.
- ROS-TCP-Connector: v0.7.0.
- ROS: Humble on Ubuntu 22.04.
- Nav2 bringup package: `1.1.20-1jammy.20260916.005516`.
- Installed ROS-TCP-Endpoint commit: `54c1a64b6d5ef6ffa0a0431570bb74329b79b15b`.
- Test image ID: `1f928d87cafe30ae9feb382a107a1e559d35f19ddc448a2f21fb0b42f59cb8da`.

The existing test image was reused, not rebuilt during these checks. The
Dockerfile still follows the endpoint's `main-ros2` branch and current apt
packages, so a new image may differ. Pin and rebuild the environment before
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

## Next integration check

Select one Unity scene and matching ROS map, build a fresh player, and verify
clock, TF, odometry, and laser data through the TCP endpoint. Send a navigation
goal and record actual movement and completion. Repeat after task reset and
scene reload. The ROS default `lab` map must not be paired with the current
player's Warehouse scene. Preserve failure logs and record all build inputs.

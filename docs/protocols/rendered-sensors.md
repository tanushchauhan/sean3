# Rendered camera and sensor validation

Run this on robovision. The runner uses the existing ROS overlay and a Linux
player built from the sensor candidate. It launches a private ROS endpoint,
exposes only its TCP port on localhost, and stops only its own processes.
Use a new results directory for every run. The runner stops the GPU player
before its display server and rejects native-crash markers in the full player
log after cleanup. Endpoint transport diagnostics remain a separate review.

```sh
root=/scratch/tchauhan/sean3
cd "$root/sean3"
SEAN_VGL_DEVICE=egl4 SEAN_TCP_PORT=10325 SEAN_SENSOR_HEADING=0 \
  SEAN_CAPTURE_SECONDS=25 bash scripts/check_rendered_sensors.sh \
  "$root/builds/rendered-sensors-20261027-fix6/sean.x86_64" \
  "$root/ros_ws" "$root/social_sim_ros" /path/to/new-results

docker run --rm --network none \
  -v "$root/sean3/tests:/tests:ro" -v /path/to/new-results:/results \
  localhost/sean3-humble:dev \
  python3 /tests/analyze_rendered_sensors.py /results/capture
```

Repeat with `SEAN_SENSOR_HEADING=90` and `180`, using separate directories.
Omit `SEAN_SENSOR_HEADING` to capture the normal Warehouse scene. Omit
`SEAN_VGL_DEVICE` for Mesa software rendering under Xvfb; that path is much
slower. Device selection must match the available VirtualGL EGL devices on the
host. `glxinfo.txt` records the actual renderer. The application defaults to a
30 fps cap, configurable with `SEAN_FRAME_RATE`; camera publishers request 15 fps.
Neither setting guarantees an achieved rate.

The camera coroutines wait for rendered frames. The runner deliberately omits
`-batchmode` and `-nographics`, which the headless navigation check uses.
`SEAN_TCP_PORT` defaults to 10322; assign separate ports for concurrent players.
Set `SEAN_CAPTURE_RESET=1` without a measured heading to request one acknowledged
task reset before capturing another normal Warehouse view. This records the
placement change in `reset.json`; it does not certify arbitrary starts as clear.
`SEAN_PLAYER_ARGS` passes extra player arguments, for example `-view top`.
`SEAN_VIEW_CYCLE=1` (with `SEAN_XDOTOOL_ROOT` pointing at an extracted xdotool)
presses the view key every `SEAN_VIEW_INTERVAL` seconds after the task starts,
`SEAN_VIEW_PRESSES` times, and saves a screenshot of each view under `views/`.

## On-screen views

Press C in the player to cycle the window through `Auto` (the task's own layout:
first-person view with overhead and third-person insets), `FirstPerson`,
`ThirdPerson`, `Overhead` and `Top` (the whole environment). `-view NAME` selects
the starting view. The switcher only changes which camera is drawn on screen;
ROS camera topics come from separate offscreen copies and are unaffected. It is
disabled when a participant controls the player.

## Measured fixture

The optional player arguments `-sensor-validation-output FILE` and
`-sensor-validation-heading DEGREES` activate a test fixture. It waits for the
Warehouse robot, disables task progression and velocity controllers, freezes
the robot at a known pose outside the Warehouse geometry, and places a wall
two metres ahead of the first-person camera. Four unlit colored panels at
known offsets establish image orientation and projection. The same wall is
visible to the depth camera and the raycast laser. No fixture is installed
without the output argument.

The fixture writes camera poses, clipping ranges, robot pose, laser pose, and
wall plane to `fixture.json`. The capture tool waits for this file before
sampling. This tests the actual robot publishers and mounts; it does not
measure Warehouse map or collider accuracy against a physical building.

Acceptance checks require:

- Three saved, decodable 640×480 images per stream; every subsequent received
  payload is also decoded during the bounded capture.
- Image/calibration dimensions and frame names agree, with at least two
  matching timestamp pairs, advancing timestamps, no regressions, and last
  image stamps within three simulation seconds of the latest clock.
- All four camera frames match their optical axes and mount positions within
  0.002 vector norm / 0.002 metres at each heading.
- Red/green/blue/yellow marker centroids match the published first-person
  camera projection within three pixels, including top/bottom and left/right.
- The central depth patch agrees with the measured wall plane within 0.03 m.
- Laser bearings 0°, ±15°, and ±30° agree within 0.01 m; the published laser
  mount and forward axis agree within 0.002 m / vector norm.

`capture.json` retains counts, timestamps, sample metadata, initial sensor
messages, and the latest transform for every observed child frame. Original
image payloads and decoded PNGs are retained. `analysis.json` records every
check and measurement. The capture command alone is exploratory and does not
assert acceptance; the analyzer returns a nonzero exit status on failure.

## Message conventions and limits

RGB messages contain PNG-encoded RGBA images. Camera intrinsics come from the
camera rendering the output texture, including its output aspect ratio.
The orthographic overhead view reports zero K/P and an empty distortion model
to mark its pinhole calibration unsupported.

The retained first-person frame name `firstperson_rgb_link` now describes
optical axes (x right, y down, z forward). The third-person image header uses
`thirdperson_rgb_link`, matching its existing transform. Depth uses
`center_depth_optical_frame`; the overhead view uses `overhead_rgb_link`.
`base_link -> laser` comes from the scanner's actual Unity mount, without
requiring Nav2 or a robot-description publisher.

Depth remains the legacy RGBA-packed normalized eye depth in a PNG, with the
camera far plane at 20 m. It is not a standard `32FC1` image or
`compressedDepth` payload. The analyzer decodes the retained shader's channel
weights `[1, 1/255, 1/65025, 1/160581375]` and multiplies by the far plane.
The old ROS 1 `depth_synchronizer.py` is not a validated ROS 2 consumer.

These checks do not establish camera throughput, physical photometric
accuracy, the synchronous readback fallback, all image sizes/scenes, all
depths/angles, moving-camera timing, camera survival through repeated resets,
or participant recording quality. Navigation and transport lifecycle evidence
remain separate. See [the October 27 sensor result](../results/2026-10-27-rendered-sensors.md)
for the tested revisions and bounded results.

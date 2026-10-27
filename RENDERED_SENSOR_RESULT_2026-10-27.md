# Rendered sensor result — October 27, 2026

The bounded rendered-camera and sensor-geometry baseline passes on robovision.
This covers the configured Warehouse robot and a controlled measured target,
using Mesa software rendering and NVIDIA OpenGL. It does not qualify the
simulator for participant use or validate every scene, placement, or sensor mode.

## Changes and source record

Unity commit `23da99e3e1ddd9a99550665535935487ecc935d4` follows the accepted
clean-source revision `7ae54bab2297bc263e0bb22fbd9dac8035f376df`. ROS remains
`2ac78a303d323fbce0caad83555dbe940cc40435`; Rocketbox remains
`8aa27b9765284e01be88b1eed18ece55af5b7c5c` from the approved personal fork.

The initial accepted-build camera capture observed 35 messages per RGB stream.
All nine saved RGB payloads failed PNG decoding: the asynchronous path read an
unpopulated CPU texture and sent raw bytes while claiming PNG. The fix reads the
render texture as RGBA and encodes the pixels as PNG. Readback failures skip a
frame. Rendering restores the shared active texture before yielding.

Other corrections:

- CameraInfo uses the output camera's projection and actual dimensions. The
  orthographic overhead view explicitly reports unsupported pinhole calibration
  with zero K/P, rather than misleading intrinsics.
- Packed depth uses linear RGBA storage, disables MSAA, uses the configured
  width/height consistently, and requests explicit RGBA readback.
- First-person image transforms use optical axes. Rotation adjustments compose
  as local quaternion rotations. The third-person image header now names the
  existing `thirdperson_rgb_link` transform.
- The scanner publishes `base_link -> laser` from its actual mount. Previously
  scan messages named this frame without publishing it. Existing navigation
  success alone had not established that scan geometry was usable.
- An opt-in measured fixture and repeatable ROS capture/analyzer tools preserve
  images, headers, calibration, transforms, distances, and individual verdicts.

The final player was built from the existing working checkout with these source
changes, before committing them. Its manifest therefore records base commit
`7ae54ba` plus captured diffs, not `23da99e` as its build-time HEAD. All 12
candidate files, including new fixture/shader assets and metadata, were verified
byte-for-byte against `source.sha256` and the committed candidate. The remote
branch/index were subsequently aligned with the commit without replacing
working files. Existing Rocketbox metadata changes and generated UserSettings
remain uncommitted. This was a cached incremental build, not another clean-source
import; the earlier clean-source result remains evidence for `7ae54ba` only.

Unity 2022.3.62f3 editor SHA256:
`1ab357c16a84816ec7d4399d174f1e40769964879fa813a5c1139f63349f1f96`.
The final build ran 19:31:43–19:32:30 UTC, exited zero, and reported success.
All 175 payload hashes verified. Package manifest/lock hashes remained
`ae9c2b53760a9b9e0e17d7721ef6757ada6aff2082878551207e9284a5a36e97` and
`47744304bf01af280ab2f94f29f5a5913d231fa6d68ebac68ea0b99012a412ed`.
The existing `localhost/sean3-humble:dev` image and overlay were reused.

## Results

| Check | Result |
| --- | --- |
| Unity EditMode suite | 16 passed, zero failed/skipped/inconclusive |
| Python harness regression suite | 14 passed |
| Measured headings 0°, 90°, 180°, Mesa llvmpipe OpenGL 4.5 | All passed |
| Same headings, NVIDIA Quadro RTX 6000 OpenGL 4.6 / driver 580.178.04 | All passed |
| Normal Warehouse capture on both renderers | Both passed payload/timing checks |
| NVIDIA Warehouse capture after an acknowledged task reset | Passed; clear first-, third-person, and overhead views inspected |
| Image payloads decoded across the nine final captures | 2,820; zero decode failures |
| Largest first-person marker projection error | 1.885 pixels; limit 3 pixels |
| Largest central depth error against the wall plane | Less than 0.00001 m; limit 0.03 m |
| Largest laser error across five bearings at each heading | Less than 0.000015 m; limit 0.01 m |
| Camera/laser mount and axis checks | All passed at all headings on both renderers |
| Headless startup / task reset / scene reload navigation | All three passed |

The wall's near face is two metres ahead of the RGB camera. Mount offsets make
expected central depth about 2.0700 m and forward laser distance about 2.1200 m.
The laser comparison also covers ±15° and ±30°. These small numerical errors
compare simulated data with analytical target geometry; they are not evidence
of physical sensor accuracy. Acceptance thresholds and decoding conventions are
documented in [RENDERED_SENSORS.md](RENDERED_SENSORS.md).

Each capture checks all four streams for valid 640×480 images, matching
calibration dimensions/frames, paired timestamps, advancing time, no timestamp
regressions, and freshness relative to the clock. Three images per stream are
saved, and every subsequent received image is decoded. Software rendering
yielded nine images per stream per measured capture; NVIDIA yielded 134–144.
The GPU runner caps the application at 30 fps, while publishers request 15 fps;
these checks do not certify an achieved frame rate or real-time performance.

Navigation used None / RandomABNav / seed 7 and external goals. The three
displacements were 0.6521, 0.6504, and 0.6534 m, with final goal errors 0.3479,
0.3496, and 0.3466 m. All stages had fresh sensors. One initial placement was
rejected, and task/scene reset clocks advanced without regression. No missing
laser-frame or transform-filter failure was found in the final navigation logs.

## Remaining findings and limits

The default seed-7 Warehouse startup view is occluded by shelving. The navigation
runner also rejects an initial placement before choosing a clear test start.
A separate acknowledged task reset produced the clear inspected views at ROS
position approximately (-10.5625, 2.6040, 0.0400). This milestone does not fix
or accept arbitrary task-start placement or camera clearance. Resolve that
before participant workflows rely on random starts.

The final rendered-player logs contain no managed exception, unsupported-shader
error, or fixture kinematic-body warning. The separate `-nographics` navigation
run retains its expected unsupported-shader messages. Transport teardown is
still unclean: its endpoint log contains two end-of-stream errors and one bad
file descriptor; two GPU capture endpoint logs each contain an end-of-stream
error on exit. These remain open transport findings, not sensor acceptance.

Depth remains a custom RGBA-packed PNG, not a standard metric ROS depth image.
The old ROS 1 depth synchronizer is not a validated ROS 2 consumer. The
synchronous readback fallback, arbitrary image sizes at runtime, changing poses,
repeated camera resets, all depths/angles, Warehouse map/collider accuracy,
photometric accuracy, throughput, participant control/recording, and ORCA remain
outside this result. Earlier import/legacy asset findings remain recorded in
[the clean-source report](CLEAN_BUILD_RESULT_2026-10-27.md).

## Evidence and reproduction

Authoritative paths on robovision:

- `/scratch/tchauhan/sean3/validation/rendered-sensors/20261027-baseline/`
- `/scratch/tchauhan/sean3/validation/rendered-sensors/20261027-fix6/`
- `/scratch/tchauhan/sean3/validation/rendered-sensors/20261027-fix6-gpu/`
- `/scratch/tchauhan/sean3/builds/rendered-sensors-20261027-fix6/`

Local evidence is under ignored `results/rendered-sensors-20261027/`.
The report, tools, and candidate pin are versioned; generated captures and
earlier attempts remain separate. Intermediate attempts preserve an incorrectly
transferred unchanged-source build, a test-reflection failure, a stripped
fixture shader, an out-of-range four-metre laser target, and missing frame
findings. They are not accepted runs. The final fixture uses an explicit shader
resource, a two-metre target within the laser's 3.5 m range, and frozen physics
without kinematic-body warnings.

Use [RENDERED_SENSORS.md](RENDERED_SENSORS.md) to reproduce captures and analysis.
Set `SEAN_CAPTURE_RESET=1` for the additional post-reset Warehouse view. Use the
existing navigation runner separately to repeat all three navigation stages.

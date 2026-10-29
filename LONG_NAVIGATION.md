# Longer Warehouse navigation

The configured Warehouse robot is Kuri, and the current navigation runner uses
`nav2_kuri.launch.py`. Earlier checks used `nav2_jackal.launch.py`; that historical
ROS profile name did not identify the live Unity robot. The player now logs
this identity explicitly.
This check drives the actual `RandomABNav` task goal with Nav2, rather than
substituting a one-metre test goal. It runs startup, task reset, and scene reload
in order. No rejected start or goal is silently replaced. Use at least seeds 7
and 42 and retain every attempted run, including failures.

## Protocol and acceptance

Use the paired component versions in the dated longer-navigation result.
Earlier transport-player baselines use their saved tooling snapshots. The
current long-route runner requires the explicit Kuri identity log. The runner uses `-external-goals` and
`-completion-distance 0`. The latter prevents the legacy 1.2 m / five-second
completion debounce from teleporting the robot before precise Nav2 completion.
The 3,600-second task timeout remains enabled; the harness independently limits
each goal to 300 wall seconds. This is an explicitly controlled evaluation
configuration, not validation of the legacy automatic task-completion rule.

Each stage requires a generated start and goal at least three metres apart,
free 0.6 m ROS-map footprints, an initial successful global plan, Nav2 action
success, final planar position error at most 0.4 m, displacement at least 0.5 m,
fresh sensor/task streams, no reported collisions, no translation stall, and no
bounded-motion stall.
The two resets retain the existing clock-continuity checks. Shutdown must pass
the existing full-log transport and process-exit checker. Normal route-level
failures are collected through all three stages; setup errors stop the run.

The JSON stores the initial global plan, sampled timestamped odometry, goal and
final pose, action status, wall time, simulation duration, accumulated path
length, turn angles, translation pauses, and collision-counter baseline/maxima.
A translation stall is at least 20 simulation seconds without moving 0.05 m
from an anchor. Rotations and recovery waits count as translation pauses, so
this measure is not proof of deadlock. A separate bounded-motion stall is at
least 15 simulation seconds without leaving a 0.5 m radius around an anchor.
It detects small circles that can keep resetting the 0.05 m translation anchor.
Both measures include turns and intentional waits; the accepted routes must
satisfy both. Routes must also keep wall receipt minus `/clock` stamp from
growing by more than 1.0 s, which detects a delivery backlog that `fresh()`
cannot see. Odometry is sampled approximately every
0.2 simulation seconds; sampling gaps are reported. Path length includes
odometry noise; planned and actual turn totals depend on sampling resolution.
Nav2 feedback records remaining distance and the maximum reported recovery
count. A trajectory sampling gap over one simulation second fails acceptance.
The initial path and a sampled 0.3 m straight-corridor map check describe route
geometry; they are not an independent swept-volume contact detector.

The legacy `obj_collisions` counter received object entries from every proximity
trigger and suppressed entries during its fall debounce. The new
`ObjectContactSensor` counts physical `OnCollisionEnter` events on the robot's
body, excluding tagged pedestrians and upward support normals with y >= 0.5
(floor/ramp support up to 60 degrees). One callback with several contact points
counts once; a separated second impact counts again. Side and overhead contacts
count during falls too. The per-trial metric resets through the existing
`Metrics` event; the sensor's diagnostic Count property is lifetime cumulative.
Pedestrian proximity metrics retain their legacy trigger implementation.

A physics regression exercises floor support, personal-space overlap, wall
impact, continued contact, a second impact, and pedestrian-tag exclusion. A
separate regression checks that the published object metric ignores proximity.
This does not certify all compound colliders, contact orientations, slopes,
penetrations, or missed events caused by discrete physics. Zero recorded events
is a bounded observation. There are no pedestrians in this fixture.

The active velocity-controlled rigidbody uses `VelocityControlledBody`: zero static/dynamic
friction with Minimum combination and zero restitution. Its existing actuator
sets rigidbody velocities directly each physics tick. Default floor friction
cancelled small commands; a captured stall commanded 0.0333 m/s while measured
translation was almost zero. The physics regression reproduces this deadzone
with the default material on a child collision shape, then checks the production
material setup preserves the commanded displacement. The wall-impact regression uses
the same production material and checks that the wall still blocks motion.

The velocity controller applies the resource material to all physical colliders
owned by its selected rigidbody. Triggers and independently owned child bodies
retain their materials. The player log records the actual selected robot and
material. This is an ideal velocity-controlled body, not a wheel traction/dynamics model.
Validation is limited to the configured Warehouse robot.

`nav2_kuri.launch.py` selects the dedicated Kuri profile. Its 0.60 m circular
footprint (zero additional padding) encloses the measured 0.2262742 m horizontal
collider envelope, with at least 0.30 m of clearance even allowing for polygon
approximation. The audit includes explicit wheel radii/suspension because
WheelCollider bounds can be empty in EditMode. It is a physical-collider bound,
not a guarantee about every visual mesh or camera-boom orientation.

The profile uses Nav2 Regulated Pure Pursuit with collision checking enabled,
a 0.6 m lookahead, 0.3 m/s desired speed, 0.05 m/s minimum regulated/approach
speed, curvature-based speed regulation, and a one-second collision-check
horizon up to the lookahead point. It rotates toward path/goal headings at up
to 1.8 rad/s. Local/global inflation extend to 1.0 m with cost-scaling factor
3.0. The velocity smoother retains its existing limits.
The Kuri navigator selects Nav2's installed
`nav_to_pose_with_consistent_replanning_and_if_path_becomes_invalid.xml` tree.
The recorded implementation checks validity at 2 Hz and expires the path after
10 simulation seconds, with replanning on goal changes/invalidity and the usual
recovery actions retained. Both costmaps mark and raytrace finite laser returns
through the configured sensor's full 3.5 m range. The earlier 2.5 m marking / 3 m
clearing limits discarded observed obstacles that were still visible farther
away. A captured failure alternated the initial path heading by approximately
180 degrees for the same goal. Full-range observation is evaluated separately
from the rejected goal/failure-only route-retention experiment.

Registration/removal now shares the endpoint executor's wait-set critical
section. A registration-ready gate and executor wake give the active client
priority over another idle wait, preventing starvation. Expected closure and
unexpected-error diagnostics remain visible. Regressions cover blocked removal
during wait-set construction and fifty create/remove cycles with a live executor.

The [upstream controller documentation](https://github.com/ros-navigation/navigation2/blob/humble/nav2_regulated_pure_pursuit_controller/README.md)
describes those parameters. The original Jackal/DWB profile remains available
through `nav2_jackal.launch.py`; it is not the current Kuri acceptance profile.
This changes navigation behavior and is not a pedestrian-controller comparison.
Reduced-rollout, rotation-shim, and mismatched-footprint experiments remain
separate failed evidence. See the dated result for live acceptance.

## Run on robovision

From `/scratch/tchauhan/sean3/sean3`, with no other run sharing the overlay.
Use the tf2-matched image and its own overlay workspace; the earlier `:dev`
image pairs tf2 0.25.22 with tf2_ros 0.25.24, which can deadlock Nav2's TF
listener (see [LONG_NAVIGATION_RELIABILITY.md](LONG_NAVIGATION_RELIABILITY.md)):

```sh
SEAN_ROS_IMAGE=localhost/sean3-humble:tf2-0.25.24 SEAN_CHECK_MODE=long-navigation \
  SEAN_SEED=7 SEAN_TCP_PORT=10327 \
  bash scripts/check_unity_navigation.sh \
  /scratch/tchauhan/sean3/builds/long-reliability-c01-20261028/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws_tf2 /scratch/tchauhan/sean3/social_sim_ros \
  /scratch/tchauhan/sean3/validation/long-navigation/NEW/seed7
```

Build the image with
`docker build -f docker/Dockerfile.humble-tf2 -t localhost/sean3-humble:tf2-0.25.24 docker`.
Repeat serially with seed 42, a fresh output directory, and an available TCP
port. `SEAN_GOAL_TIMEOUT` overrides the declared goal wall-time limit; record
the value and keep runs with different budgets distinct. Run the Python harness
regressions on robovision with `python3 -m unittest discover -s tests -p 'test_*.py'`.
See the dated result report for actual outcomes and exact source/tooling hashes.

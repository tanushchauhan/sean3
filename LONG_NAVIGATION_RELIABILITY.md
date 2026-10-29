# Long-route navigation reliability

Protocol for the Warehouse / None / RandomABNav Kuri long routes, written before
the qualification campaign. See [LONG_NAVIGATION.md](LONG_NAVIGATION.md) for the
route definition and per-route gates. The dated result reports actual outcomes.

## Diagnosis

Repeated failures circled, invoked recoveries and timed out even with the
historical accepted player and profile. A diagnostic run of the clean `3033ba1`
player recorded `/clock`, odometry, TF, commands and plans with system-time
receipt stamps, alongside per-process CPU samples:

- Unity published 10 transforms per rendered frame as 10 separate `/tf` messages
  (about 300 per second), plus `/clock` every 0.01 simulation seconds.
- The Python TCP endpoint averaged about 105% CPU, a saturated GIL-bound core.
- Wall receipt minus simulation stamp grew from 0.3 s to 25 s during the route.
  After navigation stopped, simulation time arrived 1.16 times faster than wall
  time. Unity's clock cannot outrun wall time, so that was a backlog draining.
- Cross-correlating commanded and measured yaw rate gave a command-to-odometry
  delay of 0.1 s at the start, then 2 to more than 8 s. Nav2 was steering from
  state that was seconds old, which explains overshooting rotations and circling.
- The checker's `fresh()` gate compares message stamps with `/clock`. Both
  arrive through the same delayed stream, so it could not detect the backlog.

Historical accepted routes ran at simulation/wall ratios of at least 0.992. The
heavy-recovery failures ran at 0.906 to 0.966. Machine load changes the endpoint
margin, which explains why the same player sometimes passed. Candidate13's
modern-profile scene route failed at an aggregate ratio of 0.993, so a whole-route
ratio does not explain every earlier failure.

## Repair

Unity now publishes each frame's transforms as one `TFMessage`, so it sends the
same transforms, stamps and rate in about 10 times fewer messages (Unity
`1fec526`). With the same seed, checker and instrumentation, endpoint CPU fell to
about 42%, the receipt offset stayed at 0.20 to 0.23 s, and round-trip delay
stayed at 0.05 to 0.15 s. Startup and task routes passed with zero recoveries.

## Checker changes

- **Receipt-lag gate (new, stricter).** Each route records wall receipt minus
  `/clock` stamp. A route fails if this grows by more than 1.0 s from the
  route's first sample. A player stall also counts as growth. Either way Nav2
  acted on old state, so the gate is conservative.
- **Reset anchor.** The checker blocks while Nav2 shuts down. A `planner_server`
  that ignores SIGINT can block it for 15 s. The previous anchor was the last
  clock sample before that block, which inflated the reset's simulation-time
  interval by up to the shutdown duration. In the confirming run that gave
  13.4 s of clock across 3.3 s of wall time. The checker now waits for a clock
  sample received after shutdown. The clock-continuity limit is unchanged.

No deadline, freshness, contact, stall or goal-error threshold was relaxed.

## First campaign (q01) and a second failure mode

Campaign q01 ran the Unity `1fec526` player with the unchanged ROS image. It
was stopped after five of twelve sequences: s01 (seed 7) and s05 (seed 42)
passed; s02 (42), s03 (1001) and s04 (7) failed, 10 of 15 routes passing.
Receipt-lag growth stayed at or below 0.06 s on every route, so the backlog
was gone. Every failed session showed a signature absent from about 50 earlier
Nav2 sessions: "Resulting plan has 0 poses", "Controller patience exceeded",
and "Pose Goes Off Grid" from the behavior server.

Instrumented runs (d04, d05) showed the cause. The local costmap's origin froze
while `/tf` on the wire stayed regular and correctly stamped. `controller_server`
kept steering from a frozen pose, so the robot left its plan and twice struck
an obstacle. Thread stacks captured at the freeze (g01) showed a deadlock:

- the TF listener thread blocked in a ready callback called from
  `BufferCore::testTransformableRequests`, and
- the laser `MessageFilter` thread blocked in `BufferCore::addTransformableRequest`
  called from `tf2_ros::Buffer::waitForTransform`.

The image paired `ros-humble-tf2` 0.25.22 with `ros-humble-tf2-ros` 0.25.24.
tf2_ros 0.25.24 holds its timer lock while requesting tf2's request lock. tf2
0.25.22 calls ready callbacks, which take that timer lock, while holding the
request lock. Upstream fixed both sides together in 0.25.24 (geometry2 #990).
The Dockerfile installed `ros-humble-tf2-ros` explicitly and left `tf2` at the
base image version. Nav2's `getCurrentPose` returns the latest stored transform
without an age check, so the frozen pose produced no error.

The mismatch predates the batching change. Batching made the deadlock far more
frequent in these runs, but a shared-mutex race can occur with either TF shape.

## Repair (environment)

`docker/Dockerfile.humble-tf2` derives `localhost/sean3-humble:tf2-0.25.24`
(ID `360d1c5b...`) from the recorded image and upgrades only `ros-humble-tf2`
to 0.25.24-1jammy.20260915.203746. A dry run confirmed that no other package
changes. `docker/Dockerfile.humble` now installs `ros-humble-tf2` explicitly and
fails if the two versions differ; that from-scratch build is not yet tested.
The old image is kept for reproducing earlier results. The new image uses a
separate overlay workspace (`ros_ws_tf2`) so build products are not mixed.

## Qualification campaign (q02)

- Player: Unity `1fec526` (the transform batching on `3033ba1`), ROS `cceff5b`
  unchanged, profile `params/kuri/nav2_params.yaml` unchanged, image
  `localhost/sean3-humble:tf2-0.25.24`.
- Twelve serial sequences, each a fresh player and endpoint with startup, task
  reset and scene reload: seeds 7 and 42 three times each, seed 1001 once, plus
  five seeds not used before (2002, 3003, 4004, 5005, 6006) once each. Runs are
  interleaved to spread host-load conditions.
- Every route must meet all gates in [LONG_NAVIGATION.md](LONG_NAVIGATION.md),
  plus the receipt-lag gate. Each sequence's runner must exit zero, which
  includes transport, process-exit and Kuri-identity checks.
- Nav2 child processes that need SIGTERM or SIGKILL at shutdown are counted and
  reported against the clean-shutdown requirement. They do not fail routes.
- No bag recorder runs during qualification. A host CPU sampler records load.
- Every attempt is retained. A failure is reported as a failure, and later
  successes do not erase it.

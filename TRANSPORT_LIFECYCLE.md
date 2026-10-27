# Connection lifecycle checks

The transport candidate upgrades the Unity connector and ROS endpoint together.
Use the paired revisions in `sean3-candidate.repos`. The endpoint adaptation is
installed by the existing ROS package; no new upstream repository or image
is required. It retains the pinned endpoint protocol and adds a local
`__disconnect` command for orderly closure. An older upstream endpoint does not
implement that command, so it cannot satisfy this candidate's clean-close checks.

## Ownership and shutdown

Unity captures and retains each connection task and cancellation source. A
scene replacement cancels outgoing work and joins that task before clearing the
connection owner. Queued system-command serialization is protected from
concurrent callbacks, and reconnect publisher registration uses the connected
stream before queued topic data. Each reader has private framing buffers and
returns on frame-boundary EOF; truncated frames fail. A failed reader also
stops queue draining. Connection attempts have a cancellation/timeout guard.
The outgoing wait handle is disposed after the worker stops.

For an expected close, Unity writes `__disconnect` after completed outgoing
frames and half-closes its write side. The endpoint detaches the outgoing ROS
queue, wakes and joins its sender, then closes the socket. Unity keeps reading
until the endpoint's FIN before completing disposal. The connector allows two
seconds for that drain and four seconds for its worker join; failures remain
visible. Normal writes retain the existing synchronous behavior. These bounds
do not certify all unresponsive-peer or sustained-backpressure conditions.

The endpoint owns its listener, active client, sender thread, and a two-thread
ROS executor. The old client must stop before a replacement starts. Pending
Unity-service requests are released on disconnect. The executor has a strong
owner and bounded spin waits so SIGINT/SIGTERM can interrupt idle operation.
Malformed frames, unexpected send/receive failures, unannounced EOF, and forced
replacement are observable. They are not treated as clean expected transitions.
The endpoint adaptation's Apache-2.0 license is included and installed.

The validation runners wait for the endpoint's post-bind ready message before
starting Unity. A host port forwarder can accept TCP before the endpoint inside
the container is ready; the runner avoids probing it with an extra connection.
At exit, runners stop Unity while Xvfb and the endpoint remain alive, wait for
the player, stop ROS launch with SIGINT, collect complete logs and exit state,
and remove the owned container. They record forced player kills and nonzero
process exits as failures.

## Reproduce

On robovision, from `/scratch/tchauhan/sean3/sean3`, after importing the candidate
and building the Linux player with the pinned licensed editor:

```sh
SEAN_ROS_IMAGE=localhost/sean3-humble:dev SEAN_CHECK_MODE=lifecycle \
  SEAN_LIFECYCLE_PAIRS=6 SEAN_TCP_PORT=10328 \
  bash scripts/check_unity_navigation.sh PLAYER \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros NEW-RESULTS
```

This runs six task resets and six scene reloads, with a recent angular command
before each transition. It checks a single publisher/subscriber graph, fresh
odometry/laser/clock, one task per request, clock continuity, and ≤0.03 m drift
in each stationary two-second window. After the first warm-up pair, player and
endpoint growth limits are 128 MiB RSS, four threads, and eight descriptors.

Run navigation separately with `SEAN_CHECK_MODE=navigation` and
`SEAN_REQUIRE_CLEAR_START=1`. For rendered operation use
`scripts/check_rendered_sensors.sh` with `SEAN_VGL_DEVICE=egl4`; adding
`SEAN_PLACEMENT_RESETS=1` also exercises twenty task resets and two scene reloads.
See [PLACEMENT.md](PLACEMENT.md) and [RENDERED_SENSORS.md](RENDERED_SENSORS.md).
Use fresh result directories and only the owned player/container.

Both runners now execute `tests/lifecycle_log_check.py` after shutdown. Acceptance
requires zero connection/reader/queue/close errors, no native or display crash,
exactly one announced close and disconnect per expected connection, player
wrapper exit zero, endpoint exit zero, and no forced player kill. End-of-stream
errors and reset-by-peer writes previously tolerated by the historical checker
now fail. Captured images still require separate sensor analysis.

Endpoint regressions run inside the recorded ROS image:

```sh
docker run --rm --network none \
  -v /scratch/tchauhan/sean3/social_sim_ros:/source:ro \
  -v /scratch/tchauhan/sean3/sean3/tests:/tests:ro \
  localhost/sean3-humble:dev python3 /tests/endpoint_compat_check.py \
  /source/social_sim_ros/scripts/sean_tcp_endpoint -v
```

These cover registration compatibility, twenty orderly sessions under outgoing
traffic, abrupt EOF, truncated frames, replacement ownership, listener/idle-client
cleanup, a service response and pending-service cancellation, and real subprocess
exits on both SIGINT and SIGTERM. The malformed and abrupt cases deliberately
produce observable diagnostics. They are fault-injection tests, not clean live
runs. Full ROS-service interoperability and general network-fault recovery are
not certified by these bounded checks.

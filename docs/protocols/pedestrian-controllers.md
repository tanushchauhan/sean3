# Scene-level pedestrian controllers

Social Forces remains the default. ORCA is an explicit experimental selection;
`joint_test` is a goal-following test double with no avoidance. None of these
selects a different robot policy: Nav2 still owns the robot in normal runs.
No trained STARS controller is available in this interface.

Pedestrian actuation is separately selected with `--pedestrian-actuation`.
Social Forces defaults to `root_motion` (`AnimatedRootMotionV1`) for backward
compatibility. Joint controllers use `velocity_body` (`VelocityTargetsV1`),
which disables animation translation and applies planar rigidbody velocities
while retaining gravity and physical contacts. Use **velocity_body for both
controllers** in a matched comparison. The root-motion ORCA prototype is retained
as diagnostic evidence; it exhibited uncommanded velocity spikes and is not the
current actuation condition.

## Launcher

Build the matching player with the existing launcher, then use:

```sh
./sean3 run --pedestrian-controller orca --scenario Random --seed 7
```

Pass `--player`/`--ros-source` for existing alternate checkouts. The launcher
requires the player's startup log to confirm a nondefault controller/actuator before
starting Nav2. An older player that ignores the new flag cannot silently become
an ORCA run. The 65-person Random scenario is an experimental use case, not
coverage supplied by the small controlled encounter results.

| Parameter | Launcher option | Encounter runner environment | Default |
| --- | --- | --- | --- |
| Decision period, seconds | `--orca-decision-period` | `SEAN_ORCA_DECISION_PERIOD` | 0.1 |
| Neighbour centre distance, metres | `--orca-neighbor-distance` | `SEAN_ORCA_NEIGHBOR_DISTANCE` | 5 |
| Maximum neighbours | `--orca-max-neighbors` | `SEAN_ORCA_MAX_NEIGHBORS` | 64 |
| Actor horizon, seconds | `--orca-agent-horizon` | `SEAN_ORCA_AGENT_HORIZON` | 2.5 |
| Obstacle horizon, seconds | `--orca-obstacle-horizon` | `SEAN_ORCA_OBSTACLE_HORIZON` | 2.5 |

All values must be positive and finite. Decision periods must be an integer
number of physics steps. They are never silently rounded. For a separate
physics-step sensitivity pair, declare a 0.2-second decision period for both
0.02- and 0.04-second physics runs. Do not confuse that pair with the default
0.1-second decision condition. Parameters are recorded in the player report and
checked against the runner's request.

## Implementation and physical assumptions

The managed C# solver is the official RVO2-CS `v2.0.1`, source
`5b7147d36d5cc6310c8e74c6955145c0fdc5fe06`, vendored with Apache-2.0 notices
and original source hashes in Unity's `Assets/ExternalAssets/RVO2/upstream.json`.
This tagged source supports the existing Unity runtime; inspected current main
targets .NET 10. No native library or Unity/ROS upgrade is introduced.

Two local solver changes are declared: serial joint stepping avoids per-step
thread/wait-handle allocation; external-control flags give a pedestrian full
avoidance responsibility versus an externally driven robot or inactive context
actor. Two active pedestrians share responsibility equally. The solver's robot
output is discarded. An active person with zero preferred velocity is still a
reciprocal actor and can move to avoid others; inactive does not mean standing.

Each decision reconstructs the singleton solver under a lock from one immutable
actual-state snapshot. It steps once, extracts bounded velocities, and discards
the solver's integrated positions. Stable actor sorting removes input iteration
order as a solver assignment choice. Unity retains animation, contacts and
physics. Joint avatars use `AnimatePhysics` and bypass `Base.Update` control;
there is no second per-avatar solver step or root-motion translation added to
the physical target. The optional SF velocity actuator also runs its force
update at the fixed physics boundary; the default SF root-motion path retains
its prior update behavior. Reset, disabled ownership, invalid
output and controller exceptions stop pedestrian targets and achieved velocity.
The synchronous in-process call stalls wall time while physics waits. A future
separate worker still needs timeout/transport handling.

Pedestrian radius comes from its actual capsule; the robot radius is a declared
conservative horizontal bound on its owned physical collider bounds. Metrics
continue to use the full capsule/wheel geometry, separately from this model
approximation. Physical footprints and the shared VelocityBodyV1 contact
material are unchanged. Achieved motion error is measured; exact tracking
of an ideal ORCA velocity and unconditional collision freedom are not claimed.

`NavMeshBoundaryV1` uses the robot's connected baked walkable floor, preserving
ramps with a valid horizontal projection. Triangle edges are welded at 1 mm;
internal edges are removed, and boundary loops orient walkable space to the
right, matching RVO's solid-space convention. Open/nonmanifold boundaries,
overlapping projected triangles and stacked levels fail explicitly. An actor
without a complete NavMesh path to the robot's floor stops the entire joint
scene; it is never removed to obtain a pass.

These boundaries already include the bake's navigation clearance. Adding the
actor radius is an explicit conservative extra margin, rather than a claim
that the polygons are measured wall surfaces. Boundary-based geometry may
overconstrain narrow spaces. Rebuild/reinitialize the controller after geometry
changes; live moving-obstacle geometry is not supported.

## Matched encounters

Use the existing Warehouse fixture and independent analyzer. With new result
directories and a matching player, run the same command for both controllers:

```sh
SEAN_ROS_IMAGE=localhost/sean3-humble:local SEAN_TCP_PORT=10371 \
  SEAN_PEDESTRIAN_CONTROLLER=social_forces SEAN_ENCOUNTER_SEEDS=7 \
  SEAN_PEDESTRIAN_ACTUATION=velocity_body \
  SEAN_ENCOUNTER_LAYOUTS=aisle SEAN_ENCOUNTER_MODES=parked,nav2 \
  bash scripts/check_warehouse_encounters.sh PLAYER ROS_WORKSPACE ROS_SOURCE NEW_RESULTS_SF

SEAN_ROS_IMAGE=localhost/sean3-humble:local SEAN_TCP_PORT=10371 \
  SEAN_PEDESTRIAN_CONTROLLER=orca SEAN_ENCOUNTER_SEEDS=7 \
  SEAN_PEDESTRIAN_ACTUATION=velocity_body \
  SEAN_ENCOUNTER_LAYOUTS=aisle SEAN_ENCOUNTER_MODES=parked,nav2 \
  bash scripts/check_warehouse_encounters.sh PLAYER ROS_WORKSPACE ROS_SOURCE NEW_RESULTS_ORCA
```

This selects two mirrors and two robot modes: four episodes per controller.
Seed 7 is development, with the same deterministic avatar assignments. Starts,
goals, robot profile, physical contacts, 45-second deadline and geometric gates
remain those of the [Warehouse protocol](warehouse-encounters.md).

ORCA reports additionally retain source revision, actual parameters, geometry
model/count, conservative robot radius, controller episode/sequence, target and
achieved velocities, named actuator, failure status and per-decision wall latency. The analyzer
rejects wrong controller provenance, missing timing/velocity data, epoch changes,
sequence regressions and worker faults. It reports latency p50/p95/max and
position-derived achieved-versus-target velocity error. Targets on the
interval-ending post-physics sample are aligned with that physics interval.
Moving and stationary error strata use a declared 0.01 m/s cutoff on either
target or achieved speed, preventing long terminal waits from masking moving
errors. Those diagnostics do
not replace physical contact or goal outcome checks. Failed episodes and partial
reports remain evidence; no acceptance threshold is changed for ORCA.

The draft `configs/experiments/schema.json` remains a design schema, not an
executable launcher configuration. Broader open-floor encounters, independent
seeds, doorways, real-time measurements and three-controller comparisons require
their own frozen configurations and runtime evidence.

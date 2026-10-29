# Scene controller contract, version 1

Implementation: the standalone `SEAN.Controllers` Unity assembly in the sibling
Unity checkout, `Assets/Scripts/SEAN/Scenario/Controllers/SceneController.cs`.
The core is now connected to production animated avatars by the opt-in
`JointAgent` and `JointControllerDriver` path. Social Forces retains its existing
per-avatar `Update`, animation and physics. ORCA uses this shared path; the
explicit `joint_test` option supplies a goal-following test double. No STARS
inference has been implemented yet. A bounded local TCP worker and history
buffer are available; see the [worker protocol](stars-worker.md). This does not
provide full ROS lockstep. See the
[controller protocol](pedestrian-controllers.md) for selection and assumptions.

## State and frames

One immutable `SceneSnapshot` contains a fresh episode ID, sequence, simulation
time, actors sorted by stable ordinal ID, and obstacle polygons. Each actor has
position, achieved velocity, heading, active mask, footprint radius, maximum
speed, optional destination and optional path-derived preferred velocity.
Exactly one actor is the externally controlled
robot. Actor identity is independent of array order. An inactive actor remains
context but receives no target; an active stationary person receives zero
velocity. Inactive is not another name for standing.

Planar values use the ROS map FLU frame: metres, seconds, radians, positive
heading counterclockwise from +x. Unity `(x,y,z)` maps to ROS `(z,-x,y)`;
Unity yaw maps to negative ROS heading. The contract's Vector2 is ROS `(x,y)`,
not Unity `(x,z)`. Root height remains Unity-owned. Circular pedestrian radii
must come from physical colliders. The radius on a robot state is only a
conservative bound; production adapters must preserve its full body geometry
for physical clearance metrics. Polygons must represent verified obstacle
geometry; the current DTO does not validate winding, intersections or mesh
coverage. STEPS/GDC calibration is **unavailable**: no transform is implied.

Existing ROS `Agent`/`AgentArray` carry identity, pose and velocity, but lack
episode/sequence, masks, physical shape, goals and obstacles. `TrialInfo` and
`SceneInfo` carry task metadata but do not supply the required scene boundary.
Keep these compatibility topics; introduce a separate versioned transport for
snapshots/decisions when the ROS bridge is implemented.

## Decision and lifecycle

1. The simulation owner captures actual executed state at a decision boundary
   and calls `BeginStep`. It must not advance physics while the response is
   pending. `Step` is the synchronous in-process convenience path.
2. One joint call returns a `SceneDecision`: episode, source sequence, source
   simulation time, exclusive validity endpoint, and one planar velocity target
   per active pedestrian. Robot targets are rejected. Velocities are world
   metres/second, not displacements. They are held constant over the short
   execution horizon; predictive adapters must explicitly convert their selected
   displacement segment to this representation.
3. Validate the entire batch before calling `ISceneMotionSink.Commit` once.
   Reject missing/duplicate/unknown actors, robot targets, nonfinite or excessive
   speed, old episode/sequence/time, duplicate application and excessive horizon.
   Do not silently clip, fall back to SF, or omit difficult actors. Rejected
   asynchronous packets leave the pending request intact; the owner waits for
   the correct response or declares worker failure.
4. The sink replaces all targets without advancing any actor. A production sink
   must implement this operation atomically on Unity's simulation thread. Unity
   owns animation/physics and supplies achieved positions at the next boundary.
   The production sink assigns all targets before animating any actor, then
   applies them at the shared physics boundary. Joint avatars use
   `AnimatePhysics` and bypass the legacy per-avatar `Update` path. Tests cover
   both deterministic planar integration and actual production root motion.
   Following error remains a measured quantity rather than exact actuation.
5. Call `Tick` on every physics boundary to enforce expiry and clock ordering.
   Advancing time with a pending response stops motion and faults the episode.
   Worker exceptions or invalid synchronous responses stop motion and require a
   fresh reset. The socket transport bounds wall time; the driver calls `Fail`
   on worker loss. Stop must clear pedestrian animation targets and
   rigidbody velocities, without touching the Nav2-owned robot.
6. Reset uses a never-reused episode ID even though the simulator's ROS clock
   can remain continuous. Stop the sink before clearing controller history and
   latent state. Reset must occur before any new capture. Dispose stops the sink
   and disposes the controller. IDs may change between snapshots in the core;
   a fixed-population STARS adapter must reject unsupported spawn/despawn.

The core is single-threaded. The production driver makes one synchronous
controller call at its configured integer-physics-step cadence and applies
zero-order-held velocity targets. It resets on the registered task's new-task
event and population changes; scene destruction disposes it. Arbitrary task
switching still requires lifecycle qualification. The local socket adapter
returns on the simulation thread with a bounded wall timeout. The core alone
does not establish lockstep Unity/ROS stepping; Nav2 remains an asynchronous external robot controller.

For STARS, derive decision cadence and observation/prediction lengths from the
checkpoint configuration. Collect actual history while holding the actors at
their declared starts during warm-up, label this initialization, and do not
invent missing observations or move actors with another controller. Eight
sample instants span seven sample intervals. Match supported preprocessing and
masks before enabling inference. The model-independent worker tests warm-up and
physical animation; no learned-model acceptance is claimed here.

## Experiment configuration

`configs/experiments/schema.json` is a draft 2020-12 structural schema, not yet
a launcher input. It separates pedestrian controller and robot policy, model
and scenario seeds, geometry version, starts/goals/footprints, synchronous
timing, split and model provenance. Hashes refer to real inputs; placeholders
must not become run evidence. Runtime semantic validation must additionally
check unique IDs, exactly one robot, supported shapes, finite values, cadence
compatibility, footprint resolution, matching input hashes, and policy ownership.
The free-form controller parameters need adapter-specific validation.

The Nav2 path currently connects its smoother directly to the robot command
topic. Before adding robot policies, introduce one command owner at that final
topic and test graph exclusivity. A configuration field alone does not enforce
arbitration. Do not run a learned robot publisher alongside Nav2.

## Gate and next implementation

`SceneControllerTests` exercises joint ordering, executed-state feedback, reset,
stale packets, malformed batches, worker failure, expiry, shutdown and coordinate
conversion. `JointAvatarTests` executes two production animated avatars through
the driver and checks achieved feedback, reset and worker-loss stopping.
`OrcaControllerTests` adds crossing, robot, standing-person, wall/corner/doorway,
order and lifecycle cases; geometry tests validate the boundary convention.
The matched runtime encounter protocol extends these checks with actual Kuri
and physical contact/goal measurements. Full ROS lockstep, additional robot-policy
arbitration and trained-model validation remain future gates. Preserve the default SF+Nav2 regression fixtures.

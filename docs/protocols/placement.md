# Warehouse random-task placement

The supported `SEAN/Warehouse`, `None`, `RandomABNav`, Kuri fixture samples
start/goal pairs subject to three constraints:

- A uniform point inside one area-weighted navigation-mesh triangle, with at
  least 0.65 m to the mesh boundary.
- A clear world-aligned column with horizontal half-width 0.65 m, from 0.1 to
  3.7 m above the sampled surface. This covers the robot and overhead camera
  column. The robot's own colliders and triggers are excluded.
- A clear 0.7 m circular footprint in the pinned Warehouse ROS map. The
  independent ROS check uses 0.6 m, leaving one map cell of margin.

The saved placement checks use `nav2_jackal.launch.py`, the historical ROS
profile name. That name does not identify the live Unity robot. Earlier versions
of this guide incorrectly called the configured Kuri fixture Jackal; placement
results do not qualify the Jackal model.

Pairs must be at least three metres apart and have a complete Unity navigation
path. Sampling stops after 256 candidate pairs. Failure leaves the current task
unchanged and retries after five seconds; the periodic goal publisher waits
until the first successful task. Surface elevation is retained, with the
existing 0.75 m body-drop and 0.5 m goal-marker offsets applied above it.

Only RandomABNav uses this sampler. Other task and pedestrian samplers retain
legacy behavior. Random sequences change from the earlier implementation.
Repeatability tests cover a restored RNG state with unchanged scene geometry;
this is not a cross-platform determinism guarantee.

## Map snapshot

`Assets/Resources/SEAN/Placement/Warehouse.json` in the Unity repository contains
a free-cell bit mask, ROS origin/resolution, source revision, and source hashes.
It is derived from `social_sim_ros/social_sim_ros/maps/warehouse/short_map.png`
and `map.yaml` at ROS commit `2ac78a303d323fbce0caad83555dbe940cc40435`.
The map uses 800×800 cells, 0.1 m resolution, origin (-40, -40), zero yaw,
trinary thresholds 0.5, and negate=false. Bits are indexed by ROS row from the
bottom, then column, least-significant bit first. Unity position converts to
ROS map coordinates as (z, -x).

Regenerate from the workspace root whenever the supported ROS map changes:

```sh
python3 sean3/tests/export_placement_map.py \
  social_sim_ros/social_sim_ros/maps/warehouse \
  social_sim_unity/Assets/Resources/SEAN/Placement/Warehouse.json
```

The exporter rejects unrecognized YAML settings. Review its source revision
when changing the map. Commit the updated map and snapshot together with their
candidate pins. A custom map override needs a matching placement profile;
this snapshot is not negotiated with an arbitrary running map server. It
constrains navigation compatibility without asserting map/collider accuracy.

## Reproduce the bounded checks

Run Unity EditMode assembly `SEAN.Editor.Tests` with the pinned Linux editor.
Build the committed candidate using `scripts/build_unity_player.sh` and verify
its `player-tree.sha256`. See [validation history](../validation.md) for editor commands.
On robovision, from `/scratch/tchauhan/sean3/sean3`:

```sh
SEAN_VGL_DEVICE=egl4 SEAN_SEED=42 SEAN_PLACEMENT_RESETS=1 \
  SEAN_CAPTURE_SECONDS=25 SEAN_TCP_PORT=10326 \
  bash scripts/check_rendered_sensors.sh \
  /scratch/tchauhan/sean3/builds/placement-20261027-goal-guard/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros \
  /scratch/tchauhan/sean3/validation/placement/NEW-rendered-run

SEAN_ROS_IMAGE=localhost/sean3-humble:dev SEAN_REQUIRE_CLEAR_START=1 \
  SEAN_SEED=7 SEAN_TCP_PORT=10327 bash scripts/check_unity_navigation.sh \
  /scratch/tchauhan/sean3/builds/placement-20261027-goal-guard/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros \
  /scratch/tchauhan/sean3/validation/placement/NEW-navigation-run
```

Use fresh output directories. Do not run these against another user's player,
endpoint, or ROS graph. DDS stays inside each owned container; TCP binds to
localhost. Use an available VirtualGL device on the host, or omit it for Mesa.

The rendered runner first waits for an acknowledged, settled initial task.
It captures all four image streams, then optionally runs:

- An opt-in Unity audit of 100 pairs across seeds 0, 1, 7, 42, and 12345. The audit
  restores the application's RNG state and does not teleport the robot.
- Startup, twenty actual task resets, and two actual scene reloads. Each checks
  fresh odometry/laser/metrics, settled height 0.04 ±0.05 m, 0.6 m free ROS-map
  footprints for both start and goal, laser minimum ≥0.3 m, and a successful
  Nav2 global plan to that task's goal. No placement is silently replaced.

Run `tests/analyze_rendered_sensors.py RESULT/capture` separately, using the
existing [sensor criteria](rendered-sensors.md). Inspect saved views as well as
JSON. The navigation runner's strict mode fails on the first rejected placement
instead of requesting a substitute; it drives short one-metre clear-path goals
at startup, after a task reset, and after a scene reload.

These checks do not drive every generated long task, qualify all camera-boom
orientations, validate pedestrian scenarios, or repeat the resource-growth
stress test. Scene resets may briefly produce Nav2 costmap-origin warnings
while rolling costmaps catch up to teleports. Transport shutdown remains open.

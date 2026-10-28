# Populated Warehouse encounters

This milestone evaluates the actual Warehouse floor, racks, baked NavMesh,
production animated SFAgents and Kuri. It requires neither participant-interface
prototype. It does not claim human realism or qualify a participant study.

## Protocol declared before live trajectories

Four people, fixed placements, two layouts (`aisle`, `rack_end`), and lateral
mirrors -1/+1. **Layout version 2** was chosen from the saved baked-mesh geometry
before any live pedestrian trajectories: the first proposed absent pose (5,-15)
was off mesh, and an audit also found several proposed rack-end poses invalid.
Candidates4/5 retain those setup rejections; no failures were replaced inside a
run. The map alone was insufficient to choose these scene coordinates.

The aisle retains Unity x/z centre (-5,5), robot start/goal at longitudinal
+/-4 m, and four people at lateral +/-0.65 m, depths +3.5/+5 m, aiming at
-5/-3.5 m. The rack-end centre is (-5,-8); robot crosses laterally from -4 to
+4 m about that centre. People start in the aisle at lateral +/-0.65 m and
longitudinal +3.5/+5 m, then turn around the rack end toward goals at lateral
(4+lane) m and longitudinal -5/-3.5 m. Mirror multiplies all lateral offsets
by -1/+1, including robot endpoints and pedestrian goals. This exercises left
and right turns in the real, not necessarily symmetric physical scene.
Parked places Kuri at the layout centre. Absent uses fixed Unity (1,-15).

**Layout version 3** preserves those horizontal starts/routes but orders terminal
goals downstream: the leading pair has depth -5 m and the trailing pair -3.5 m.
Version2's no-robot controls exposed a terminal queue: early arrivals stopped
across the trailing route, which missed the deadline without contacts. Those
failures remain candidate6 evidence; version3 is a finite through-flow fixture,
not qualification of dense terminal queues or an improved person/person model.
No pedestrian force, speed, deadline, contact threshold or start was changed.

Every point must lie within 0.2 m of the baked NavMesh, with a complete initial
path. Robot endpoints require the existing map/physical 0.65 m placement check.
Person endpoints require clear physical capsules. No rejected pose, seed or
layout is replaced. Actual sampled surface elevation and path corners are saved.

Profiles are held fixed: ColliderV1 forces, VelocityBodyV1 contacts, desired/max
walking speed 0.6 m/s; no pedestrian force retuning is part of this milestone.
Avatar selection is `(seed+personIndex) modulo template length`; seed variation
is limited, not an independent population sample. The ordinary production
NavMesh planner, animator, root motion and physical collisions remain active.

The diagnostic holds Kuri upright at the sampled mesh elevation plus 0.05 m,
with independently owned child bodies frozen; pedestrians retain gravity and
production root motion. Robot conditions use identical contact physics and
vertical constraints. This is planar controlled-body navigation, not wheel
traction/dynamics. Normal navigation without this flag is checked separately.
Recorded heights must remain within 0.01 m for the robot and 0.25 m of each
person's starting mesh height; floor fall-through cannot count as success.

Conditions:

- `absent`: stationary robot outside the encounter, to isolate person/wall motion.
- `parked`: stationary robot in the encounter centre.
- `oblivious`: Kuri follows the saved NavMesh corners at 0.3 m/s, ignoring people.
- `yielding`: same robot route/speed, stopping while any person is within 2 m
  and ahead (longitudinal dot product greater than -0.2 m); resumes as clear.
  This is an explicit oracle control with exact simulated positions.
- `nav2`: existing Kuri Nav2 profile, actual action server/planner, live laser,
  clock, odometry, and published four-person stream. Nav2 owns motion; the
  fixture neither substitutes velocities nor replaces the route. Costmaps are
  cleared between fixed teleports; initial global path and action feedback saved.

Each case has a fixed **45 simulation-second** deadline and locks frame/physics
steps to 0.02 s, paced at 50 fps. Larger-step repeats use 0.04 s at 25 fps.
Normal runs without the flag retain their existing stepping. Nav2 handshake has
a separate 120 wall-second setup bound; it occurs with all actors frozen.
Development seeds **7,42**; reserve **12349** for an unchanged-model final check.
Any failure/repair and subsequent seed reuse must be recorded explicitly.

## Acceptance and outcomes

Require exact requested seed/layout/mirror/mode coverage; no duplicates, missing
cases, nonfinite poses or sample gaps above 1.5 steps. Initial recorded poses
must match declared placements. Every person must reach within the existing
1 m goal threshold; moving robots must reach within 0.4 m. Stationary controls
must remain within 0.01 m of their declared pose. The independent analyzer
recomputes person/person clearances and goal distances from raw positions.

All modes require zero person/person and environment contact callbacks and no
sampled person/person overlaps. Parked, yielding, Nav2 and absent additionally
require zero physical robot/person callbacks and no sampled robot/person body
overlaps. Oblivious robot/person contacts remain measured outcomes, not grounds
to omit a case or make this deliberately poor control fail the entire matrix.
Person/person callbacks are raw counts recorded on both bodies, not unique
contact events. Physical callbacks are separate from analytic Kuri capsule/wheel
horizontal clearances. Neither certifies collision freedom between samples.

Report completion times, path lengths, minimum clearances, longest 0.1 m anchor
pauses, contacts, and yielding duration. Pauses include intentional waits;
missing the unchanged deadline measures unresolved progress, not proof that any
particular brief pause is a deadlock. Keep safety and benchmark difficulty
separate. A paired yielding/oblivious encounter distinguishes the controls when
yielding improves minimum robot clearance by at least **0.10 m** or reduces
physical robot/person contacts. Report every pair; do not select favourable
layouts or infer population significance. A safe matrix without that distinction
is not a demonstrated controller benchmark.

Require full-log transport and script/native-error audits, clean process exits,
Unity tests, harness regressions and normal navigation checks. Final source must
also pass a new clean-source build before qualifying a reproducible baseline.
Earlier rendered-sensor results remain tied to their original source versions.

## Run

Serialize all players, editors and ROS overlay jobs on robovision. From
`/scratch/tchauhan/sean3/sean3` with a new result directory:

```sh
SEAN_ENCOUNTER_SEEDS=7,42 SEAN_ENCOUNTER_STEP=0.02 \
  bash scripts/check_warehouse_encounters.sh /absolute/player/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros \
  /absolute/new-results-directory
```

`SEAN_ENCOUNTER_LAYOUTS` and `SEAN_ENCOUNTER_MODES` select explicit diagnostic
subsets; they cannot stand in for the full declared matrix. Defaults include
both layouts and all five conditions. The runner retains raw trajectories,
actual setup paths/avatars, Nav2 plans/feedback, script logs and closure evidence.
Failed attempts use fresh directories and remain available.

## Diagnostic integrity

The encounter JSON/case index, not the disabled random task's legacy TrialInfo
timer or goal, supplies the per-case metrics. The normal task does not reset
between these diagnostic encounters. The four-person population is published
through the existing agent streams; Nav2 uses normal laser/odometry/clock inputs.

Candidate7's first full development run exposed a recording/setup ordering bug:
a second complete JSON snapshot was written after issuing the Nav2 request.
As the accumulated trajectories grew, that blocked Unity long enough for a
Nav2 case to fail the unchanged sensor freshness gate despite reaching its
goal without contacts. The full attempt remains unaccepted. The repair removes
that duplicate write; the snapshot completes before publishing the request.
Large report writes are timed in the player log and all remain outside live
Nav2 actions. The driver now retains detailed stale-sensor ages on failure.
No sensor threshold, force, contact profile, speed, goal or deadline was relaxed.

Candidate7 also exposed a separate planar-fixture constraint defect: rotation
was frozen on every axis. Straight Nav2 aisle actions could finish, but Nav2
could not turn around pedestrians at the rack end. This does not qualify the
navigation controller. The corrected fixture freezes height, roll and pitch
while allowing Nav2 yaw; scripted controls retain their explicit orientation.
A physical Unity regression commands angular/linear velocity through this exact
fixture configuration and requires measured turning without height/tilt drift.
Raw samples now include robot yaw. Candidate8's superseded clean build was
stopped before qualification after this defect was identified. The next full
matrix uses a new committed-source clone with both fixture repairs.

## Moving-obstacle laser clearing

The corrected-turning pilot still failed both rack-end deadlines: all pedestrians
finished, sensor streams stayed fresh and no contacts occurred, but Nav2's path
grew into a long detour. These 45-second failures remain preserved. No longer
deadline is substituted.

A separate installed-Humble-costmap regression identified a concrete sensor defect:
legacy empty laser rays are zero, so laser projection drops them and they cannot
clear a departed person's obstacle mark. Merely enabling infinity on a marking
source creates a 360-cell obstacle ring near the 3.5 m limit. Shortening marking
to 3.49 m avoids that ring but loses a real finite hit at 3.495 m.

The candidate repair reports a no-hit beam as positive infinity; a physical hit
below range_min stays invalid zero. `-laser-no-return LegacyZero` retains the
old behavior for controlled ablation; `PositiveInfinity` is the new default.
Kuri's local/global costmaps each use two observations of the same scan: finite
hits mark obstacles with `inf_is_valid: false`; a clearing-only source accepts
positive infinity. Both retain the full 3.5 m horizon. This clears departed
obstacles without inventing a max-range ring or discarding far finite returns.

Run `scripts/check_laser_clearing.sh NEW_DIRECTORY` on robovision for all five
negative/proposed configurations using the installed controller/costmap plugin.
It marks an actual scan endpoint, removes it, inspects the published grid,
checks a 3.495 m finite endpoint, and requires clean lifecycle/process exit.
Unity additionally tests an actual disappearing physical cube and a too-close
hit. Warehouse schema2 records the actual laser profile; schema1/LegacyZero
cannot qualify as the repaired full matrix. `SEAN_LASER_NO_RETURN` selects the
explicit runner profile. Pedestrian forces, contacts, speed, layouts and the
45-second deadline remain unchanged.

The relevant implementation is documented in the upstream
[Humble obstacle layer](https://github.com/ros-navigation/navigation2/blob/humble/nav2_costmap_2d/plugins/obstacle_layer.cpp)
and [laser projection](https://github.com/ros-perception/laser_geometry/blob/ros2/src/laser_geometry.cpp).
The direct plugin regression establishes the clearing defect; a new live pilot
must establish whether this repair resolves these navigation detours.

The final Nav2 checker also counts the laser values actually received over ROS.
Repaired-profile qualification requires observed positive-infinity free rays
and no NaN, negative-infinity or unexpected finite ranges. The cached candidate10
corner pilot had already loaded the earlier checker when this extra telemetry
was added: both actions completed (36.44/34.56 simulation seconds), with four
pedestrian completions, fresh streams and zero contacts. Its original criteria
are retained separately in `pre-wire-summary.json`; it is not counted as final
wire-telemetry qualification. The full prospective matrix uses the frozen new
checker from the start.

# Pedestrian response to Kuri — October 28, 2026

The bounded open-floor Kuri response check passes: 60 checks completed
within the unchanged 18-simulation-second deadline, with zero physical contact
callbacks and zero negative horizontal body-clearance samples. This comprises
36 development cases, twelve cases on a fresh seed, and twelve repeats at a
larger simulation step. Ten checks are no-robot controls; fifty contain a robot.
These are repeated controlled checks, not sixty independent random trials.

The accepted profile combines ColliderV1 forces and VelocityBodyV1 contacts.
The same player also ran the Legacy-force comparison with matched contacts,
the normal three-stage Warehouse navigation smoke check, and clean shutdown audits. All 42 Unity tests, 26 Python
harness tests, and 175 final player payload checksums passed. The model is an
engineered response for this fixture, not evidence of human behavioral realism
or general pedestrian collision freedom.

## Sources and build provenance

- Unity: `aeaa7d247bc99fab12eacc95b22b3ad230d8f207`, `feature/unity-2022-upgrade`.
  Runtime/contact code is `21c28f84ca17c2a333542af486254d4975189dc7`;
  the latest commit changes documentation only. Robot-force model: `c6afbb9515bed723d4938ef1e6646edb5eb175d4`; later commits
  repair diagnostic guards/pacing and add the independent VelocityBodyV1
  contact model plus an animated-wall regression.
- ROS: `d5dd5eecd36c0d4b61a5edbceeba49afdcb2b91c`, `feature/ros2-port`; unchanged in this milestone.
- Coordination: the commit containing this report on `feature/ros2-environment`.
  Exact source/tooling hashes and executed scripts are retained with evidence.
- Unity 2022.3.62f3 on robovision, ROS 2 Humble / Ubuntu 22.04; the existing image
  `localhost/sean3-humble:dev`, ID
  `1f928d87cafe30ae9feb382a107a1e559d35f19ddc448a2f21fb0b42f59cb8da`.
- Installed endpoint SHA-256 matched its source:
  `953d09df83e60db848637d4defde961ea1f9e2f343d2d84a5b4a8b864162a9b5`.

Final player: `/scratch/tchauhan/sean3/builds/pedestrian-candidate10-20261027/sean.x86_64`.
This was an incremental build in the existing cached checkout, with build-time
HEAD `99110a72e87d18a26961d832a2d7b47780cb4799` plus subsequently committed
source. Full source snapshots, tracked patch, manifest, editor/package hashes,
submodule status, build logs, and payload inventory are preserved. It is not a
new clean-source import or an immutable-environment rebuild. Original Rocketbox
metadata and UserSettings were preserved. Earlier clean-source and rendered
sensor results remain specific to their earlier source pins.

Work began October 27; the final report uses the October 28 local date. Evidence
retains its initial `20261027-` labels; manifests/XML retain UTC timestamps.

## What changed

The source mechanisms described in the supplied `SEAN_PEDESTRIAN_NOTE.md` were
present in SEAN 3. Its numerical Jackal results are separate evidence from a
different project, speed patch, robot and metric. That project's accompanying
findings already report checks of its first avoidance patch; this work adapts
and tests the ideas for SEAN 3 rather than claiming a new discovery.

Our robot is Kuri. Its primary physical capsule has a 0.16 m radius; the old
fixed 0.2 m robot radius does not underestimate this Kuri body. The earlier
0.2262742 m audit is a conservative horizontal AABB-corner bound. The navigation
profile's 0.60 m inflated radius is not the physical contact geometry.

`SFAgent.robotResponse` now selects `ColliderV1` (default) or `Legacy`.
ColliderV1 uses physical colliders owned by the selected base-link rigidbody,
excluding triggers/independent child bodies. ClosestPoint queries occur at
shape-centre height; wheel projections use conservative radii. Unsupported
shape types fail explicitly rather than substituting a Jackal radius.

Robot radial repulsion is added after the legacy backward/lateral limiting,
so it can brake the pedestrian. A velocity clamp prevents robot repulsion from
driving it backward along the goal direction. The side term chooses the side
away from the robot, uses actual robot rigidbody velocity for approach detection,
and retains the legacy tangent bias in an exactly centred tie.

The explicit side term retains the slow-walking maximum 10 N, anticipates
within a 3 m surface gap, and fades in over B=0.16 m. Radial A=500 and B=0.16
remain; the extra robot-only force offset is zero. The nominal stationary
body-clearance balance is about 0.264 m, not a guaranteed comfort boundary.
ColliderV1 removes the random moving-robot repulsion reduction. The legacy
random draw remains so unrelated RNG consumption is preserved.

Desired/max pedestrian speed stays 0.6 m/s. Person/person and wall-force
parameters/limiting remain unchanged. This is not the outside-in project's
1.3 m/s patch, and no claim of human-data calibration is made. Legacy published
pedestrian proximity/fault counters are also unchanged; the diagnostic has its
own independent geometry and physical-contact measurements.

## Motion contacts and the larger-step failure

The first combined force diagnostic still used legacy contact physics. It
passed 36 development cases and twelve fresh cases at 0.02 s, but its 0.04 s
repeat passed only the two no-robot controls: ten robot-present cases missed
the deadline. All remained contact-free. Crucially, even without a robot the
walking time increased from 12.44 to 16.52 s although the desired speed stayed
0.6 m/s. That failed larger-step result remains preserved under candidate8.

An eight-case, same-player no-robot ablation at seed12346 then isolated contact
physics: original material took 12.44 s at 0.02 and 16.52 s at 0.04, while the
existing VelocityBodyV1 material took 9.96 s at both steps, in both mirrored
controls. This meets the predeclared 0.2 s cross-step timing check. No force,
desired-speed, deadline or contact threshold was changed for this ablation.

`IVI.SFAgent.contactModel` now independently selects `VelocityBodyV1` (default)
or `Legacy` before Start. The existing velocity-body material is applied to
colliders owned by the animated body's rigidbody. It has zero static/dynamic
friction, Minimum combination and zero restitution. It prevents floor contact
from fighting the root-motion actuator in this ideal driven-body model. It
changes realized walking pace without raising the desired-speed parameter.
It does not simulate foot traction or calibrated human contact dynamics.

A new production-startup regression loads a real animated avatar, verifies its
material, drives its actual root-motion actuator into a solid wall, observes a
physical wall callback, and checks that the capsule cannot penetrate/cross it.
The broader 42-test Unity suite also retains the existing material ownership,
floor/deadzone and collision tests. Unsupported shapes and slope behavior are
not qualified by this wall test.

For the original baseline select both Legacy forces and Legacy contacts. The
final matched comparison uses VelocityBodyV1 contacts for both force choices;
its no-robot trajectories must match. Future pedestrian-controller comparisons
must also hold the motion/contact model fixed. Do not attribute contact-model
pace improvements to the robot-force changes alone.

## Protocol and results

See [PEDESTRIAN_AVOIDANCE.md](PEDESTRIAN_AVOIDANCE.md) for commands and rules.
The opt-in fixture loads the Warehouse player, then uses a separate open floor
outside Warehouse geometry with real Kuri, production Rocketbox avatars,
animator, SFAgent, runtime NavMesh planning, root motion and physics. It isolates
robot response from walls and robot planning. It does not qualify populated
Warehouse routes or substitute for the note's multi-person Jackal experiments.

Per seed: six parked-body cases (headings 0/180 degrees, lateral offsets
-0.35/0/+0.35 m), two constant-moving robot cases, two early-yielding robot
cases, and two absent-robot controls. Pedestrians start 3 m in front and aim
3 m behind; moving/yielding Kuri starts 1 m behind and moves at 0.3 m/s, with
yielding latched at 2 m centre separation. The avatar is selected reproducibly
from the production template and its identity is logged. No placement is replaced.

Every case requires goal distance at most the legacy 1 m threshold by 18
simulation seconds, zero physical callbacks, no negative clearance, finite
samples and bounded sampling gaps. The independent horizontal clearance metric
uses the actual pedestrian capsule and Kuri capsule/wheel projections. Physics
contact callbacks are separate: contact offsets can produce callbacks with a
small positive measured gap. Zero overlap alone is insufficient.

| Mode | Legacy forces passed | ColliderV1 passed | Physical callbacks legacy / new | Min clearance m legacy / new | Max lateral deviation m legacy / new |
| --- | ---: | ---: | ---: | ---: | ---: |
| parked | 18/18 | 18/18 | 0 / 0 | 0.473 / 0.557 | 2.324 / 1.253 |
| moving | 6/6 | 6/6 | 0 / 0 | 0.086 / 0.380 | 2.337 / 1.100 |
| yielding | 6/6 | 6/6 | 0 / 0 | 0.264 / 0.535 | 2.295 / 0.985 |
| absent | 6/6 | 6/6 | 0 / 0 | 29.312 / 29.312 | 0.048 / 0.048 |

The table uses matched VelocityBodyV1 contacts and development seeds 7, 42 and
12345. It isolates force-model effects after correcting the motion-contact
physics; it is not the untouched historical Legacy baseline. Path, lateral
deviation and time include actual animated/physical movement; logged
`personVelocity` is the SFAgent model state, while `robotVelocity` is rigidbody
velocity. Desired speed is not a calibration of every avatar's root-motion speed.

| Final stage | Passed / attempted | Min body clearance m, robot present | Longest completion s |
| --- | ---: | ---: | ---: |
| run | 36 / 36 | 0.380 | 13.38 |
| heldout | 12 / 12 | 0.384 | 13.38 |
| heldout-step04 | 12 / 12 | 0.379 | 13.36 |

With corrected contact physics, Legacy forces also passed all 36 matched cases.
This simple matrix therefore does not demonstrate a contact-rate benefit from
the force changes alone. It did measure larger minimum clearances and smaller
maximum lateral deviations for ColliderV1 in these cases, as tabulated above.
The contact-material ablation identifies a separate motion defect; the force
changes have mechanism regressions and bounded live qualification, not a
demonstrated general performance advantage.

Seed12345 was initially withheld and exposed a previous version's liveness
failure. It then joined development explicitly. Seed12347 was selected before
the final model's new checks and supplied the fresh independent cases. Its
0.04 s repeat tests sensitivity; it is not an additional independent seed.
Model settings and all acceptance thresholds stayed fixed through these checks.

The six no-robot trajectories in the matched comparison differed by at most
0.000000 m, with maximum sample-count
difference 0. This comparison gates at
0.005 m and one sample. It helps expose changes unrelated to robot response;
it does not establish bit-identical simulation across machines.

Frame/physics steps are explicitly locked to 0.02 s, or 0.04 s in the repeat.
Wall pacing is capped to one simulated second per wall second to avoid
unnecessary telemetry overload. The larger-step initialization check accounts
for the moving robot's first physics step while the avatar starts. The frame
stepping controls the diagnostic; normal scenarios retain their existing
Update/Time.deltaTime integration. General frame-rate independence is unproven.

## Preserved rejected attempts

- Initial baseline: robot failed to remain at the requested fixture pose;
  accelerated streaming overflowed queues. Stopped and excluded.
- `baseline2`: valid original-force run; 17/24 strict passes, two physical
  callbacks in one moving-robot case, clean transport. Kept separately from the
  final same-player, three-seed Legacy comparison.
- Candidates1–5: partial development runs rejected for oversized detours or
  centred-approach deadline failures. Their source/build/trajectory evidence is
  retained. Changes are enumerated in the model-selection protocol.
- Candidate6: 24/24 development cases passed, but initial held-out seed12345
  passed only 10/12; both centred approaches ended 1.212 m from the goal at the
  unchanged deadline. No contacts. Later checks were gated off. This failed
  independent check is not relabelled as validation.
- Candidate7: all 36 expanded behavioral cases passed, but its full run failed
  the log audit with 6,083 telemetry queue-overflow warnings. It remains
  unaccepted. Revision8 repairs diagnostic initialization checks and pacing;
  production robot-force computation was unchanged. Later contact-model
  startup deliberately changes motion physics, as described above.
- Candidate8: all 48 checks at 0.02 s passed, but the larger-step check failed
  ten of twelve deadlines. Subsequent checks were gated off; this is not an
  accepted larger-step result. Candidate9's eight contact-material controls
  isolated the timing effect before changing production contact physics.
- Candidate10: only this player's complete combined-profile runs supply final acceptance above.
  No diagnostics were suppressed, no failed output directory reused, and no
  threshold or speed was relaxed.

## Evidence and limits

Authoritative root `/scratch/tchauhan/sean3/`:

- `validation/pedestrian-avoidance/20261027-candidate10/`: `run/`, `heldout/`,
  `heldout-step04/`, `legacy/`, `navigation/`, return codes, complete logs,
  summaries/raw trajectories, source snapshots, control comparison and audits.
- Candidate10 `unity-tests.xml`, `payload-verification.txt`,
  `force-source-verification.txt`, `protocol-at-contact-model-selection.md`, and executed
  `final-checks.sh`; parent `contact-control-harness.log` contains 26 passing tests.
- `builds/pedestrian-candidate10-20261027/`: player and complete cached-build
  provenance. Earlier players/attempts remain in their original directories.

Local ignored copies: `results/pedestrian-avoidance-20261027/evidence/` and
`build-provenance/`. `source-hashes.json` / `source-verification.txt` record the
25-file local/remote comparison. No generated recordings or assets are committed.

Scope is a single walking person and the configured Kuri body on an open floor.
The independent metric bounds physical projections, not every visible body/arm
or camera-boom surface. It cannot prove collision freedom between samples or
with unsupported geometry. Tests do not establish human realism, population
behavior, wall/corner performance, comfort calibration, cross-machine
repeatability, arbitrary network recovery, a new rendered-sensor qualification,
or participant recording/replay.

The next milestone is multi-person, mirrored Warehouse encounters with explicit
parked, yielding and oblivious-robot controls. The note's later findings show why
this matters: stronger pedestrian avoidance can make robot-controller benchmarks
too easy. Measure both safety and separation between controller conditions
before using this model to judge robot navigation. This work does not depend on
Michal's or Howard's participant-interface prototypes; ORCA remains deferred.

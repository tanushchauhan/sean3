# Pedestrian response to Kuri

This opt-in diagnostic measures the production Kuri body and animated SFAgent
on an open floor outside the Warehouse geometry, within the Warehouse player.
It isolates robot response from wall geometry and robot planning. It does not
reproduce the outside-in project's multi-person Jackal benchmark.

Use the paired source versions in the [dated result](../results/2026-10-28-pedestrian-avoidance.md).
The final combined-profile qualification uses the revision10 player and keeps every earlier
attempt separate. See the result for outcomes, source/build provenance and limits.

## Fixed model and case matrix

`IVI.SFAgent.robotResponse` selects `ColliderV1` (default) or `Legacy` before
Start. ColliderV1 uses the selected base-link rigidbody's enabled physical
colliders, excluding triggers and independently owned child bodies. Supported
primitive/convex shapes use ClosestPoint at their centre height; wheels use
conservative radius projections. Unsupported shapes fail explicitly. There is
no hard-coded Jackal-radius fallback. Qualification is limited to Kuri.

Robot radial force is added after the legacy backward/lateral limits. The next
velocity may brake to zero along the goal direction without being driven
backward by robot repulsion. The explicit side term points away from the robot
and uses actual robot rigidbody relative velocity; an exactly centred tie keeps
the legacy tangent bias. Person/person and wall-force parameters/limiting stay
unchanged. Desired/max pedestrian speed stays 0.6 m/s.

| Parameter | ColliderV1 |
| --- | --- |
| Radial A / B | 500 N / 0.16 m |
| Robot-only extra repulsion offset | 0 m |
| Explicit side-term maximum | A / (10 * LATERAL_DAMPENING) = 10 N, before front-angle factor |
| Robot anticipation surface gap | 3 m, fading from zero to full over B = 0.16 m at entry |
| Moving-robot random repulsion reduction | Removed; the legacy RNG draw is retained |
| Original pedestrian mass / goal relaxation T | 80 / 0.5 s |

For a head-on stationary force balance, body clearance is approximately
`offset + B*ln(A/(mass*desiredSpeed/T))`, or 0.264 m. This is an engineered
setting, not a hard comfort boundary or a calibration against human data.
Root-motion speed need not equal the model's desired speed.

Each seed produces twelve cases:

- Parked Kuri: headings 0/180 degrees, pedestrian lateral offsets -0.35/0/+0.35 m
  (six cases).
- Constant-moving Kuri, early-yielding Kuri, and no-robot control: offsets
  -0.35/+0.35 m (two cases each).

People start 3 m in front and aim 3 m behind the parked robot position. Moving
and yielding robots start 1 m behind it and move at 0.3 m/s toward the person.
Yielding latches permanently at 2 m centre separation. The no-robot control
moves Kuri 30 m sideways. The diagnostic selects an avatar reproducibly from
the production template, uses its real animator/root motion/physics, and records
its identity. No placement is silently replaced.

The initial development set was seeds7 and42. Candidate6 failed two centred
cases on the first withheld seed12345, which then explicitly joined development.
The force-only revision8 later passed 36 development and twelve seed12346 cases
at 0.02 s, but its 0.04 s check failed. Contact ablations used that already-seen
seed12346. Final combined-profile development remains **7,42,12345** (36 cases),
with a newly reserved **12347** (12) and its 0.04 s repeat (12). Both model choices
were fixed before these final checks. The repeat is not another independent
seed. Legacy forces use the same final player and matching contact physics.

## Independent motion/contact profile

`IVI.SFAgent.contactModel` selects `VelocityBodyV1` (default) or `Legacy`
independently of robotResponse, before Start. VelocityBodyV1 applies the existing
zero-friction, Minimum-combine velocity-body material to the animated body's
owned physical colliders. This changes realized walking pace without raising
the desired-speed parameter. It is an ideal driven capsule, not a foot-traction
or calibrated human-contact model. The animated-wall regression verifies that
production startup applies it and root motion still blocks against a real wall.

The eight seed12346 no-robot ablations found original contacts took 12.44 s at
0.02 s and 16.52 s at 0.04 s. VelocityBodyV1 took 9.96 s at both, in both mirrored
controls. The 0.2 s cross-step timing gate was declared before reading them.
This identifies the contact-physics effect separately from robot avoidance.

For the untouched baseline select both Legacy forces and Legacy contacts. For
the matched force comparison use VelocityBodyV1 contacts on both force choices.
Record both settings. Future pedestrian-controller comparisons must share the
same motion/contact model too.

Final combined-profile development remains seeds7,42,12345. Fresh seed12347 was
reserved before the contact model was integrated; it and its 0.04 s repeat
supply the final independent/sensitivity checks. Earlier seed12346 data remains
preserved as the force-only and contact-ablation diagnostic, not final holdout
acceptance. Full combined-profile qualification still has 60 checks: 36+12+12.

## Measurements and acceptance

Every case must:

- Reach within the legacy 1 m goal threshold by 18 simulation seconds.
- Have zero physical person/robot CollisionEnter callbacks.
- Have no negative independently measured horizontal body clearance.
- Have finite samples and sample gaps no larger than 1.5 configured steps.
- Pass the requested pose/model/seed/step setup checks.

The independent clearance metric uses the pedestrian's actual capsule radius
and analytic horizontal Kuri capsule/wheel projections. Wheel discs are
conservative bounds. Unsupported robot shapes stop the fixture rather than
being omitted. Contact offsets may produce a physics callback with positive
geometric clearance; zero overlap alone is not sufficient. Published legacy
pedestrian proximity/fault counters are unchanged and are not this metric.

Raw per-frame records retain person/robot positions, model person velocity,
robot rigidbody velocity, clearance and goal distance. Summaries add path length,
maximum lateral deviation, completion time, contact count and sample gaps.
The deadline catches failure to complete; this fixture does not separately
certify every brief stop or prove freedom from deadlock in broader scenarios.
No-robot controls must complete, and matched trajectories must agree within
0.005 m with at most one sample-count difference.

Frame and physics steps are locked to 0.02 s, with a 0.04 s repeat. Wall pacing
is capped at `round(1/step)` fps (50/25), preventing unnecessary accelerated
telemetry load. This affects only the opt-in diagnostic. Normal scenes retain
their existing Update/Time.deltaTime force integration; general frame-rate
independence is not established.

A moving robot advances one fixed step while its avatar initializes. Revision8
checks that predicted advance within 0.002 m. The independent analyzer accounts
for that step and the first recorded step, and rejects a wrong pose at 0.04 s.
This guard does not move the robot or change physical trajectories.

Each runner must also pass the full-log connection/process audit, with normal
exits, announced closure, no queue overflow and no forced player kill. A
behaviorally successful run with a failed log audit remains unaccepted.

## Run on robovision

Serialize these runs and any Unity editor/ROS overlay jobs. From
`/scratch/tchauhan/sean3/sean3`, using a new output directory:

```sh
mkdir /scratch/tchauhan/sean3/validation/pedestrian-avoidance/NEW
SEAN_PEDESTRIAN_MODEL=ColliderV1 SEAN_PEDESTRIAN_SEEDS=7,42,12345 \
SEAN_PEDESTRIAN_CONTACT=VelocityBodyV1 \
SEAN_PEDESTRIAN_STEP=0.02 SEAN_TCP_PORT=10331 \
  bash scripts/check_pedestrian_avoidance.sh \
  /scratch/tchauhan/sean3/builds/pedestrian-candidate10-20261027/sean.x86_64 \
  /scratch/tchauhan/sean3/ros_ws /scratch/tchauhan/sean3/social_sim_ros \
  /scratch/tchauhan/sean3/validation/pedestrian-avoidance/NEW/development
```

Repeat with seed12347, then that seed at 0.04 s, then Legacy forces with the same
VelocityBodyV1 contacts and the three development seeds. Every run needs a fresh directory. Defaults are
`ColliderV1`, `VelocityBodyV1` contacts, all four modes, seeds 7,42, step 0.02,
and the existing `localhost/sean3-humble:dev` image. The runner checks actual recorded parameters
against requested settings, bounds wall runtime, saves partial evidence on
failure, and uses the existing ordered player/endpoint cleanup.

`SEAN_PEDESTRIAN_CONTACT=Legacy` selects original body contacts.
`SEAN_PEDESTRIAN_MODES=absent` requests only no-robot controls; the expected
matrix is explicit and cannot count as a full run. The report records actual
modes/contact profile and the runner checks them against the request.

Run regressions on robovision:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the full `SEAN.Editor.Tests` Unity suite with the pinned editor, and inspect
its XML as well as process exit. The final sequence also checks ordinary
three-stage Warehouse navigation without the diagnostic flag and verifies the
player's complete payload checksum inventory.

## Development history and limits

All attempts remain under `validation/pedestrian-avoidance/`; the frozen model
selection/contact-ablation/guard-repair records remain with their original
attempts. The dated result retains outcomes and exact source/build provenance.

| Attempt | Disposition |
| --- | --- |
| Initial baseline | Invalid robot pose and queue overflow; stopped/excluded. |
| Baseline2 | Valid original Legacy forces/contacts: 17/24 strict passes, two physics callbacks in one case, clean transport. |
| Candidates 1-5 | Partial force-model experiments rejected for wide or slow centred passes under the unchanged deadline. |
| Candidate6 | Development24/24; first held-out12345 only10/12. Kept as a failed independent check. |
| Candidate7 | All36 behavioral cases passed, but 6,083 queue warnings failed the full audit. |
| Revision8 | Guard/pacing repaired. All48 cases at0.02 passed; larger-step only2/12 (no-robot controls), with no contacts. Later stages gated off. |
| Revision9 | Eight explicit no-robot material/step ablations isolated the walking-pace issue:12.44/16.52s original versus9.96/9.96s VelocityBodyV1. |
| Revision10 | Separately selectable production contacts, animated-wall regression, full combined-profile qualification and aligned Legacy-force comparison. See the dated result. |

Do not infer human realism, population safety, wall/corner navigation
performance, camera-boom clearance, cross-machine determinism, or fair
robot-controller benchmark difficulty. The wall regression validates physical
blocking of the driven capsule; it does not validate a wall-navigation strategy.
The next evaluation must use multi-person mirrored Warehouse encounters and
parked, yielding and oblivious-robot controls. Stronger pedestrian avoidance can
make a controller comparison too easy. Neither participant-interface prototype
is required for this work; ORCA remains deferred.

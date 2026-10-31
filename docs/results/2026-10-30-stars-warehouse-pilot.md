# Checkpoint-backed STARS Warehouse pilot

The seed-0 deterministic forecaster runs through the real Warehouse player and
the shared physical pedestrian actuator, but **does not qualify as a
goal-directed pedestrian controller under stationary-history initialization**.
All four STARS encounters fail the original acceptance checks: no pedestrian
reaches its assigned goal, and neither Nav2 robot route completes. There are
zero recorded physical contacts and no worker/controller faults. These are
behavioral failures, not transport passes being treated as successful navigation.

## Matched protocol

The pilot uses the same newly built Linux player for all three controllers,
seed 7, aisle layout, both mirrors, and parked/Nav2 robot modes: four episodes
per controller, with four pedestrians each. All use `VelocityTargetsV1` physical
actuation. Fixed placements, goals, 45-second deadlines, goal tolerances, contact
checks and fresh-sensor/Nav2 requirements are unchanged. SF is goal-directed;
ORCA uses goal-derived preferred velocities; this STARS checkpoint has no goal,
robot or map conditioning. Decision rates also differ: SF uses the physical
cadence, ORCA 0.1 seconds, and STARS its native 0.4 seconds. This is a diagnostic
pilot, not an equal-capacity or statistical policy benchmark.

STARS uses eight actual observed position samples. The first seven decisions
hold people stationary, giving a 2.8-second history span before inference. Each
new episode clears history. There is no SF bootstrap, inserted predicted state,
synthetic moving history, clipping, fallback, or deadline increase. The first
forecast segment alone is converted to velocity. See the
[reproduction protocol](../protocols/stars-warehouse-validation.md).

## Comparison

| Pedestrian controller | Episodes passing | Pedestrian routes completed | Nav2 robot routes completed | All recorded contacts |
| --- | ---: | ---: | ---: | ---: |
| Social Forces | 4/4 | 16/16 | 2/2 | 0 |
| ORCA | 3/4 | 16/16 | 1/2 | 0 |
| STARS, stationary history | 0/4 | 0/16 | 0/2 | 0 |

SF's parked episodes finish in approximately 13.42 seconds; ORCA's finish in
12.58 seconds. SF's Nav2 goal errors are approximately 0.329 and 0.338 metres.
ORCA's first Nav2 route succeeds at approximately 0.349 metres error; its second
is canceled at the deadline with approximately 1.778 metres error. Sensors
remain fresh and planning succeeds in every controller's Nav2 cases. No joint
controller faults occur.

The ORCA outcome retains an unresolved robot-navigation failure. Although its
3/4 aggregate matches the earlier pilot, this case has status 5 (canceled) and
different terminal evidence from the earlier status-6 abort; it is not reported
as reproduction or resolution of that earlier failure. Every failed attempt is
retained, with no reruns selected to improve the result.

## STARS observations

- All 16 pedestrian routes miss their goals. Every person travels only
  0.0622–0.0716 metres of total planar path during a 45-second episode; assigned
  routes initially span approximately 8.5 metres.
- Maximum target speed is approximately 0.01876 m/s, far below the scene's
  0.6 m/s limit. Maximum position-derived achieved/target velocity error is
  approximately 0.0000262 m/s. The physical actuator follows the small forecasts.
- Both parked cases remain contact-free. Both Nav2 cases also remain
  contact-free, with minimum measured robot/person surface gaps approximately
  0.474 and 0.487 metres.
- Nav2 plans succeed and sensor data remain fresh, but the action results are
  canceled at the fixture deadline (status 5). Recorded final robot goal errors
  are approximately 1.579 and 1.719 metres. These are not successful actions or
  the status-6 abort observed in the earlier ORCA pilot.
- All history-ready flags agree with sequence 7 and later. No controller faults
  occur. Per-episode decision-exchange medians are approximately 14.4–16.0 ms;
  the maximum is 39.7 ms on CPU. These are development diagnostics, not a
  throughput benchmark.
- The worker exits with status 0 without forced termination. Lifecycle and
  simulation-log audits pass. The failed behavior is preserved in the raw
  reports, navigation feedback, costmaps and logs.

## Interpretation and next model work

The evidence supports successful model loading, actual-state feedback and
physical actuation. It does not support destination-conditioned locomotion.
The network receives stationary initial histories and no goal/intent input;
its near-stationary continuation is consistent with that input. This pilot
does not isolate initialization effects from the checkpoint's learned motion
distribution, nor establish how it behaves with previously observed moving
pedestrians. It also does not establish the complete cause of Nav2's deadline
failures around the nearly stationary population.

Before advertising STARS in the ordinary launcher, establish an explicit
initialization/intent contract: whether the model is meant to continue already
observed motion, how a simulated person starts moving, and how assigned goals
condition its predictions. A separately declared actual-motion bootstrap would
be a different experimental protocol; a goal-conditioned model would require
matching model code/weights and validation. Neither should be silently inserted
to make these failed episodes pass.

## Source and evidence

The player is built from Unity revision
`636f8be2662098a2e785500d46d5957e6a7cf4c2`; the runner/analyzer revision is
`b754f14e600a3d0142c5bdaf3113469dce8fc61a`; ROS is
`234262d28f7f426020fa198aa3f0dedefb04e117`. All 177 built-player payload
checksums verify. Pre-build validation passes 85 Unity project tests and 75
Python tests, with the real checkpoint enabled and zero skips.

Checkpoint SHA-256 is
`382d2c00d818f43dda8d3406d857d824c439bba2918d7872dd576b56b8abaaa3`.
Its matching extension is `d72eb2295c3336f0674932796cf41b60636cde3e`, with
upstream STARS `13d840c5c0677ff52e928eea1679ba5ce1f19c14`. The checkpoint's
dirty-training-source provenance remains provisional. No weights or external
source are redistributed.

Raw artifacts are retained remotely at
`/scratch/tchauhan/sean3/validation/stars-warehouse-20261030/` and local copies
under `.sean3/evidence/stars-warehouse-20261030/`. The build is retained at
`builds/stars-636f8be-20261030/` on robovision. Preexisting Rocketbox metadata and
UserSettings changes were preserved and captured in the build provenance; this
is not represented as a pristine checkout build.

The [pilot manifest](2026-10-30-stars-warehouse-manifest.json) records per-case
outcomes, source/build identities, raw artifact hashes and test results. The
earlier [checkpoint integration report](2026-10-30-stars-checkpoint.md) records
the pinned model environment and standalone worker checks.

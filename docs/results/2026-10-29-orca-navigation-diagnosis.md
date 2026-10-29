# ORCA / Nav2 abort investigation

The original failed encounter is an actual Nav2 collision-check/recovery abort,
not a missing global plan, stale-sensor rejection, worker exception or recorded
physical collision. One unchanged development repeat passed. The original
failure remains part of the results; no controller fix or deterministic
reproduction is claimed.

## Original evidence

Seed 7, aisle, mirror +1, Nav2, episode 3, with the committed `aa7bf26` player,
`VelocityTargetsV1`, 0.02-second physics and unchanged 45-second deadline:

- Global planning succeeded (status 4), sensors remained fresh, and no physical
  contacts or ORCA faults were recorded. Navigation aborted (status 6).
- The action's log segment contains 146 collision-ahead warnings, 14 controller
  patience failures, three failed backup recoveries, three failed spins and the
  final `Goal failed`. Feedback reports up to 22 recoveries.
- The robot remains within 1 mm of its final pose from 18.42 seconds through
  the 45-second deadline, a 26.58-second terminal interval. This is distinct
  from the original analyzer's 26.94-second pause using a 0.1 m anchor.
- At the final pose, the nearest pedestrian has 0.3663 m physical-body
  clearance. Its centre is approximately 0.7263 m from the robot centre.
  Nav2's configured 0.60 m navigation radius plus the pedestrian's 0.20 m
  capsule radius gives a **-0.0737 m** circular-envelope margin.

This geometry is consistent with Nav2 refusing to move or spin even without
physical contact. ORCA uses a conservative physical robot bound of 0.2263 m;
Nav2 deliberately uses a larger clearance envelope. These are different
documented assumptions. A stopped pedestrian can therefore be physically clear
while still obstructing a Nav2 maneuver.

The original run did not capture the costmap, so the exact marked/inflated cell
responsible, contribution of static geometry, and sequence that led to the
terminal configuration cannot be established from the surviving data. The
geometry calculation is an approximation, not a reconstruction of Nav2's
polygon collision checker or proof of the whole causal chain.

## Unchanged diagnostic repeat

The same accepted player, component revisions, seed, placements, controller and
actuator settings, and gates were repeated once. The only harness additions
preserve time/pose in feedback and the last received local costmap before
cleanup. They do not change navigation commands or pass/fail thresholds.

All four encounters passed with zero recorded contacts. Nav2 mirrors -1/+1
finished in 43.22 / 40.38 simulation seconds, with goal errors 0.3331 / 0.3349 m.
Their action logs still contain 49 / 40 collision-ahead warnings and 4 / 3
controller patience failures, but recovery eventually succeeds. Their final
costmaps contain no lethal cell centre inside the 0.60 m navigation circle;
the nearest lethal cell centres are approximately 2.273 m away.

The repeat did **not** reproduce the failed terminal configuration and cannot
verify the original costmap explanation. Nav2 operates asynchronously, and a
fixed placement seed does not establish deterministic timing or replay. Do not
replace the original 3/4 result with this later 4/4 result or pool the two as a
prespecified evaluation campaign.

## Changes and reproduction

`tests/warehouse_navigation_check.py` now preserves `nav2-costmap-INDEX.json`
with map stamp, reception age, origin, resolution, data and robot position, plus
timed action feedback. `tests/diagnose_warehouse_navigation.py` segments action
logs, reports recovery events and terminal geometry, and hashes its inputs.
It changes no acceptance decisions.

```sh
python3 tests/diagnose_warehouse_navigation.py RESULTS \
  --navigation-radius .6 --output RESULTS/diagnosis.json
```

Original raw evidence is under
`/scratch/tchauhan/sean3/validation/velocity-actuator-final-20261029/orca/`;
repeat evidence is under
`/scratch/tchauhan/sean3/validation/orca-diagnosis-20261029/`.
Local copies are in the corresponding ignored `.sean3/evidence/` directories.
The [diagnostic manifest](2026-10-29-worker-and-mlagents-manifest.json) records
the input hashes and both diagnostic summaries.

No navigation-radius reduction, longer patience/deadline, pedestrian-removal
rule or ORCA tuning was applied. Choosing a different navigation/pedestrian
clearance relationship would require an explicit experimental condition and
fresh evaluation, not relabeling this failure as a pass.

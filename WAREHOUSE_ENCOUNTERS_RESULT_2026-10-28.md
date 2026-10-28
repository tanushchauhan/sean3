# Multi-person Warehouse result — October 28, 2026

The clean-source candidate passes **80 controlled four-person encounter cases**
(320 person routes), including sixteen actual Nav2 actions, with zero recorded
robot/person, person/person, person/environment or robot/environment contacts.
All cases complete within the unchanged 45-simulation-second bound. This supplies
an autonomous populated fixture without Michal's prototype or Howard's extensions.

**Sustained normal navigation remains unqualified.** The prospective follow-up
failed, and benchmark difficulty does not meet the declared clearance headroom
criterion in every layout. This candidate is a bounded development baseline,
not a generally reliable simulator release or a validated controller benchmark.

## Sources and build

- Unity: `3033ba1fb63a01698d543c16f6b21a0e210db85e`.
- ROS: `cceff5bd54ce52787fa47595fdff8b9c9775527f`.
- Executed encounter tooling: `1e6cad48298aa6dfbecae7659ccd389e118e90b9`.
- Rocketbox: `8aa27b9765284e01be88b1eed18ece55af5b7c5c`, unchanged in this milestone.
- Unity 2022.3.62f3, Linux x86_64, robovision; ROS 2 Humble in the existing
  `localhost/sean3-humble:dev` image, ID
  `1f928d87cafe30ae9feb382a107a1e559d35f19ddc448a2f21fb0b42f59cb8da`.

The player was built from a new committed-source clone, with a clean checkout,
exact submodules and no Library before import. Dirty origin metadata was recorded
without copying it. The build ran 18:31:54–18:38:25 UTC October 28, exited zero,
and retained its manifest, full import/build log, source inventories and payload
hashes. All 175 payload files verified after the runs. The recorded environment
was reused; this is not an immutable-environment or bit-identical-build claim.
Forty-five selected component/tooling files matched their frozen hashes before
qualification. Later diagnostic builds do not supply the 80-case result.

## Completed checks

| Stage | Seeds | Step s | Cases passed | Nav2 successes | Maximum case s |
| --- | --- | ---: | ---: | ---: | ---: |
| Development | 7, 42 | 0.02 | 40/40 | 8/8 | 38.18 |
| Fresh held-out seed | 12349 | 0.02 | 20/20 | 4/4 | 36.88 |
| Larger-step repeat | 12349 | 0.04 | 20/20 | 4/4 | 40.96 |

Every stage covers both aisle and rack-end layouts, both lateral mirrors, and
absent, parked, yielding, oblivious and Nav2 robot conditions. Eleven avatar
identities occur across these deterministic selections. These are controlled
repeats, not 80 independent random-population trials. Every accepted stage also
passes raw pose/height, exact coverage, independent clearance, completion,
sampling, stream freshness, transport and clean-exit checks.

| Additional check | Result |
| --- | --- |
| Clean-source build | Passed |
| Unity EditMode | 45 passed, zero failures/skips |
| Python harness regressions | 53 passed |
| Installed Humble costmap negative/proposed controls | 5 passed, clean native exits |
| Ordinary startup / task reset / scene reload navigation | 3/3 passed |
| Player payload verification after testing | 175/175 matched |
| Sustained normal navigation | Failed; see below |

The smallest sampled robot/body clearance is **0.289462 m**; the smallest
person/person clearance is **0.407180 m**. The longest individual person completion
is 31.24 simulation seconds. Contact callbacks and sampled geometric clearance
are independent checks, with their own stated limitations.

The Nav2 checker received 3,446 scans containing 751,727 positive-infinity free
rays and 488,833 finite hits; no NaN, negative infinity or invalid finite sample
was observed. All sixteen actions returned SUCCEEDED with fresh required inputs.

## Interpretation of controller comparisons

All five conditions have sixteen passing cases and zero robot/person contacts,
including the oblivious robot. Therefore this fixture demonstrates no contact-rate
advantage for yielding or Nav2. Yielding improves sampled clearance relative to
oblivious by 1.028–1.090 m at the rack end, with about 2.32–5.26 seconds of added
robot delay. In the aisle, the benefit is 0.057–0.099 m, below the declared 0.10 m
headroom threshold, while adding about eight seconds of delay. The all-pairs
headroom result is false at all three stages. The threshold was not reduced.

These results support layout-dependent clearance/delay comparisons. They do not
establish general controller superiority, safety benefit or benchmark difficulty.
A more discriminating encounter design needs its own prospective protocol and
fresh evaluation data; these outcomes must not be relabelled to satisfy it.

## Necessary repairs and rejected attempts

The fixture uses actual Warehouse racks, floor and baked NavMesh, production
animated SFAgents, the existing ColliderV1 forces and VelocityBodyV1 contacts,
0.6 m/s desired walking speed and a 0.3 m/s ideal Kuri velocity body. No force,
material, speed, deadline or acceptance threshold was retuned for these results.
See [the protocol](WAREHOUSE_ENCOUNTERS.md) for exact layouts and acceptance.

| Attempts | Outcome and treatment |
| --- | --- |
| 1–2 | Fixture authoring/namespace errors; no accepted live result. |
| 3 | Bootstrap destroyed the diagnostic owner; corrected persistence. |
| 4–5 | Proposed coordinates rejected by the actual NavMesh; mesh audited before walking. |
| 6 | Three of four no-robot controls missed the deadline because terminal arrivals blocked trailing people. Version3 orders terminal goals downstream; dense terminal queues remain unqualified. |
| 7 | Full development attempt rejected: Nav2 yaw was frozen and a duplicate report write blocked live input. Four corner goal failures and one freshness failure retained. |
| 8 | Superseded clean build completed but was not qualified after the yaw defect was identified. |
| 9 | Yaw/recording repaired; two corner actions still missed 45 seconds with fresh streams and no contacts. |
| 10 | Laser/costmap repair passed two corner actions; same-player LegacyZero ablation failed both. Tooling gained wire telemetry after the first driver loaded, so the earlier-criteria success is retained separately and is not final wire qualification. |
| 11 | Frozen clean-source 80-case result above; ordinary three-stage navigation passed; sustained follow-up failed. |
| 12 | Proposed snapshot publication gate failed to fix the sustained problem and was fully reverted. |
| 13 | Diagnostic-only queue topic labels and historical-stack comparisons; no production behavior fix accepted from this attempt. |

A real laser defect required a production repair: empty rays formerly used zero,
which laser projection discarded, leaving departed pedestrians marked in Nav2.
No-hit rays now use positive infinity; physical hits below range_min remain invalid
zero. Each Kuri costmap separates finite marking from infinity-enabled clearing,
retaining the full 3.5 m horizon. Unity tests exercise a disappearing physical
cube, a too-close hit and production defaults. The installed costmap controls
show that zeros retain old marks, naive infinity marking creates a 360-cell ring,
and shortening the horizon loses a real 3.495 m hit; the split-source profile
clears the old mark without either defect. See upstream
[Humble obstacle handling](https://github.com/ros-navigation/navigation2/blob/humble/nav2_costmap_2d/plugins/obstacle_layer.cpp)
and [laser projection](https://github.com/ros-perception/laser_geometry/blob/ros2/src/laser_geometry.cpp).
The paired live corner actions completed in 36.44/34.56 simulation seconds with
the repair; LegacyZero controls using the same player/profile missed 45 seconds.

## Sustained-navigation failure and next work

Candidate11's follow-up reported 14,754 outgoing queue warnings, stale streams
and a reset timeout. The proposed candidate12 publication gate still produced
15,206 warnings. Measurements showed snapshot headers were already unique;
the gate and its temporary test were reverted. No warning was suppressed.

Candidate13 added only topic names to the existing warning. Its modern-profile
long run had zero queue warnings: two goals completed, but the first failed the
unchanged 15-second confinement gate (16.6 seconds), and the third timed out.
Thus queue overflow is not a sufficient explanation of all failures.

With the old laser/profile, candidate13 also failed. The historical accepted
executable with that same old profile then timed out on the exact previously
accepted startup route (301.23 wall seconds, 13 recoveries, fresh sensors, no
contacts); its task route aborted after 239.80 seconds. This weakens attribution
to the new encounter/laser code. The actual historical acceptance was candidate17,
not the earlier failed candidate9 logs; both used the same retained player.
A further single-route control used the original accepted checker with that
executable/profile, isolating the added diagnostic subscriptions. It also timed
out: 301.24 wall seconds, twelve recoveries, 24.67 m final error, fresh sensors
and zero contacts. The historical player's 175 payload checksums verified unchanged.
The extra monitoring is therefore not a sufficient explanation either. The
historical successes remain valid observations, but these repeats demonstrate
that they did not establish dependable route completion.

No 300-second deadline, freshness/contact requirement or stall threshold was
relaxed. The original full qualification pipeline exited nonzero; the successful
population stages are reported separately. Longer seed42 was not run after that
pipeline failure. Diagnose repeated path/command behavior and timing under the
frozen original harness before accepting a sustained-navigation fix. Preserve
all outcomes; a later successful repeat cannot erase these failures.

## Evidence and limits

Remote root: `/scratch/tchauhan/sean3/validation/warehouse-encounters/`.
Candidate11 contains the authoritative `development/`, `heldout/`,
`heldout-step04/`, `navigation/`, `population-summary.json`, source verification,
unit/harness logs and payload verification. `laser-clearing-20261028/qualification/`
contains the five installed-plugin controls. All rejected candidates remain
alongside them. The clean player and complete build project remain at
`/scratch/tchauhan/sean3/builds/warehouse-clean-3033ba1-20261028/`.
A local ignored copy is retained under
`results/warehouse-encounters-20261028/evidence/`, with selected build provenance
under `build-provenance/`; generated evidence and player binaries are not committed.

This qualifies a finite four-person through-flow fixture with controlled stepping
and a planar ideal velocity body. It does not qualify dense terminal queues,
large crowds, human realism, wheel traction, arbitrary frame rates, cross-machine
repeatability, broad navigation reliability, rendered sensors at these pins,
participant control/recording/replay, ORCA, GDC reconstruction or STEPS alignment.
Legacy TrialInfo timer/goal fields do not reset per diagnostic case; authoritative
case metrics come from `encounters.json` and the case index. Kuri is the tested
robot; Jackal-specific geometry and the outside-in note's separate experiment
are not claimed as validated here.

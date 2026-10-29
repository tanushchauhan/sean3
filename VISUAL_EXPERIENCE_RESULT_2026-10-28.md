# Visual experience result: October 28, 2026

Step 3 checks that the current stack still behaves with pedestrians, renders
correctly and stays responsive with a visible window. It used the long-route
qualified stack: Unity `1fec526` (c01 player, not a clean-source build), ROS
`cceff5b`, image `localhost/sean3-humble:tf2-0.25.24` and overlay `ros_ws_tf2`.

**Summary.** The controlled encounter matrix and the measured sensor fixture
pass unchanged on the new stack. A visible Warehouse run without pedestrians
passes all three routes. Visible and headless runs with the 65-person `Random`
scenario render correctly and keep transport healthy, but Kuri's Nav2 profile
completes only 3 of 9 routes there and two contacts are recorded. Follow-up
work added on-screen view switching (C key or `-view`), per-contact logging, and
a Kuri Nav2 profile whose reported success stays within the 0.4 m gate; the
long-route campaign passes again with those changes (36 of 36 routes).

## 1. Encounter rerun (gate)

The unchanged 80-case protocol in [WAREHOUSE_ENCOUNTERS.md](WAREHOUSE_ENCOUNTERS.md),
with the same runner and analyzer, on the new player and image.

| Stage | Seeds | Step s | Cases passed | Nav2 successes | Maximum case s | Earlier maximum s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Development | 7, 42 | 0.02 | 40/40 | 8/8 | 38.08 | 38.18 |
| Held-out seed | 12349 | 0.02 | 20/20 | 4/4 | 41.08 | 36.88 |
| Larger step | 12349 | 0.04 | 20/20 | 4/4 | 41.00 | 40.96 |

Zero contacts of any kind. Smallest sampled robot/body clearance 0.290 m and
person/person clearance 0.407 m (earlier 0.289 and 0.407). Nav2 goal error 0.325
to 0.341 m. Every stage passed the analyzer, transport audit, script-log audit
and clean-exit checks, and all 175 player payload hashes verified afterwards.
The yielding headroom criterion remains unmet, as before.

Two held-out Nav2 cases ran about 4 s longer than on the old stack (40.16 and
41.08 s), leaving 3.9 s of margin to the 45 s deadline. The development and
larger-step stages match their earlier maxima within 0.1 s. The cause of the
held-out difference was not investigated.

## 2. Rendered sensors

The measured-target fixture in [RENDERED_SENSORS.md](RENDERED_SENSORS.md) at
headings 0, 90 and 180 degrees, NVIDIA OpenGL through VirtualGL (`egl4`).
All three captures pass the analyzer with no failed checks: image decoding and
dimensions, calibration, optical-frame transforms, marker projection, depth
against the measured wall, and laser bearings. Transport was clean.

## 3. Visible navigation

`scripts/check_unity_navigation.sh` gained opt-in `SEAN_VISIBLE=1` (rendered
1280x720 window under Xvfb, optional VirtualGL device, screen recording) and
`SEAN_SCENARIO`. Each run is a startup route, a task reset and a scene reload
under the unchanged long-route gates, including the receipt-lag gate.

| Run | Scenario | Rendering | Startup | Task reset | Scene reload |
| --- | --- | --- | --- | --- | --- |
| v01, seed 7 | None | GPU | Pass, 0.317 m | Pass, 0.322 m | Pass, 0.317 m |
| v02, seed 7 | Random (65) | GPU | Fail: 0.499 m | Pass, 0.312 m | Fail: timeout, 18.4 m |
| v03, seed 42 | Random (65) | GPU | Fail: 0.675 m | Fail: aborted, 4.6 m; 21.8 s confinement | Fail: 1 robot-on-person contact |
| v04, seed 7 | Random (65) | Headless | Pass, 0.323 m | Fail: timeout, 13.0 m | Fail: timeout, 15.6 m; 1 person-on-robot contact |

On every route, sensors stayed fresh, receipt-lag growth was at most 0.165 s,
and transport and process exits were clean. Recoveries ranged from 0 to 16 on
pedestrian routes and were zero on v01.

v02 and v04 share seed 7 and the same startup and scene-reload routes; their
task routes differ. The same startup route passed headless and failed visible,
and both scene reloads timed out. Pedestrian motion is not reproducible between
runs, so these are not paired comparisons.

What the failures show:

- **Crowd blockage.** The recordings show dense groups of `Random` agents
  filling the route. The planner repeatedly found no path, and the robot circled
  until the 300 s limit (v02 scene route: 70 m driven, never nearer than 15 m).
- **Nav2 success outside the gate.** Nav2 reported SUCCEEDED at 0.499 m and
  0.675 m. NavFn's `tolerance: 0.5` lets a replan end short of a blocked goal,
  and the Humble controller checks its 0.35 m tolerance against that path end,
  so Nav2 can succeed up to about 0.85 m away. The checker's 0.4 m gate was not
  changed. A pedestrian beside the goal is visible at the end of the v02
  startup route, but pedestrian positions were not logged, so this cause is
  likely rather than proven.
- **Contacts.** Two contacts were counted, one in each direction. Their
  circumstances have not been reviewed in the recordings.
- **Rendering is not the cause.** The headless pedestrian run fails similarly.

Observed visible frame rate was 17 to 20 fps against a 30 fps target, read from
the on-screen display; it was not logged. Endpoint container CPU averaged
100 to 109% and the Unity process 283 to 340% over pedestrian runs (161%
without pedestrians). These averages came from an earlier sampler. The committed
runner (`a026f2a`) records per-process CPU ticks instead.

Frames confirm the expected display: splash screen, then the robot's
first-person camera with overhead and third-person insets. Pedestrians animate
and walk; the yellow goal marker is visible.

## 4. Camera switching

The release `SEAN/Warehouse` scene had no view-switching control: the C-key
`CameraController` exists only in deprecated scenes (`Cameras.prefab`).
Unity `51d1453` adds `ViewSwitcher` to the SEAN display prefab. C cycles
`Auto`, `FirstPerson`, `ThirdPerson`, `Overhead` and `Top`; `-view NAME` sets the
starting view; the current view is labelled on screen. It reuses the existing
cameras and does not run in participant-controlled sessions.

Checked on player `views-da6edb0-20261029` (built from committed `da6edb0` in the
existing project, so not a clean-source build; 175 payload hashes verified):

- EditMode: 47 passed, including a test of the view cycle, argument parsing and
  the prefab component.
- Live: xdotool pressed C five times during a 50 s Warehouse capture. The player
  logged all five views in order; screenshots show the expected view each time
  and `Auto` restores both insets. `-view top` starts in the top view.
- ROS images were unaffected: all four camera streams published 244 images in
  49.7 s, with no decode errors or timestamp regressions, comparable to the
  5.35 Hz fixture capture. Transport and process exits were clean.

## 5. Contact review

The two counted contacts could not be reviewed. SEAN counts a person contact
when a person's trigger entry occurs within the robot radius plus 0.06 m
(centre distance minus the agent radius); the robot is "at fault" when moving
toward the person. Neither the time nor the agent was logged, the v03 recording
around the likely moment is inconclusive, and v04 was headless.

Unity `da6edb0` now logs each counted person contact with ROS time, agent,
distance, robot speed, fault and both positions. Three visible `Random` runs with
that player (seeds 7, 42 and 1001, recorded from the overhead view) produced no
contacts in nine routes; five routes passed. Across all 18 pedestrian routes in
this step, two contacts were counted. Future pedestrian runs record each one.

## 6. Nav2 success tolerance

Nav2 reported SUCCEEDED up to 0.675 m from the goal because NavFn's 0.5 m
tolerance lets a replan end short of a blocked goal and the goal checker tests
the path end. ROS `fe9bd37` lowers the Kuri planner tolerance to 0.05 m, so
success stays within about 0.4 m, and adds `goal_tolerance:=` and
`planner_tolerance:=` launch arguments. A launch inside the image confirmed the
defaults (0.05/0.35) and overrides (0.5/0.25) on the running nodes.

Requalification q03 repeated the q02 plan on the new player and profile:
**12 of 12 sequences, 36 of 36 routes**, goal error 0.311 to 0.337 m, wall time
up to 173.3 s, receipt-lag growth at most 0.071 s, zero recoveries, contacts
and forced Nav2 kills (q02: 0.314 to 0.342 m, 173.2 s, 0.059 s).

Pedestrian routes with the new profile repeated the three logged contact runs
(same player, seeds, `Random` scenario and overhead recording):

| Profile | Routes passed | Success beyond 0.4 m | Median recoveries | Contacts |
| --- | ---: | ---: | ---: | ---: |
| Planner tolerance 0.5 m | 5 of 9 | 0 | 6 | 0 |
| Planner tolerance 0.05 m | 2 of 9 | 0 | 16 | 1 |

Failures were aborts or timeouts in crowds; receipt-lag growth stayed at most
0.178 s and transport was clean. Pedestrian motion differs between runs and nine
routes per profile are too few to attribute the difference in pass rate to the
tolerance. Neither set happened to contain a short success, so this comparison
does not measure the case the change addresses; v02 and v03 did.

The logged contact (seed 1001, startup route) was `Agent_10`, not robot at
fault, 0.166 m, robot speed 0. The overhead recording shows Kuri stationary and
the pedestrian walking into its side. This is a pedestrian clearance issue, not
a navigation one.

## Evidence

Robovision: `/scratch/tchauhan/sean3/validation/step3-visual-20261028/`
(`encounters.sh`, `visual.sh`, per-run directories, consoles, progress logs,
recordings). Frames extracted for review are in each visible run's `frames/`.
Follow-up runs are in `step3-views-20261029/` (tests, build, view cycling),
`step3-contacts-20261029/` (logged pedestrian runs) and
`nav2-tolerance-20261029/q03/` (requalification).

## Limitations

- Both players (c01 and `views-da6edb0`) are cached, not clean-source, builds.
- One machine, two pedestrian seeds and one headless run; nine pedestrian
  routes in total.
- Frame rate, contact timing and pedestrian positions were not logged.
- Handcrafted social-situation scenarios, Lab and Outdoor scenes, and Mesa
  software rendering were not tested in this step.

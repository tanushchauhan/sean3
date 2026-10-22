# Preliminary development roadmap

This roadmap reflects the initial direction discussed with Nathan. Scope and platform versions remain provisional until the existing prototypes are reviewed.

## 1. Review existing work

- Review Michal's prototype, sensor integration, and reinforcement-learning interface.
- Identify reusable participant-control, replay, and feedback features from Howard's work.
- Select the supported ROS 2, operating-system, and Unity versions based on dependencies and available hardware.

Acceptance: documented starting commits, dependencies, reusable components, and a small set of reproducible baseline encounters.

## 2. Establish the modern baseline

- Bring up one robot in one Unity scene through ROS 2.
- Verify simulation time, transforms, odometry, velocity commands, and required sensors.
- Run one navigation task end to end and document setup.
- Compare the migrated Social Force implementation with the legacy baseline.

Acceptance: another developer can reproduce the task from documented versions, with migration-related behavioral differences recorded.

## 3. Add interchangeable pedestrian controllers

- Retain Social Forces and integrate ORCA behind a shared controller interface.
- Keep behavior graphs responsible for higher-level goals and activities.
- Define treatment of stationary people, obstacles, robot avoidance, and movement constraints.
- Update agent motion from a consistent state snapshot per simulation step.

Acceptance: the same scenario can run with either controller; trajectory and failure logs are available for comparison.

## 4. Build repeatable evaluation

- Configure scenes, initial states, goals, seeds, stopping criteria, and episode resets.
- Evaluate crossing, head-on passing, doorway, bottleneck, and stationary-person encounters.
- Measure completion, stalls, contacts, clearance, runtime, and robot-navigation outcomes.
- Define metrics before comparing controllers and report variability and failure cases.

Acceptance: a repeatable comparison report distinguishes infrastructure improvements from controller effects. ORCA integration alone is not treated as evidence of human realism or unconditional collision freedom.

## 5. Develop the STEPS and GDC workflow

- Inspect the STEPS data schema and implement playback of a short recording.
- Align trajectories to measured atrium geometry and validate against held-out landmarks.
- Explore Nucleus4D capture exports and asset-release terms.
- Start with simple measured geometry if the detailed reconstruction is not yet available.

Acceptance: a time-indexed STEPS segment plays in aligned atrium geometry with documented coordinate conventions and data provenance.

## 6. Establish the paper claim

Use the observed results to select the contribution: a practical platform release, a controlled study of pedestrian-model effects on navigation evaluation, or a stronger physically validated result. A particular venue or acceptance is not assumed.

Acceptance: an evidence-backed claim, relevant comparisons, reproducible configurations, and clearly stated limitations.

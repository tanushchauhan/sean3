# Experimental STARS Warehouse encounters

This is an opt-in research validation path, separate from the ordinary launcher.
It uses the existing fixed Warehouse encounter fixture, physical velocity
actuation and Nav2 default controller. It does not establish that a trajectory
forecaster is a qualified destination-conditioned pedestrian controller.

Use the external checkpoint/model environment described in
[the worker protocol](stars-worker.md). Build a new Linux player from the pinned
Unity source before running; older players do not implement this fixture path.
The explicit `-pedestrian-controller stars` argument is accepted only together
with `-warehouse-encounter-output`.

From this repository on a Linux host with the ROS overlay and image available:

```sh
export SEAN_STARS_CHECKPOINT=/absolute/path/to/best.pt
export SEAN_STARS_EXTENSION=/absolute/path/to/stars_steps_extension
export SEAN_WORKER_PYTHON=/absolute/path/to/stars-venv/bin/python
export SEAN_TCP_PORT=10371
export SEAN_ENCOUNTER_SEEDS=7
export SEAN_ENCOUNTER_LAYOUTS=aisle
export SEAN_ENCOUNTER_MODES=parked,nav2
export SEAN_PEDESTRIAN_ACTUATION=velocity_body

SEAN_PEDESTRIAN_CONTROLLER=stars bash scripts/check_warehouse_encounters.sh \
  /absolute/path/to/sean.x86_64 /absolute/path/to/ros_ws \
  /absolute/path/to/social_sim_ros /absolute/path/to/new-stars-results
```

Run `social_forces` and `orca` separately with the same player, fixture settings,
velocity actuator and new results directories. The fixture runs both mirrors
for every requested seed/layout/mode. A one-seed aisle pilot has four episodes
per controller; it is not a statistical benchmark or full Warehouse qualification.

The script launches one loopback-only Python worker, verifies its reported model,
checkpoint checksum, source revision and cadence, and passes its ephemeral port
to Unity. The worker's JSON startup provenance, stderr and exit/forced-stop status
are retained alongside the simulator and ROS artifacts. The provided checkpoint
records a dirty training checkout; this experimental runner explicitly permits
provisional inference and preserves that status in `worker-startup.json`.
Stopping the player closes its socket; cleanup waits for the worker before
recording any forced termination. No checkpoint or external model source is
copied into the public repository.

Unity owns actual observations, physics and animation. The worker samples at
its native 0.4-second cadence and uses eight actual position observations. The
first seven decisions hold pedestrians stationary, giving a 2.8-second observed
span before inference. Every new episode clears history; spawn/disable/enable
changes also cause an explicit population reset. Predictions never become
history. Initial motion is not supplied by SF, desired velocities or fake
positions. This stationary initialization is part of this protocol and may be
unsuitable for forecasts learned from moving trajectories.

The network has no robot, map or pedestrian-goal conditioning. Kuri is retained
in transport/core state but excluded from the learned graph. Predictions can
therefore ignore Kuri or assigned destinations. The first predicted displacement
is converted to velocity and held until the next observation. Invalid, stale or
excessive outputs stop the entire pedestrian batch; there is no clipping or
fallback. A joint-controller fault ends the matrix with the remaining episodes
unattempted and preserves an incomplete failed report.

The original acceptance checks remain in force: fixed placements, 45-second
deadline, pedestrian/robot goal thresholds, physical contacts, fresh ROS sensor
data, and successful Nav2 action evidence where requested. The analyzer also
requires STARS provenance and history-ready telemetry. A run without contacts
still fails if pedestrians do not complete their routes. Native decision rates
differ: SF updates at the physical cadence, ORCA uses its recorded configured
period, and this checkpoint uses 2.5 Hz.

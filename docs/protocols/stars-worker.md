# Local scene worker and STARS history preparation

Unity's `SocketSceneController` and workspace `runtime/stars_bridge.py` provide
a versioned local Python worker boundary and actual-state history buffer. They
can load external trained STARS weights through `runtime/stars_predictor.py`.
The launcher does not advertise a `stars`
controller until a forecasting adapter has been qualified.

## Ownership and timing

Unity owns actual poses, physics, animation and simulation time. The joint
driver calls the worker synchronously, blocking simulation-thread progress
until a complete reply or wall deadline. The scene core validates the entire
batch before physical actuation. Robot outputs are forbidden; Nav2 owns Kuri.
This is loopback TCP, not full Unity/ROS lockstep. Blocking Unity does not pause
Nav2's wall clock. The wrapper owns worker startup and process cleanup.

History contains the last `observation_steps` **executed** snapshots at `dt`.
Predictions never become history. Missing/off-cadence observations fail rather
than interpolate. N observations span `(N-1)*dt` seconds. Before readiness, all
active pedestrians receive zero velocity: warm-up is a declared held
initialization, not another controller's motion. Sampling parameters must match
at both ends and eventually come from the checkpoint, not transport defaults.

## Protocol version 1

Packets have a 4-byte unsigned big-endian length followed by UTF-8 JSON, with
a 4 MiB maximum. Listen only on `127.0.0.1`; there is no authentication or
supported remote deployment. Use a dedicated unused port.

- Reset: `version=1`, `kind="reset"`, fresh `episode`, `observation_steps`, `dt`.
  Acknowledge version/kind/episode; clear history and predictor latent state.
  Episode IDs cannot be reused on the connection.
- Step: `version=1`, `kind="step"`, matching episode, consecutive `sequence`
  starting at zero, nonnegative `time`, `actors`, `obstacles`. Actors carry
  stable IDs, robot/active masks, position, achieved velocity, heading, radius,
  maximum speed and optional destination/preferred velocity with presence
  flags. Planar values are ROS map FLU, metres and seconds. Polygon vertices
  have `x` and `y` fields.
- Decision: `version=1`, `kind="decision"`, matching episode/sequence/time,
  `valid_until=time+dt`, history `ready`, one `{id,velocity:[vx,vy]}` per active
  pedestrian. Inactive actors and Kuri remain context only.

Step requests also carry `time_token`, the invariant round-trip decimal string
of Unity's double simulation timestamp. Replies echo that exact string and
provide `valid_until_token` for the endpoint. These preserve exact identity
despite Unity JSON rounding numeric doubles. Numeric time fields remain for
inspection and must agree within 1 microsecond; tokens determine core timing.

Fixed-population sessions reject ID, role, mask and speed-limit changes until
explicit reset. This does not qualify learned-model spawn/despawn behavior.
No missing-history observations or masks are synthesized.

## Failure and shutdown

Unity bounds connect and total exchange time (default 5 seconds), including
fragmented reads. Disconnects, invalid lengths, stale replies, malformed packets
and nonfinite/excessive targets fail. There is no clipping, partial application
or SF fallback. The driver stops all pedestrian animation targets and rigidbody
velocities. Recreate a faulted connection and reset with a fresh episode.

Disposal closes the socket; Python exits on peer disconnect. The Python receive
timeout bounds abandoned connections. Idle listeners remain the launching
wrapper's responsibility. Healthy connections support task resets with history
and latent-state clearing before further observations.

## Exercise without weights

```sh
python3 runtime/stars_bridge.py --test-double --port 10382 \
  --observation-steps 8 --dt .4
python3 -m unittest discover -s tests -p test_stars_bridge.py
```

The default double returns zeros. `--moving-test-double` echoes preferred
velocities after warm-up, without learned inference or avoidance. Startup logs
name the double; neither is a STARS result.

Set `SEAN_WORKER_SCRIPT=/absolute/path/to/runtime/stars_bridge.py` when running
Unity's `SEAN.Editor.Tests` assembly. Tests cover real Python resets/warm-up,
timeouts, disconnects, stale replies, overspeed and forbidden robot targets.
The animated test covers physical motion, actual feedback, warm-up, reset and
failure stopping. Cross-process tests explicitly skip without that environment
variable; validation on robovision sets it.

## External forecasting checkpoint

The adapter supports the deterministic `stars_ma`, `phase="forecast"` recipe
at extension revision `d72eb2295c3336f0674932796cf41b60636cde3e`, with upstream
STARS submodule `13d840c5c0677ff52e928eea1679ba5ce1f19c14`. Keep both external
checkouts clean. It loads weights strictly, in evaluation/inference mode, with
PyTorch's restricted `weights_only=True` loader. It rejects incompatible
revisions, preprocessing, windows and stochastic decoders.

Prepare an isolated Python 3.12 environment with `torch==2.9.1`,
`torch-geometric==2.8.1` and `numpy==2.5.1`. Initialize only the extension's
`references/stars` submodule. No training/data-analysis dependencies are needed
for this adapter. Select an appropriate PyTorch CUDA wheel separately on GPU
hosts; the validated environment for this change is macOS CPU.

From this workspace repository, with absolute external paths:

```sh
.sean3/stars-venv/bin/python runtime/stars_bridge.py \
  --checkpoint /absolute/path/to/best.pt \
  --extension /absolute/path/to/stars_steps_extension \
  --allow-dirty-training-source \
  --port 10382 --observation-steps 8 --dt .4 --device cpu --threads 1
```

`--allow-dirty-training-source` explicitly permits provisional inference when
the training checkout had uncommitted changes. The supplied seed-0 fine-tuned
checkpoint records this condition; startup provenance preserves it. Removing
the flag rejects that checkpoint. The flag does not permit local model-source
changes or revision mismatches.

All observed pedestrians, including inactive ones, become type-1 graph nodes
in stable ID order. Kuri is excluded from the model graph because this
forecaster has no trained robot-conditioning pathway. Only active pedestrians
receive outputs. No goal, obstacle, desired speed, measured heading or achieved
velocity is fed into the network: its matching preprocessing derives motion
and headings from actual position history. The graph uses the checkpoint's
kNN/radius settings. All eight samples are present, so no history interpolation
is necessary. The first local forecast displacement is rotated into ROS map
coordinates and divided by 0.4 seconds; it is held until the next observation.
The remaining eleven forecast steps are discarded. No predicted positions are
inserted into history. Deterministic inference has no latent state to reset.

Run the opt-in real-model tests (the default suite skips them without weights):

```sh
SEAN_STARS_CHECKPOINT=/absolute/path/to/best.pt \
SEAN_STARS_EXTENSION=/absolute/path/to/stars_steps_extension \
.sean3/stars-venv/bin/python -m unittest discover -s tests -p 'test_stars*.py' -v
```

This qualifies offline inference and Python worker transport only. Unity still
requires explicit `SocketSceneController(port, 8, .4)` driver injection with
matching cadence and velocity actuation. A real-checkpoint Unity run, speed
feasibility at Kuri-scene pedestrian limits, held-history warm-up, map collisions,
destination completion and Nav2 coexistence remain unqualified. There is no
learned robot policy, goal conditioning, wall avoidance or SF fallback. No
extension source or weights are redistributed.

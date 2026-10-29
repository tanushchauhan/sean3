# Local worker preparation and ML-Agents compatibility

Unity 2022.3.62f3 supports the tested ML-Agents build/train/resume/inference
route without an editor upgrade. A separate local Python scene worker now
supports actual-state history, warm-up, reset and bounded failure handling.
Trained STARS inference remains unavailable until a forecasting checkpoint and
its preprocessing/provenance are supplied.

## ML-Agents

The isolated probe uses official release_21 commit
`7a03145ae48ad354821bd89e0243d99332149ace`, Unity package `3.0.0-exp.1`,
Sentis `1.2.0-exp.2`, Python trainer/environment packages `1.0.0`, CPython
3.10.12 and PyTorch `2.1.1+cpu`. It built with the existing licensed editor,
trained PPO to 1032 steps (1024 configured), resumed the checkpoint to 2064
steps (2048 configured), and ran 128 finite, nonzero model actions in a
standalone inference-only player without Python connected.

The first dependency-resolution attempt failed on the upstream NumPy pin;
the first trainer startup failed because current setuptools lacks
`pkg_resources`. The tested environment explicitly overrides NumPy to `1.23.5`
and pins setuptools `75.6.0`. These deviations and the complete successful
environment are documented in the
[probe reproduction guide](../../experiments/mlagents/README.md).

The training player used the initial probe script; the inference player added
the bounded inference exit check. Both source hashes are recorded. The model
embedded in the inference player is the original 1032-step export; the final
results directory also retains the later resumed export. They are distinct
artifacts. Minimal-project package resolution, build and inference do not
establish compatibility with every dependency in the full SEAN project.
No Kuri training, reward qualification or navigation-performance claim follows.

## Worker preparation

Unity `688d0e0` adds `SocketSceneController` to the standalone controller
assembly. Workspace runtime `8d39b24` provides the Python session and bounded
history. The driver blocks the simulation thread during a joint exchange,
validates a complete batch and applies velocity targets at the existing shared
physics boundary. Robot targets are forbidden. History contains actual states,
not predicted rollouts; N sample instants span N-1 intervals. Fixed-population
changes need an explicit new episode. Warm-up commands zero pedestrian motion.

The actual animated test exposed JSON rounding of simulation timestamps.
Round-trip decimal timestamp tokens now preserve source identity and endpoint
precision. Sequence/episode checks, whole-batch validation and bounded wall
timeouts remain enforced. There is no clipping or fallback controller.

Final validation on robovision: **84/84 Unity project tests passed, zero skips**,
with `SEAN_WORKER_SCRIPT` set. This includes real Python transport, warm-up,
reset, timeout/disconnect, stale/invalid output rejection, forbidden robot
targets, and production animated-avatar physical motion/feedback/stopping.
The workspace regression suite passes **69 tests**, including a timestamp
rounding regression and real subprocess/socket exchange.

Earlier failures are retained: an unfiltered invocation attempted a bundled
connector player-build test without its build setup; animated-test refactoring
initially mishandled play-mode/domain-reload transitions; and the timestamp
rounding defect was found by the real physical integration. Final validation
explicitly targets `SEAN.Editor.Tests`, the project assembly used for this gate.

The worker currently supplies explicitly labeled hold/preferred-velocity test
doubles only. No STARS weights/code are bundled, no `stars` launcher choice is
enabled, and no full ROS lockstep or robot-policy arbitration is implemented.
See the [worker protocol](../protocols/stars-worker.md) for the transport and
remaining trained-model gate.

## ORCA investigation

The [separate diagnosis](2026-10-29-orca-navigation-diagnosis.md) identifies the
original Nav2 collision-check/recovery abort and an approximate 7.37 cm overlap
of its padded navigation envelope with a stopped pedestrian. The original
costmap was not captured. One unchanged repeat with new costmap/feedback
instrumentation passes 4/4; it does not reproduce or erase the original 3/4
result. No navigation or pedestrian behavior was changed to obtain that pass.

## Evidence

The [manifest](2026-10-29-worker-and-mlagents-manifest.json) records versions,
source/artifact hashes, test XML identity and both ORCA diagnostic summaries.
Robovision retains `mlagents-probe/`, `validation/worker-20261029/` and
`validation/orca-diagnosis-20261029/` under `/scratch/tchauhan/sean3/`.
Local evidence copies are under ignored `.sean3/evidence/`. Large binaries,
generated projects, checkpoints and trajectories remain outside Git.

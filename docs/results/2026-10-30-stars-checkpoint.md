# STARS checkpoint adapter: offline and worker validation

This report covers the initial adapter and open-floor integration. Subsequent
standalone Warehouse testing is recorded in the
[matched pilot report](2026-10-30-stars-warehouse-pilot.md), including its failures.

The supplied seed-0 fine-tuned multi-agent forecasting checkpoint loads strictly
against external `stars_steps_extension` revision
`d72eb2295c3336f0674932796cf41b60636cde3e` and its pinned upstream STARS revision
`13d840c5c0677ff52e928eea1679ba5ce1f19c14`. Checkpoint SHA-256:
`382d2c00d818f43dda8d3406d857d824c439bba2918d7872dd576b56b8abaaa3`.
No weights or external source are committed in this repository.

The checkpoint declares `model=stars_ma`, `phase=forecast`, seed 0,
`encoder_mode=finetune`, a deterministic decoder, eight observations at 2.5 Hz,
twelve prediction steps, kNN 16 and radius 10 metres. Eight observation instants
span 2.8 seconds. It records raw XY inputs/targets with no standardization.
Its selected epoch is 98; its embedded validation all-agent ADE is approximately
0.1061 metres. That metric is training-run metadata and has not been independently
reproduced here; synthetic integration tests do not measure forecasting quality.

The training checkout records `git_dirty=true`. The operator authorized proceeding
with provisional inference. The worker requires an explicit
`--allow-dirty-training-source` flag and reports this status in startup provenance.
Strict state-dictionary loading verifies architecture compatibility; it does not
establish that unrecorded training-source changes were immaterial.

## Validation

On macOS CPU with Python 3.12.5, PyTorch 2.9.1, torch-geometric 2.8.1 and NumPy
2.5.1, the full Python regression suite passes **74/74 tests, zero skips** with
the checkpoint environment variables enabled. Five new real-checkpoint tests
cover:

- Numerical agreement with direct upstream graph construction and scene-frame
  forecasting, including the first-displacement-to-velocity conversion.
- Rotation/translation equivariance, stable ID mapping and exclusion of robot
  position from the human-only graph.
- Reset repeatability, preservation of actual input history, inactive pedestrian
  target masking and an empty pedestrian population.
- Seven held warm-up observations, then rejection of a forecast above the
  configured speed limit, with a faulted session remaining stopped.
- An actual checkpoint-backed Python worker subprocess, framed TCP exchanges,
  ready/non-ready responses, subsequent observation and reset, and clean exit.

See the [machine-readable manifest](2026-10-30-stars-checkpoint-manifest.json)
for checkpoint metadata and the complete installed package versions, and the
[worker protocol](../protocols/stars-worker.md) for setup and commands.

## Robovision Unity validation

After connectivity was restored, the code, checkpoint and pinned model sources
were synchronized to robovision. The checkpoint checksum matches the original
above. A dedicated CPU environment uses Python 3.12.3, PyTorch 2.9.1+cpu,
torch-geometric 2.8.1 and NumPy 2.5.1. The full Python suite passes 74/74 tests
with no skips on Linux as well.

Unity 2022.3.62f3 passes **85/85 project tests, zero skips**, including a new
`AnimatedAvatarsUseStarsCheckpointAndStopOnProcessLoss` test and both existing
animated-avatar tests. The new test uses production Rocketbox avatars, the
physical velocity actuator, the actual checkpoint-backed Python process and
the normal joint scene driver on an open test floor. It checks:

- Eighteen consecutive scene observations; history becomes ready at sequence 7,
  with zero targets on the first seven decisions.
- Pedestrian-only target batches, bounded achieved planar speed, physical
  displacement and nonzero movement in subsequent actual-state snapshots.
- Immediate velocity/target clearing on reset, a new episode ID, and history
  returning to non-ready before warming up again.
- Actual Python process termination while a nonzero target is active, followed
  by the driver's fault/stop behavior, under 5 mm residual planar motion over
  0.5 simulated seconds, and an unchanged external robot pose.

The maximum target speed was approximately **0.02024 m/s**. The maximum complete
decision exchange took 28.213 ms in the focused animated run and 25.9255 ms in
the full-suite run. These are diagnostics from two small stationary-start test
runs, not a latency benchmark or a claim of realistic pedestrian motion. No
owned worker or Unity editor process remained after the tests. Existing remote
Rocketbox metadata and UserSettings changes were preserved.

Raw XML/logs are preserved under local `.sean3/evidence/stars-checkpoint-20261030/`
and remote `/scratch/tchauhan/sean3/validation/stars-checkpoint-20261030/`.
Their hashes, exact source revision and Linux package versions are in the
manifest. The workspace pins the tested Unity revision.

## Limits and next validation

No new standalone player or real-checkpoint Warehouse/Nav2 encounter was run
for the initial integration evidence in this report; see the subsequent pilot above.

The model consumes actual pedestrian position histories only. It has no robot,
map, destination or commanded-speed conditioning. The adapter executes the first
forecast segment and discards the rest, with no clipping or controller fallback.
Forecasts may exceed SEAN scene speed limits; those requests deliberately fail
and stop rather than silently change the learned output. Held warm-up histories,
physical collisions, reaching destinations and simultaneous Nav2 behavior remain
to be tested beyond the open-floor integration. This change neither exposes a production `stars` launcher option
nor establishes a learned robot controller.

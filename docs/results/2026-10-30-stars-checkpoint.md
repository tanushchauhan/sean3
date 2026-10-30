# STARS checkpoint adapter: offline and worker validation

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

## Limits and next validation

Robovision SSH timed out during this work. Its checkout has not been synchronized
and no real-checkpoint Unity/ROS test or new player build was performed. Existing
Unity test-double evidence must not be reported as learned-model validation.

The model consumes actual pedestrian position histories only. It has no robot,
map, destination or commanded-speed conditioning. The adapter executes the first
forecast segment and discards the rest, with no clipping or controller fallback.
Forecasts may exceed SEAN scene speed limits; those requests deliberately fail
and stop rather than silently change the learned output. Held warm-up histories,
physical collisions, reaching destinations and simultaneous Nav2 behavior remain
to be tested. This change neither exposes a production `stars` launcher option
nor establishes a learned robot controller.

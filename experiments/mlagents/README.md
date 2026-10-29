# Unity ML-Agents compatibility probe

The existing Unity **2022.3.62f3** editor can build an ML-Agents environment,
train a small PPO policy, resume its checkpoint, and execute its exported ONNX
model in a standalone Linux player. An editor upgrade is unnecessary for this
tested route. This isolated scalar task is a compatibility check, not a Kuri
navigation environment or evidence of learned navigation quality.

## Tested versions

| Component | Version |
| --- | --- |
| Official ML-Agents source | `release_21`, `7a03145ae48ad354821bd89e0243d99332149ace` |
| Unity package | `3.0.0-exp.1` |
| Sentis | `1.2.0-exp.2` |
| Python trainer / environments | `1.0.0` / `1.0.0` |
| CPython | `3.10.12` |
| PyTorch | `2.1.1+cpu` |
| NumPy / setuptools | `1.23.5` / `75.6.0` |

The [release_21 package manifest](https://github.com/Unity-Technologies/ml-agents/blob/7a03145ae48ad354821bd89e0243d99332149ace/com.unity.ml-agents/package.json)
declares Unity 2022.3. The [release_22 manifest](https://github.com/Unity-Technologies/ml-agents/blob/release_22/com.unity.ml-agents/package.json)
requires 2023.2; do not mix its Unity package with this trainer.

Two upstream compatibility issues were encountered and retained in the logs:

- The environment package pins NumPy `1.21.2`; ordinary dependency resolution
  rejects the tested `1.23.5` environment. Use the explicit override below.
  This is a declared metadata deviation, not an unmodified upstream install.
- Current setuptools removed `pkg_resources`, which this trainer imports.
  Pinning `75.6.0` restores the required API.

Keep this environment separate from ROS and STARS. It does not install packages
into the simulator's normal project or alter its package manifest.

## Reproduce

On Linux with the existing editor and `xvfb-run`, create a dedicated directory
and check out the official revision above. `ML_SOURCE`, `PROBE_PROJECT`,
`PROBE_OUT`, `PROBE_ENV`, and `EDITOR` below are absolute paths chosen for that
directory and editor. `PROBE_PROJECT` must not exist yet.

```sh
uv venv --python 3.10.12 "$PROBE_ENV"
uv pip install --python "$PROBE_ENV/bin/python" \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  -r experiments/mlagents/requirements-tested.txt
printf 'numpy==1.23.5\n' > "$PROBE_OUT/numpy-override.txt"
uv pip install --python "$PROBE_ENV/bin/python" \
  --override "$PROBE_OUT/numpy-override.txt" \
  "$ML_SOURCE/ml-agents-envs" "$ML_SOURCE/ml-agents"
python3 experiments/mlagents/prepare.py "$ML_SOURCE" "$PROBE_PROJECT"
SEAN_PROBE_PLAYER="$PROBE_OUT/training/probe.x86_64" \
  DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1 GIT_CONFIG_GLOBAL=/dev/null \
  xvfb-run -a "$EDITOR" -batchmode -quit -projectPath "$PROBE_PROJECT" \
  -executeMethod BuildProbe.Build -logFile "$PROBE_OUT/build.log"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$PROBE_ENV/bin/mlagents-learn" experiments/mlagents/probe.yaml \
  --env "$PROBE_OUT/training/probe.x86_64" --run-id compatibility \
  --results-dir "$PROBE_OUT/results" --base-port 10381 --no-graphics --time-scale 20
```

For checkpoint resume, copy `probe.yaml`, increase `max_steps` to 2048, and run
the same command with the copied configuration and `--resume`. Keep the same
run ID and results directory. The tested runs exported at steps 1032 and 2064;
trainer batch boundaries can exceed the configured step limit slightly.

For embedded inference, copy the exported `CompatibilityProbe.onnx` into
`$PROBE_PROJECT/Assets/CompatibilityProbe.onnx`, rebuild to a **different** player
path with the same builder, then run:

```sh
"$PROBE_OUT/inference/probe.x86_64" -batchmode -nographics \
  -probe-inference-steps 128 -logFile "$PROBE_OUT/inference.log"
```

The builder detects the imported model and selects `InferenceOnly`. The probe
requires finite, nonzero model actions without a Python communicator, logs
`PROBE_INFERENCE ... passed=True`, and exits zero after 128 actions. No reward
or navigation-performance threshold is asserted.

## Evidence and limits

Robovision evidence: `/scratch/tchauhan/sean3/mlagents-probe/`. Initial unmodified
dependency resolution failed (`install.log`); initial trainer startup failed
without the setuptools pin (`train.log`). Successful training, resume and
inference are retained in `train-02.log`, `resume.log`, `inference.log`, build
logs, resolved package lock, Python freeze and `results/compatibility-02/`.
Generated projects, players and checkpoints stay outside Git.

This is a new minimal project, not an ML-Agents installation in SEAN. Shared
project dependency conflicts, Kuri observations/actions, reward design,
simulation stepping and robot command ownership still require their own work.
The experimental package is a tested option, not a commitment to adopt it.

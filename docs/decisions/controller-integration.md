# Pedestrian controller integration decision — October 29, 2026

## Source ownership and synchronization

The workspace is `sean3/`; authoritative editable components are its existing
sibling `social_sim_unity/` and `social_sim_ros/` checkouts, on their existing
feature branches. Leave `sean3/sources/` unpopulated during this work rather
than editing two component copies. Use launcher `--ros-source` and build
`--unity-source` overrides where required. Do not change submodule pins until
the corresponding candidate is built and runtime-tested.

Robovision's matching working directories are under `/scratch/tchauhan/sean3/`.
Its workspace was fast-forwarded from `689f80e` to local `cf69676` using a Git
bundle. New contract/test/configuration files are transferred explicitly with
rsync. Changes remain uncommitted; the source inventory and file hashes identify
them. Preserve remote Rocketbox metadata changes, UserSettings, crash blobs and
AppleDouble files, and the local historical `REVIEW_2026-10-26.md`. The baseline
runtime player is the accepted fresh-build artifact, not a new build of these
uncommitted controller changes.

## Runtime responsibilities

Unity owns authoritative state, geometry, clock, reset, animation and physical
application. The standalone `SEAN.Controllers` assembly supplies a scene-level
contract with one validated target batch per snapshot. It currently has no
production scene registration or ROS dependency. ROS will own the worker
transport, Nav2 connection and eventual exclusive robot command ownership.
The workspace owns schemas, comparison orchestration, evidence and component
pins. The established SF+Nav2 launcher path remains the baseline.

STARS will run in a separate pinned Python environment. The inspected source's
`pyproject.toml` requires Python >=3.12 and pins torch 2.9.1, torch-geometric
2.8.1 and numpy 2.5.1 among other dependencies. Robovision has Python 3.12.3;
that alone does not establish a compatible installed inference environment.
Do not install these packages into ROS Humble's environment. No new training
or externally billed jobs have been started.

## Model provenance and prerequisite limits

Pinned reviewed source: `michaelmunje/stars_steps_extension` at
`d72eb2295c3336f0674932796cf41b60636cde3e`. Durable checkouts exist locally at
`sean3/.sean3/models/stars_steps_extension` and on robovision at
`/scratch/tchauhan/sean3/sean3/.sean3/models/stars_steps_extension`. They were
created from a bundle of the reviewed revision, not a claim about latest upstream.
Its STARS reference submodule is pinned to
`13d840c5c0677ff52e928eea1679ba5ce1f19c14` and is unpopulated.

No trained `.pt`/`.pth`/`.ckpt` file was found in the reviewed checkout or the
bounded `/scratch/tchauhan` search (maximum depth four). This does not establish
that none exists elsewhere. No dataset or checkpoint has been designated for
this integration, and no calibrated STEPS-to-Unity transform is available.
No top-level license was found in the reviewed model checkout; review the model
and reference implementation's reuse terms before importing their code.
Trained-model validation remains blocked on weights, architecture/preprocessing
configuration, training/evaluation provenance, applicable reuse terms, and a
verified separate inference environment. Synthetic contract tests cannot clear it.

Decision 15 in the model repository proposes a future `sean3/` Python package
alongside `src/`. This integration retains the established Unity/ROS workspace
and reuses the model through a worker boundary. A future upstream Python
adapter may live there, but it will not relocate or duplicate this simulator.
Historical upstream job/push instructions supply no authorization here.

## Next dependency

Complete an opt-in production snapshot/sink/reset path and verify animated
following and synchronous stepping with a fake controller. Only then select a
license-compatible ORCA implementation and connect one scene-wide solver.
STARS source/interface work can proceed independently, but live model claims
must wait for the missing model artifacts. See the
[contract](../protocols/scene-controller-contract.md) and
[result](../results/2026-10-29-controller-integration.md).

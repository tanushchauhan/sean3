# SEAN 3 development workspace

Development entry point for modernizing SEAN 2 and evaluating pedestrian controllers. This repository coordinates component versions, setup, and experiments; simulator and ROS code remain in their respective forks.

## Current status

The development branches target ROS 2 Humble and Unity 2022.3.62f3. The ROS
package builds, all eight Nav2 lifecycle nodes activate, and the velocity
smoother passes command-routing and timeout checks. The current candidate passes
42 Unity EditMode tests and 26 harness regressions. The unchanged endpoint
previously passed 12 compatibility, socket, and process tests. The earlier transport candidate passed six task resets
and six scene reloads with fresh sensors, clock continuity, stable graph counts,
and bounded resource growth. Its headless and NVIDIA rendered sequences also
passed clean closure and process exit checks; those larger sequences were not
rerun on the latest pedestrian-response candidate. See the [transport result](TRANSPORT_RESULT_2026-10-27.md)
and [VALIDATION.md](VALIDATION.md) for exact versions, commands, and limits.

Three live Warehouse navigation checks pass: initial startup, task reset, and
scene reload, with fresh sensors and a continuous clock. Earlier rendered RGB/depth,
optical frames, calibration, and measured laser geometry checks passed at three headings
on Mesa and NVIDIA OpenGL. See the [sensor result](RENDERED_SENSOR_RESULT_2026-10-27.md)
and [reproduction guide](RENDERED_SENSORS.md). The bounded Warehouse random-task
placement checks now pass with ROS-map and live-geometry constraints; see the
[placement result](PLACEMENT_RESULT_2026-10-27.md) and [guide](PLACEMENT.md).
The earlier longer-navigation milestone passed six actual generated routes across
seeds 7 and 42 with zero recorded physical object contacts, stalls, or recovery
actions, and clean shutdown. The configured robot is Kuri; earlier Jackal labels
came from the ROS profile name. See the [longer-navigation result](LONG_NAVIGATION_RESULT_2026-10-27.md)
and [protocol](LONG_NAVIGATION.md). Participant workflows, populated scenarios,
and broader navigation reliability still need validation. The earlier clean-source
Unity build milestone passed for the
configured Warehouse fixture: twelve EditMode tests and all three navigation
stages pass after fixing the Rocketbox importer. See the
[October 27 build review](CLEAN_BUILD_RESULT_2026-10-27.md). These checks reuse
the recorded environment and do not establish bit-for-bit reproducibility.
ORCA remains unimplemented. Review Michal's prototype and
Howard's extensions before adding new sensor, learning, or study interfaces.

The pedestrian-response milestone now passes 60 controlled checks with the
actual Kuri body and animated pedestrians, covering parked, moving and yielding
robots, no-robot controls, a fresh seed and a larger time step. ColliderV1 adds
physical robot geometry, braking and obstacle-aware sidestepping, with an
independent contact-model correction for animated walking. The Legacy-force
comparison holds contact physics fixed. These are single-person open-floor checks, not populated
Warehouse or human-realism validation. See the [pedestrian result](PEDESTRIAN_AVOIDANCE_RESULT_2026-10-28.md)
and [protocol](PEDESTRIAN_AVOIDANCE.md). Multi-person encounters and an oblivious
robot control are next, to check both safety and benchmark difficulty.

## Repositories

| Component | Development fork | Upstream |
| --- | --- | --- |
| Unity simulator | [social_sim_unity](https://github.com/tanushchauhan/social_sim_unity) | [yale-sean/social_sim_unity](https://github.com/yale-sean/social_sim_unity) |
| ROS integration | [social_sim_ros](https://github.com/tanushchauhan/social_sim_ros) | [yale-sean/social_sim_ros](https://github.com/yale-sean/social_sim_ros) |
| Workspace and roadmap | This repository | New coordination repository |

`sean3.repos` preserves the original SEAN 2 revisions. `sean3-candidate.repos`
pins the migration revisions used for the component checks below. The candidate
is not yet a validated end-to-end simulator release.

## Get the workspace

Clone this entry-point repository first:

```sh
gh repo clone tanushchauhan/sean3
cd sean3
git switch feature/ros2-environment
```

With `vcstool` installed and `vcs` available, import the pinned components:

```sh
mkdir -p sources
vcs import sources < sean3-candidate.repos
git -C sources/social_sim_unity submodule update --init --recursive
git -C sources/social_sim_ros submodule update --init --recursive
```

The imported repositories live under the ignored `sources/` directory. The Unity project is `sources/social_sim_unity`; the ROS repository is `sources/social_sim_ros`.

Importing commit pins can leave component repositories at detached HEAD. Before editing, create a descriptive branch in the component you are changing, for example:

```sh
git -C sources/social_sim_unity switch -c feature/orca-controller
```

Add upstream remotes once per component checkout:

```sh
git -C sources/social_sim_unity remote add upstream https://github.com/yale-sean/social_sim_unity.git
git -C sources/social_sim_ros remote add upstream https://github.com/yale-sean/social_sim_ros.git
```

Use [VALIDATION.md](VALIDATION.md) for existing ROS and Unity checks and
[CLEAN_BUILD.md](CLEAN_BUILD.md) for the clean-source build procedure and
acceptance criteria. The legacy `sim_ws` remains a [reference](https://github.com/yale-sean/sim_ws), rather than a dependency of the new workspace.

## Development workflow

- Implement simulator changes in the Unity fork and ROS changes in the ROS fork.
- Use focused branches and pull requests against the development forks.
- Keep migration changes separate from pedestrian-controller changes so their effects can be evaluated independently.
- Submit suitable fixes upstream; coordinate the ROS 2 migration with the upstream maintainers.
- Record experiment configuration, random seeds, component commits, platform versions, and results when validating a combination.
- Keep STEPS recordings, scan assets, generated builds, and local credentials outside Git. Document access and asset terms separately.

See [ROADMAP.md](ROADMAP.md) for milestones and acceptance criteria and [BASELINE.md](BASELINE.md) for initial source revisions. The initial dependency pins are also tagged `sean2-baseline` in each development fork.

## Attribution

The two core SEAN repositories declare BSD-3-Clause licenses. Preserve their license files and attribution when modifying or redistributing them. Third-party code, Unity assets, avatars, and reconstructed environments may have separate terms; their availability is not implied by this workspace.

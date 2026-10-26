# SEAN 3 development workspace

Development entry point for modernizing SEAN 2 and evaluating pedestrian controllers. This repository coordinates component versions, setup, and experiments; simulator and ROS code remain in their respective forks.

## Current status

The development branches target ROS 2 Humble and Unity 2022.3.62f3. The ROS
package builds, all eight Nav2 lifecycle nodes activate, and the velocity
smoother passes command-routing and timeout checks. Nine Unity EditMode tests
and six startup-check regression tests pass. See [VALIDATION.md](VALIDATION.md)
for versions, commands, and limits.

Three live Warehouse navigation checks pass: initial startup, task reset, and
scene reload, with fresh sensors and a continuous clock. Participant workflows,
camera rendering, collision metrics, and broader navigation scenarios still
need validation. ORCA remains unimplemented. Review Michal's prototype and
Howard's extensions before adding new sensor, learning, or study interfaces.

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

Use [VALIDATION.md](VALIDATION.md) for the current ROS container and Unity test procedure. The legacy `sim_ws` remains a [reference](https://github.com/yale-sean/sim_ws), rather than a dependency of the new workspace.

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

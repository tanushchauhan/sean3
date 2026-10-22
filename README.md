# SEAN 3 development workspace

Development entry point for modernizing SEAN 2 and evaluating pedestrian controllers. This repository coordinates component versions, setup, and experiments; simulator and ROS code remain in their respective forks.

## Current status

Repository setup only. The component forks currently contain the upstream SEAN 2 baseline. ROS 2 migration, a Unity upgrade, and ORCA integration have not been implemented or tested. Review Michal's prototype and Howard's extensions before choosing implementation starting points.

## Repositories

| Component | Development fork | Upstream |
| --- | --- | --- |
| Unity simulator | [social_sim_unity](https://github.com/tanushchauhan/social_sim_unity) | [yale-sean/social_sim_unity](https://github.com/yale-sean/social_sim_unity) |
| ROS integration | [social_sim_ros](https://github.com/tanushchauhan/social_sim_ros) | [yale-sean/social_sim_ros](https://github.com/yale-sean/social_sim_ros) |
| Workspace and roadmap | This repository | New coordination repository |

The dependency manifest `sean3.repos` pins exact component revisions. Update it only when a new combination has been checked together. These initial pins record provenance; they do not indicate that the baseline has been validated on current hardware.

## Get the workspace

Clone this entry-point repository first:

```sh
gh repo clone tanushchauhan/sean3
cd sean3
```

With `vcstool` installed and `vcs` available, import the pinned components:

```sh
mkdir -p sources
vcs import sources < sean3.repos
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

Installation of ROS, Unity, sensors, and navigation dependencies will be documented after the prototype review and platform selection. The legacy `sim_ws` remains a [reference](https://github.com/yale-sean/sim_ws), rather than a dependency of the new workspace.

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

# SEAN 3

SEAN 3 is the modernized Social Environment for Autonomous Navigation: a Unity
simulator of people and a mobile robot, driven through ROS 2. It updates SEAN 2
to Unity 2022.3 and ROS 2 Humble.

This repository is the workspace. It pins the two component repositories, holds
the Docker setup, run and test scripts, and documents every validation result.

## Repositories

| Component | Fork | Upstream |
| --- | --- | --- |
| Unity simulator | [social_sim_unity](https://github.com/tanushchauhan/social_sim_unity) | [yale-sean/social_sim_unity](https://github.com/yale-sean/social_sim_unity) |
| ROS 2 integration | [social_sim_ros](https://github.com/tanushchauhan/social_sim_ros) | [yale-sean/social_sim_ros](https://github.com/yale-sean/social_sim_ros) |
| Workspace | this repository | |

`sean3-candidate.repos` pins the current development versions; `sean3.repos`
pins the original SEAN 2 revisions.

## Status

Development baseline, not yet a release. On the reference machine (Linux,
NVIDIA GPU, rootless Podman):

- Kuri navigates the Warehouse with Nav2 across startup, task resets and scene
  reloads: 36 of 36 qualification routes.
- 80 controlled four-person encounters pass with no contacts.
- Camera, depth and laser output match a measured target; the window can switch
  between first-person, third-person, overhead and top views.
- In a dense crowd of 65 random pedestrians, Kuri completes only some routes.
  This is open work.

See [docs/validation.md](docs/validation.md) for the full history and the dated
reports in [docs/results](docs/results).

## Quick start

```sh
git clone https://github.com/tanushchauhan/sean3.git
cd sean3
git switch feature/ros2-environment
./sean3 setup
./sean3 build-player --unity /path/to/Unity-2022.3.62f3/Editor/Unity
./sean3 run
```

`setup` fetches the components into `sources/` and builds the ROS image.
`run` starts ROS, Nav2 and the simulator; Ctrl+C stops all of them. See
[docs/getting-started.md](docs/getting-started.md) for requirements, options,
controls and troubleshooting. To change a component, create a branch in its
`sources/` checkout first, since the pins leave it at a detached HEAD.

## Documentation

| Folder | Contents |
| --- | --- |
| [docs/getting-started.md](docs/getting-started.md) | Setup, running, controls and troubleshooting |
| [docs/roadmap.md](docs/roadmap.md) | Milestones |
| [docs/validation.md](docs/validation.md) | Validation history and how to run the checks |
| [docs/protocols](docs/protocols) | How each test is defined and run |
| [docs/results](docs/results) | Dated result reports |
| [docs/baseline.md](docs/baseline.md) | SEAN 2 starting revisions |

## Contributing

Simulator changes go to the Unity fork and ROS changes to the ROS fork, on
focused branches. Record seeds, component commits and platform versions with
any result. Keep recordings, scans, builds and credentials out of Git.

## License

The SEAN components are BSD-3-Clause; keep their license files and attribution.
Third-party code, Unity assets, avatars and environments may have their own terms.
SEAN was created by the Interactive Machines Group at Yale.

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

The two components are git submodules under `sources/`, pinned to the versions
this workspace was tested with. `sean3.repos` records the original SEAN 2 revisions.

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
- Experimental ORCA and shared physical pedestrian actuation are implemented
  with a bounded local Python worker/history boundary. A matched four-case aisle pilot
  passes 4/4 with SF and 3/4 with ORCA, with zero contacts on both; one ORCA/Nav2
  robot goal fails. See
  [the controller result](docs/results/2026-10-29-orca-controller.md).
- The external seed-0 STARS forecast checkpoint loads through the Python worker;
  all 74 Python tests and 85 Unity project tests pass on robovision, including
  real-checkpoint animated motion, reset and process-loss stopping. Warehouse
  encounters and Nav2 coexistence with these weights remain unqualified. See
  [the checkpoint validation](docs/results/2026-10-30-stars-checkpoint.md) and
  [worker instructions](docs/protocols/stars-worker.md).
- An isolated ML-Agents probe builds, trains PPO, resumes a checkpoint and runs
  exported-model inference with the existing Unity 2022.3 editor. See the
  [tested versions and reproduction steps](experiments/mlagents/README.md).

See [docs/validation.md](docs/validation.md) for the full history and the dated
reports in [docs/results](docs/results).

## Quick start

```sh
git clone --recursive -b feature/ros2-environment https://github.com/tanushchauhan/sean3.git
cd sean3
./sean3 setup
./sean3 build-player --unity /path/to/Unity-2022.3.62f3/Editor/Unity
./sean3 run
```

`setup` builds the ROS image, and fetches the components if the clone was not
recursive. `run` starts ROS, Nav2 and the simulator; Ctrl+C stops all of them.
See [docs/getting-started.md](docs/getting-started.md) for requirements,
options, controls and troubleshooting.

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
focused branches. Inside `sources/<component>`, check out a branch before
editing (submodules start at a detached commit) and push it to the fork. Then
commit the updated submodule in this repository, so the workspace pins the
version that was tested. Record seeds, component commits and platform versions
with any result. Keep recordings, scans, builds and credentials out of Git.

## License

The SEAN components are BSD-3-Clause; keep their license files and attribution.
Third-party code, Unity assets, avatars and environments may have their own terms.
SEAN was created by the Interactive Machines Group at Yale.

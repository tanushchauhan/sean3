# Getting started

This guide takes a Linux machine from nothing to a running SEAN 3 simulation.
Everything goes through the `./sean3` script at the top of this repository.

## Requirements

- Linux x86_64. SEAN 3 is developed on Ubuntu with an NVIDIA GPU.
- Docker or rootless Podman, for the ROS 2 Humble side.
- Python 3.8 or newer, Git, and [vcstool](https://github.com/dirk-thomas/vcstool)
  (`pip install vcstool`).
- Unity 2022.3.62f3 with a license, to build the simulator.
- For a window: a desktop session. On a server, `xvfb` gives a virtual display
  and `ffmpeg` records it. VirtualGL (`vglrun`) lets a server render on its GPU.

## 1. Set up

```sh
git clone https://github.com/tanushchauhan/sean3.git
cd sean3
git switch feature/ros2-environment
./sean3 setup
```

`setup` fetches the pinned Unity and ROS repositories into `sources/`, builds
the ROS image `sean3-humble:local` (several minutes the first time) and builds
the ROS package. It is safe to run again.

## 2. Build the simulator

```sh
./sean3 build-player --unity /path/to/Unity-2022.3.62f3/Editor/Unity
```

The build goes into `builds/<commit>-<time>/`, and `builds/latest` points to it.
Unity must be activated first; the build log is kept in the build folder.

## 3. Check

```sh
./sean3 doctor
```

Each line reports `ok` or `FAIL` with the fix. Pass the same options you will
use with `run`, for example `--headless` on a machine without a display.

## 4. Run

```sh
./sean3 run
```

This starts the ROS endpoint, the simulator, Nav2 and a task driver. Kuri gets a
random goal in the Warehouse, drives there with Nav2, and the next task starts.
Press Ctrl+C to stop everything; the script shuts down Nav2, the simulator and
the ROS container in order.

Common options:

| Option | Effect |
| --- | --- |
| `--scenario Random` | 65 people walking between random points (`None` has no people) |
| `--seed 42` | Different starting positions and goals |
| `--view top` | Start in another view: `auto`, `first-person`, `third-person`, `overhead`, `top` |
| `--headless` | No rendering; fastest, but camera topics do not publish |
| `--record run.mkv` | Render on a virtual display and save a video |
| `--gpu egl0` | Render on that GPU through VirtualGL |
| `--no-nav2` | Start only ROS and the simulator, to drive the robot yourself |
| `--no-loop` | Stop giving new goals after the first task |
| `--port 10001` | Use another TCP port, for example for a second run |

Only the Warehouse is validated. `--scene lab` and `--scene outdoor` start, but
have not been tested with SEAN 3.

## Controls

| Where | Control | Effect |
| --- | --- | --- |
| Simulator window | C | Cycle the view |
| Another terminal | `./sean3 next-task` | Start a new task (new start and goal) |
| Another terminal | `./sean3 reload-scene` | Reload the scene |
| Terminal running `run` | Ctrl+C | Stop everything |

ROS topics are inside the container. To use ROS tools against a running
simulation, open a shell there:
`docker exec -it $(docker ps -qf name=sean3-run) bash` (or `podman`).

## Logs

Each run writes to `logs/<time>/`: `player.log` (Unity), `endpoint.log`,
`nav2.log` and `task-driver.log`. The driver log lists each task and whether
Nav2 succeeded or aborted.

## When something goes wrong

The script stops with a message saying what failed and what to do. The most
common ones:

| Message | Fix |
| --- | --- |
| ROS image ... is missing | `./sean3 setup` |
| tf2 and tf2_ros versions differ | `./sean3 setup --rebuild-image`; mismatched versions deadlock Nav2 |
| No simulator build at ... | `./sean3 build-player --unity PATH` or `--player PATH` |
| Port ... is in use | Another run is active; stop it or pass `--port` |
| No display is available | Use a desktop, install `xvfb`, or pass `--headless` |
| The simulator did not connect to ROS | Read `player.log`; often a missing graphics driver |
| The simulator exited during startup | Read `player.log` |

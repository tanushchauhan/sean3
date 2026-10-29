# SEAN 3 development workspace

Development entry point for modernizing SEAN 2 and evaluating pedestrian controllers. This repository coordinates component versions, setup, and experiments; simulator and ROS code remain in their respective forks.

## Current status

The development branches use Unity 2022.3.62f3 and ROS 2 Humble. The current
clean-source candidate passes 80 controlled four-person Warehouse encounters
(320 person routes), including sixteen live Nav2 actions, with zero recorded
physical contacts. Forty-five Unity tests, 53 harness regressions, five installed
costmap controls and ordinary startup/task-reset/scene-reload navigation pass.
This autonomous fixture does not require Michal's prototype or Howard's extensions.
See the [multi-person result](WAREHOUSE_ENCOUNTERS_RESULT_2026-10-28.md) and
[protocol](WAREHOUSE_ENCOUNTERS.md) for exact source pins, geometry and limits.

**Longer normal navigation now passes a bounded prospective campaign.** With
Unity `1fec526` (one `/tf` message per frame) and the tf2-matched ROS image
`localhost/sean3-humble:tf2-0.25.24`, 12 of 12 startup/task-reset/scene-reload
sequences (36 routes, eight seeds) completed with zero recoveries and contacts.
Two causes were found: a TCP endpoint backlog that fed Nav2 stale state, and a
tf2/tf2_ros version mismatch that deadlocked Nav2's TF listener. See the
[reliability result](LONG_NAVIGATION_RELIABILITY_RESULT_2026-10-28.md). That
player is not a clean-source build, and pedestrian scenes were not retested
with these changes. The 80 encounter cases use controlled stepping at Unity
`3033ba1`. All robot conditions, including oblivious motion, had zero contacts,
and the declared clearance-benefit threshold was not met in the aisle. This is a
development baseline, not a release or a validated controller benchmark.

**Step 3 visual check (October 28).** On the same stack, the 80 encounter
cases and the three-heading sensor fixture pass again, and a visible Warehouse
run passes all three routes. With the 65-person `Random` scenario, rendering and
transport stay healthy but Nav2 completes only 3 of 9 routes, with two contacts.
The release Warehouse has no camera-switching control. See the
[visual result](VISUAL_EXPERIENCE_RESULT_2026-10-28.md).

The earlier [single-person pedestrian result](PEDESTRIAN_AVOIDANCE_RESULT_2026-10-28.md)
passes 60 open-floor checks and explains ColliderV1's body geometry, braking and
sidestepping corrections. The new milestone preserves that model and repairs
laser free-space reporting/costmap clearing. Historical
[longer-navigation](LONG_NAVIGATION_RESULT_2026-10-27.md),
[transport](TRANSPORT_RESULT_2026-10-27.md),
[rendered-sensor](RENDERED_SENSOR_RESULT_2026-10-27.md),
[placement](PLACEMENT_RESULT_2026-10-27.md) and
[clean-build](CLEAN_BUILD_RESULT_2026-10-27.md) reports retain their own source pins
and coverage. Their successful results must not be attributed to every later
candidate. See [VALIDATION.md](VALIDATION.md) for the validation history.

The next work is sustained-navigation diagnosis and a prospectively designed,
more discriminating encounter benchmark. Participant workflows, large crowds,
human realism and broad navigation reliability remain open. ORCA is unimplemented.
Review Michal's prototype and Howard's extensions before adding overlapping
sensor, learning or participant-study interfaces; they are not dependencies of
the autonomous fixture above.

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

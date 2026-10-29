# Long-route reliability result: October 28, 2026

The repaired Kuri Warehouse stack passes the prospective long-route campaign:
**12 of 12 sequences and 36 of 36 routes** (startup, task reset and scene reload
in each sequence). The sequences cover seeds 7 and 42 three times each, seed
1001, and five seeds not used before. Every route completed with zero Nav2
recoveries, zero recorded contacts and at most 0.059 s of receipt-lag growth.
No Nav2 process needed SIGTERM or SIGKILL at shutdown. See
[LONG_NAVIGATION_RELIABILITY.md](LONG_NAVIGATION_RELIABILITY.md) for the
diagnosis and the protocol, which was written before this campaign.

This is a bounded result: one machine, one static scene without pedestrians,
one robot and profile, and 36 routes. Even treating every route as independent,
the 95% upper bound on the per-route failure rate is about 8% (rule of three).
The repeated seeds behaved near-deterministically, so the effective sample is
smaller: 24 distinct routes, giving a bound near 12%. It does not establish
long-run reliability, cross-machine behavior or performance with pedestrians.

## Two causes and their repairs

1. **Endpoint backlog.** Unity sent 10 single-transform `/tf` messages per
   frame. The Python TCP endpoint saturated one core, and Unity-to-ROS data
   queued for up to 25 s. Nav2 then steered from state that was seconds old.
   Unity `1fec526` sends each frame's transforms as one message. Endpoint CPU
   fell from about 105% to 42%.
2. **TF listener deadlock.** The ROS image paired `ros-humble-tf2` 0.25.22 with
   `ros-humble-tf2-ros` 0.25.24, an ABBA lock-order combination that upstream
   fixed in 0.25.24 of both packages. Stacks captured from a frozen
   `controller_server` show the two blocked threads. Nav2 then used a frozen
   pose silently. The derived image `localhost/sean3-humble:tf2-0.25.24`
   upgrades only tf2.

Earlier failures with the historical player are consistent with cause 1: they
ran at simulation/wall ratios of 0.906 to 0.966. Accepted historical routes ran
at 0.992 or higher. Cause 2 was present in the image throughout. It appeared in
no earlier session's logs and became frequent after batching. One earlier
failure (candidate13 scene route, ratio 0.993) is not specifically explained.

## Sources and environment

- Unity `1fec526` on `feature/unity-2022-upgrade` (TF batching on `3033ba1`).
  The player `builds/long-reliability-c01-20261028/sean.x86_64` (SHA-256
  `0bfe5132...`) was built from the existing project at `3033ba1` plus a
  working-tree diff identical to `1fec526`. That project also carries the
  pre-existing Rocketbox metadata changes, so this is **not** a clean-source
  build. All 175 payload hashes verified after the campaign.
- ROS `cceff5b` unchanged; Kuri profile SHA-256 `37b17375...`.
- Coordination tooling `e6320a2`: receipt-lag gate and post-shutdown reset
  anchor. The executed checker files match that commit byte for byte.
- Image `localhost/sean3-humble:tf2-0.25.24`, ID `360d1c5b...`, built by
  `docker/Dockerfile.humble-tf2` from the recorded `:dev` image (`1f928d87...`).
  tf2 and tf2_ros are both 0.25.24. Overlay workspace `ros_ws_tf2`.
- Unity 2022.3.62f3, Linux x86_64 on robovision; ROS 2 Humble / Ubuntu 22.04.

## Campaign q02

| Measure | Range over 36 routes |
| --- | --- |
| Action status | 4 (SUCCEEDED) on every route |
| Final goal error | 0.314 to 0.342 m (limit 0.4 m) |
| Wall time | 15.6 to 173.2 s (limit 300 s) |
| Receipt-lag growth | 0.002 to 0.059 s (limit 1.0 s) |
| Longest 0.05 m translation pause | 0.4 to 2.0 s (limit 20 s) |
| Longest 0.5 m confinement | 2.0 to 4.2 s (limit 15 s) |
| Maximum odometry sample gap | 0.2 s (limit 1 s) |
| Recoveries / contacts | 0 / 0 |

Reset clock checks passed in all 24 resets: simulation minus wall interval was
between -0.20 and +0.07 s. All twelve runners exited zero with clean transport
and process exits. Repeated seed-7 and seed-42 sequences reproduced their route
times within 0.6 s, so those repeats are near-deterministic rather than
independent samples.

## Regression checks on the new image

| Check | Result |
| --- | --- |
| Unity EditMode (includes the new batching test) | 46 passed |
| Python harness regressions (includes the new lag test) | 54 passed |
| Endpoint compatibility tests | 12 passed |
| Nav2 lifecycle and command routing | Passed |
| Installed-costmap laser-clearing controls | 5 of 5 as expected, clean exits |
| Player payload hashes | 175 of 175 |

## Preserved attempts

All runs are under
`/scratch/tchauhan/sean3/validation/long-navigation-reliability-20261028/`, with
a local copy (bags excluded) in ignored `results/`.

| Run | Configuration | Outcome |
| --- | --- | --- |
| d01 | `3033ba1` player, old image, bag | Startup timeout, 13 recoveries; reset clock check failed. Backlog measured. |
| d02 | c01 player, old image, old checker, bag | Startup and task passed with 0 recoveries; scene reset failed on the stale anchor after a 15 s planner shutdown. |
| d03 | c01, old image, bag | 3 of 3 passed. |
| q01 | c01, old image, campaign | Stopped after 5 sequences: 2 passed, 3 failed; 10 of 15 routes passed. |
| d04, d05 | c01, old image, bag | Failed: TF freeze, robot struck an obstacle in d04. |
| g01 | c01, old image, ptrace diagnostic | Failed; deadlock stacks captured twice, 5 s apart. |
| q02 | c01, tf2-matched image | 12 of 12 passed (this result). |

The earlier long-route failures, the 80-case encounter qualification and its
revisions are unchanged and remain separate results. The encounter result
applies to Unity `3033ba1` and the old image; it was not rerun here.

## Remaining limitations

- The main `Dockerfile.humble` now requires matching tf2 versions, but a
  from-scratch rebuild has not been tested. A from-scratch build would also pull
  newer versions of other packages.
- Nav2 Humble's pose lookup has no age check. A future TF stall would again be
  silent to Nav2. The receipt-lag gate does not detect a stall inside a single
  ROS process.
- The c01 player is not a clean-source build; step 6 requires one.
- The Python endpoint still has finite throughput; heavier sensor or pedestrian
  traffic could recreate a backlog. The receipt-lag gate will report it.
- Pedestrian scenes, rendered sensors and frame-rate sensitivity were not
  retested with these changes.

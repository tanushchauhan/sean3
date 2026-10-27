# Connection lifecycle result — October 27, 2026

The bounded connection reload/shutdown milestone passes on robovision for the
configured Warehouse / None / RandomABNav / Jackal fixture. Across a headless
stress run, driving run, and NVIDIA rendered run, all twelve accepted endpoint
connections have matching announced closes and disconnects. Both processes exit
zero, no player is forcibly killed, and complete player/console/endpoint logs
contain zero transport failures, queue drops, native crashes, or display errors.

## Changes

Unity now retains and joins its connection worker on scene destruction or
application quit. Cancellation is captured before scheduling, the reader task
is retained, framing buffers belong to each reader, and EOF/truncation are
handled without a failing-reader loop. System-command serialization is protected
from concurrent callbacks. Publisher registration on reconnect writes to the
connected stream before queued data. The outgoing wait handle is disposed only
after worker completion.

For planned closure, Unity sends `__disconnect` after completed outgoing frames,
half-closes writes, and drains incoming TCP data until the endpoint closes its
write side. The endpoint detaches its active queue, wakes and joins the sender,
and only then closes the socket. It owns its listener and client threads and
waits for an old client before starting a replacement. Pending Unity-service
requests are released on disconnect. Unexpected EOF, truncated frames, forced
replacement, and real I/O failures remain observable and fail live acceptance.

The endpoint owns a two-thread ROS executor with bounded spin waits, enabling
clean SIGINT/SIGTERM handling even while idle. Its adapted upstream transport
license is included and installed. These changes live in the existing ROS
compatibility wrapper/module, without changing the pinned upstream repository.

Validation runners wait for the endpoint's post-bind ready log before starting
Unity. A forwarded host port can accept and reset a connection before the
process inside the container is listening. Shutdown keeps Xvfb and ROS alive
until Unity exits, then sends SIGINT to ROS launch, records process exits and
full logs, and removes the owned container. The checker now rejects transport
errors previously tolerated by historical results and also reads console-only
display diagnostics.

## Source and environment record

| Component | Accepted revision |
| --- | --- |
| Unity | `4e9371c7fb3c0344cce130f2ce5c11dea8c78b7b` |
| ROS integration | `bf0ea37a4f1eac53ae8a995d7a7d5276ecdc7712` |
| Rocketbox | `8aa27b9765284e01be88b1eed18ece55af5b7c5c` (unchanged) |

The Linux player was built 21:41:37–21:44:16 UTC from the existing cached checkout
at base HEAD `fa63861` plus these source changes. Its manifest records that base
and the tracked diff, not the later commit `4e9371c` as build-time HEAD. All three
Unity source/metadata files and all four ROS source/license/build files were
verified byte-for-byte against the accepted commits. The remote branches/index
were aligned afterward without replacing working files. All 175 player payload
hashes verified. This is an incremental build, not a new clean-source import.

Unity 2022.3.62f3 editor SHA256:
`1ab357c16a84816ec7d4399d174f1e40769964879fa813a5c1139f63349f1f96`.
Package manifest/lock hashes remain
`ae9c2b53760a9b9e0e17d7721ef6757ada6aff2082878551207e9284a5a36e97` and
`47744304bf01af280ab2f94f29f5a5913d231fa6d68ebac68ea0b99012a412ed`.
The existing `localhost/sean3-humble:dev` image, ROS overlay, and pinned endpoint
libraries were reused. Rendered operation used NVIDIA OpenGL via VirtualGL egl4.
Both paired component revisions are required for the new close command; an
unmodified upstream endpoint is not accepted by the clean-close checker.

## Accepted results

| Check | Result |
| --- | --- |
| Unity EditMode suite | 28 passed; zero failed/skipped/inconclusive |
| Python harness regressions | 16 passed |
| Endpoint compatibility/socket/process tests in the ROS image | 10 passed |
| Headless task resets / scene reloads | 6 / 6 passed |
| Headless connection / announced-close / disconnect counts | 7 / 7 / 7 |
| Graph counts after each headless transition | Stable single publishers and control subscribers in the checked topics |
| Headless clock regressions | 0 |
| Largest stationary drift in the twelve post-reset windows | 0 m measured |
| Largest positive player RSS / thread / FD growth after warm-up | 1,028 KiB / 0 / 0 |
| Largest positive endpoint RSS / thread / FD growth after warm-up | 168 KiB / 0 / 0 |
| Strict startup / task-reset / scene-reload driving | All three goals passed, no substitute placement resets |
| Driving connection / announced-close / disconnect counts | 2 / 2 / 2 |
| Rendered startup + twenty task resets + two scene reloads | All 23 placements and generated-goal global plans passed |
| Rendered connection / announced-close / disconnect counts | 3 / 3 / 3 |
| Rendered payload/calibration/timestamp analysis | Passed; 479 images decoded, zero failures |
| Process exits and forced player kills across all three runs | All player/endpoint exits 0; zero forced kills |
| Full-log transport, native-crash, and display-error counters | All zero |

Resource budgets remained the previously declared 128 MiB RSS, four threads,
and eight descriptors, measured after the first warm-up pair. The graph check
covers clock, odometry, laser, reset controls, and the velocity-command topic;
it is not an exhaustive assertion about every ROS topic or RPC interface.
The driving displacements were 0.6561, 0.6545, and 0.6547 m, with final errors
0.3439, 0.3455, and 0.3453 m against short one-metre goals. Longer generated
routes in the rendered sequence were planned, not driven.

The transport tests exercise a 128 KiB final-response drain, twenty immediate
Unity connect/cancel cycles, independent fragmented readers, null-terminated
topics, frame-boundary EOF versus truncation, and reconnect registration order.
Endpoint tests include twenty sessions under outgoing traffic, idle cleanup,
replacement ownership, malformed/abrupt disconnects, a service response and
pending-request cancellation, and actual subprocess exits on SIGINT and SIGTERM.
Injected faults deliberately remain visible in those tests. They are distinct
from the zero-error accepted live logs.

## Preserved failed attempts and remaining limits

Earlier attempts are retained separately and are unaccepted. They include:

- A fake-endpoint test that omitted the protocol's trailing-null handling, and
  a registration-order test that supplied MemoryStream to a NetworkStream API.
- Live registration ordering/serialization failures, corrected by direct stream
  registration and protected command serialization.
- An endpoint executor ownership mistake caught by real process tests; a strong
  owner and interruptible waits fixed process startup/exit.
- Startup resets caused by connecting to the forwarded port before endpoint
  readiness. The runner now waits for the post-bind message.
- A newly added NetworkStream write-timeout setting that produced failed writes,
  queue drops, and stalled sensors in these player runs. That setting was removed;
  the final candidate retains the original synchronous write behavior. The
  experiments do not establish a particular underlying Mono implementation bug.
- A run with passing reset functionality but initial connection/queue errors.
  The stricter full-log check correctly rejected it.

The accepted result covers expected transitions in the recorded local TCP and
ROS configuration. It does not certify sustained overload, arbitrary stalled
peers, all network-fault recovery, full RPC interoperability, GPU resource growth,
all scenes/robots/scenarios, long-task navigation, or participant workflows.
Unity reports failures if its two-second graceful drain or four-second join
expires; these bounds are not a general guarantee for an indefinitely blocked
synchronous write. Depth format, physical map accuracy, other task samplers,
controller comparisons, and ORCA remain as previously documented.

Existing unrelated local ROS metadata/submodule changes, the local review file,
remote Rocketbox metadata changes, generated UserSettings, and earlier crash
blobs were preserved. Validation processes and containers are removed after
accepted runs; older unrelated processes were not touched.

## Evidence and reproduction

See [TRANSPORT_LIFECYCLE.md](TRANSPORT_LIFECYCLE.md) for protocol ownership,
acceptance criteria, commands, and test coverage. Authoritative evidence:

- `/scratch/tchauhan/sean3/validation/transport/20261027-candidate9/`
- `/scratch/tchauhan/sean3/builds/transport-20261027-candidate9/`

The accepted directory contains full logs and exit states for `lifecycle/`,
`navigation/`, and `rendered/`, resource samples, source and payload verification,
unit-test results, captures and sensor analysis, and exact tooling snapshots.
Attempts `20261027-candidate1/` through `20261027-candidate8/` and their builds
remain separate. Local accepted evidence is under ignored
`results/transport-20261027/`. The earlier clean-source, sensor, and placement
reports remain historical evidence for their own revisions.

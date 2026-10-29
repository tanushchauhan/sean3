# Clean-source build review, October 27, 2026

## Outcome

**Accepted for the configured Warehouse build and smoke-test fixture.** The
corrected candidate built from a fresh committed checkout, verified all 175
payload hashes, passed all 12 EditMode tests (the existing 11 plus one importer
regression), and passed startup, task reset, and scene reload navigation.
Rocketbox callback exceptions fell from 544 in the first resumed run to zero.
Remaining diagnostics are classified below; unused legacy prefab errors and
unvalidated rendering/animation paths remain open.

The scope is a Linux Warehouse player under the recorded existing environment,
with pedestrian behavior `None`, task `RandomABNav`, seed 7, and external goals.
It is not an end-to-end simulator release or a claim that every imported asset,
scene, rendering path, or pedestrian behavior works.

## Source and environment

| Input | First resumed run | Corrected candidate |
| --- | --- | --- |
| Unity | `3e5f863a37f4f8139692f2e896c78dc715443142` | `7ae54bab2297bc263e0bb22fbd9dac8035f376df` |
| Rocketbox | `9e1048a2010826fd02b7996d650029cf83d25de5` | `8aa27b9765284e01be88b1eed18ece55af5b7c5c` |
| ROS | `2ac78a303d323fbce0caad83555dbe940cc40435` | Unchanged |
| Build/check tooling | coordination commit `14a56c2`, scripts from `2559138` | Unchanged |

The original candidate added only `RosPublishExtensions.cs.meta`, retaining its
previously generated GUID. The corrected candidate changes the Rocketbox URL
and gitlink and adds one EditMode regression. The third-party fix is three
added lines replacing one line: find `Bip01`, return when absent, then find its
pelvis. Models with the expected skeleton retain their existing processing.

The user approved creating the personal
[Rocketbox fork](https://github.com/tanushchauhan/Microsoft-Rocketbox).
The [fix](https://github.com/tanushchauhan/Microsoft-Rocketbox/commit/8aa27b9765284e01be88b1eed18ece55af5b7c5c)
is on `fix/unity-import-null-skeleton`. The original upstream repository is
[yale-img/Microsoft-Rocketbox](https://github.com/yale-img/Microsoft-Rocketbox).
Its pinned callback ran on all project models and dereferenced a missing
`Bip01` at line 44, including for Warehouse geometry and the Jackal model.

Recorded environment:

- Host: robovision, Linux `7.0.0-28-generic`, x86_64.
- Unity: `2022.3.62f3`, executable SHA-256
  `1ab357c16a84816ec7d4399d174f1e40769964879fa813a5c1139f63349f1f96`.
- Editor: `/scratch/tchauhan/sean3/unity/unity-2022.3.62f3/Editor/Unity`;
  installed Linux build support recorded in `unity.txt`.
- Existing ROS image: `localhost/sean3-humble:dev`, ID
  `sha256:1f928d87cafe30ae9feb382a107a1e559d35f19ddc448a2f21fb0b42f59cb8da`.
- Package manifest SHA-256:
  `ae9c2b53760a9b9e0e17d7721ef6757ada6aff2082878551207e9284a5a36e97`.
- Package lock SHA-256:
  `47744304bf01af280ab2f94f29f5a5913d231fa6d68ebac68ea0b99012a412ed`.

The build runner hashes remain:

- `build_unity_player.sh`: `3d33e97a3d2a9500d16218fb8bb1f83857cf18e4e6b3d9f39a8bc7dce29eca29`.
- `clean_build_unity_player.sh`: `18340dbe3a129c90f905dc50fd4a3b91aa295fabdfac7fe7f427fe8e9aabbd13`.
- `test_build_provenance.sh`: `fdd582630e8409546affa0d5716e0f8127d59c6907393b8abf27587b7b5fadf0`.

## First resumed run

Remote evidence: `/scratch/tchauhan/sean3/validation/clean-source/20261027T182807Z/`.
Remote output: `/scratch/tchauhan/sean3/builds/clean-source-20261027T182807Z/`.

| Check | Result |
| --- | --- |
| Fresh committed checkout, clean recursive submodule, no Library/UserSettings | Passed |
| Build provenance regressions / Python harness | Passed / 14 passed |
| Unity build, 18:29:41-18:36:24 UTC | Exit 0; `Build Finished, Result: Success.` |
| Linux executable / payload verification | Present and executable / all 175 hashes matched |
| EditMode suite | 11 passed; XML checked; exit 0 |
| Startup / task reset / scene reload navigation | All passed; runner exit 0 |
| Import acceptance | Failed: 544 Rocketbox callback exceptions |

Player SHA-256:
`0bfe51325720c950b4ad75ce7c3b65595fd7e939908520ec33600919919327a8`.
This small executable's hash alone is not the player identity; the data and
runtime files are covered separately by `player-tree.sha256`.

| Navigation stage | Displacement | Goal error |
| --- | --- | --- |
| Startup | 0.651 m | 0.349 m |
| Task reset | 0.653 m | 0.347 m |
| Scene reload | 0.653 m | 0.347 m |

One initial placement was rejected. All stages received fresh sensors. The
clock advanced 1.290 s at task reset and 3.610 s at scene reload; the existing
runner detected no regression. These are selected clear-path smoke tests.

## Accepted corrected-source run

Remote evidence: `/scratch/tchauhan/sean3/validation/clean-source/20261027T184537Z/`.
Remote output: `/scratch/tchauhan/sean3/builds/clean-source-20261027T184537Z/`.

| Check | Result |
| --- | --- |
| Fresh checkout / recursive submodule | Clean, pinned to `7ae54ba` / `8aa27b9` |
| Library / UserSettings before import | Both absent |
| Build provenance regressions / Python harness | Passed / 14 passed |
| Unity build, 18:47:26-18:53:42 UTC | Exit 0; `Build Finished, Result: Success.` |
| Linux player / payload verification | Executable present / all 175 hashes matched |
| Rocketbox callback exceptions / C# compilation errors | 0 / 0 observed |
| EditMode XML | 12 passed, 0 failed/skipped/inconclusive; editor and XML-check exit 0 |
| Three-stage navigation JSON | `passed: true`; runner exit 0 |

The executable SHA-256 remains
`0bfe51325720c950b4ad75ce7c3b65595fd7e939908520ec33600919919327a8`.
The SHA-256 of the complete `player-tree.sha256` inventory is
`550ea3e1c8712407cf127f516600b97ff8cfeefce6774bc24f281e8d7b00564f`.
Matching executable stubs do not establish identical player payloads or
bit-for-bit reproducibility.

| Navigation stage | Displacement | Goal error |
| --- | --- | --- |
| Startup | 0.653 m | 0.347 m |
| Task reset | 0.655 m | 0.345 m |
| Scene reload | 0.653 m | 0.347 m |

One startup placement was rejected. All three stages received fresh sensors;
clock advances were 1.190 s for task reset and 3.630 s for scene reload, with no
regression detected. DDS stayed inside the container; only the TCP endpoint
was exposed on `127.0.0.1:10321`. Unity jobs and overlay builds ran serially.

The complete corrected log was reviewed: the other diagnostic counts below
match the first resumed run, but there are no Rocketbox callback exceptions.
The two broken legacy prefabs are outside the statically traversed
LoadingScene/Warehouse dependencies. No missing script references were found
in that traversal or as runtime missing-reference failures in the navigation
fixture. This supports acceptance of this fixture, not all scenes or assets.

The same four metadata files and generated Search settings changed after
import. GUIDs and package manifest/lock hashes remained unchanged. Source
status after functional checks matches the reviewed generated changes.

The initial functional launcher read its run pointer before it was written and
waited without invoking Unity. It was stopped and corrected to wait before
reading the pointer, then the functional checks ran once. The initial launch
log, correction note, and final launcher are retained with the evidence. The
build and checkout were not altered by this orchestration correction.

## Import diagnostics and metadata

The complete build log, not merely its successful final line, was reviewed.
`import-diagnostics.json` records categorized, line-numbered messages; counts
are log occurrences, including repeated compiler output, not unique defects.
The first resumed run contained:

| Diagnostic | Occurrences | Assessment |
| --- | --- | --- |
| Rocketbox model callback null reference | 544 | Blocks acceptance; includes required model imports; eliminated by the corrected pin in the accepted fresh run. |
| Rig / animation import warnings | 417 | Existing animation assets; animation fidelity and pedestrian behaviors are unvalidated. |
| FBX blendshape normals warnings | 6 | Missing smoothing groups; visual quality remains unvalidated. |
| URDF required-component warnings | 51 | Editor import components; navigation smoke tests do not establish robot-model fidelity. |
| Missing serialized scripts | 36 | Legacy resource prefabs; static Warehouse/LoadingScene dependency traversal found no unresolved script GUIDs. This does not validate all resource or runtime string loads. |
| Broken prefabs | 2 | `HotelEnvironment.prefab` lacks its nested Hotel prefab; `GlobalPath Variant.prefab` lacks its parent. Neither is in the static LoadingScene/Warehouse dependency traversal. Hotel and legacy path visualization remain unvalidated. |
| C# warnings | 231 | Member hiding, obsolete APIs, unreachable/unused code, null comparison and compiler language-name warnings; no C# compilation error observed. |
| Shader warnings | 9 | Legacy renderer pragmas and integer division; no rendered-camera claim. |
| Shader mixed line endings | 2 | LightShafts sources; no source rewrite made. |
| NuGet editor assembly load failure | 2 | DLL filename/assembly-name capitalization mismatch; editor package-management functionality is unvalidated. Player build and the test assembly completed. |

The log also records three licensing errors followed by successful entitlement
resolution, two GTK assertion messages, and an editor HTTP REST port error.
They did not prevent this batch build or EditMode tests; this does not validate
those optional editor services.

Static GUID traversal found no duplicate GUIDs or unresolved script references
for LoadingScene and Warehouse. It found eight unresolved animation GUIDs in
Social Force controllers; it excludes binary references and runtime string
loads. `None` pedestrian behavior is the tested fixture, so broader Warehouse
animation and pedestrian claims remain excluded.

Both fresh imports changed four Rocketbox child FBX `.meta` files: Female_Child_01,
Female_Child_02, Male_Child_01, and Male_Child_02. Each advances importer
serialization from 19301 to 22200 and adds newer importer fields. The full diff
is saved as `rocketbox-import.diff`; **no GUID changed**. Unity also generated
`UserSettings/Search.settings`. Package manifest and lock hashes stayed equal
before/after both builds. Generated changes were not copied back into the
committed source. The existing source checkout's older metadata diff was
compared byte-for-byte before and after advancing the guarded importer.

The missing-meta inventory includes hidden NuGet signatures, submodule Git
administration files, and Maya swatches. It is an inventory, not proof that
these files are Unity assets requiring new committed metadata.

## Functional limits and retained failures

The first player's log contains headless unsupported-shader diagnostics, one
connection-reset-by-peer write, and an X server interruption during process
cleanup. The endpoint log contains two EOF errors and one bad file descriptor.
The corrected player's log still contains one reset-by-peer write and two
endpoint EOF errors, with no bad-file-descriptor message observed. Transport
teardown remains unclean and was not changed. Resource growth and
the six-pair lifecycle stress check were not rerun for this candidate.

The interrupted `20261027T002705Z` attempt remains intact. Its manifest stayed
`status: building`, its outer wrapper returned 143, and a player was eventually
written during shutdown. It is not accepted as a completed build. The first
resumed run and the corrected-source run use separate new directories.

## Resume and evidence

The current resume point is the accepted corrected-source output at
`20261027T184537Z`, pinned in `sean3-candidate.repos`. Keep all three attempts
and their manifests. To repeat this milestone, use the commands in
[clean-build protocol](../protocols/clean-build.md) and another new output directory, then run the
12-case `SEAN.Editor.Tests` assembly and the existing three-stage navigation
runner. Further work on unused prefabs, rendering, animation, or transport
requires separate validation; do not relabel those as covered here.

The fix branch in the personal Rocketbox fork is pushed. Unity and coordination
changes use their existing `feature/unity-2022-upgrade` and
`feature/ros2-environment` branches. ROS remains at its previous pin.
`resume-state.txt` in the accepted remote evidence records final branch heads.

Evidence includes host/editor/image records, exact tooling and candidate
snapshots, clean checkout state, source/submodule diffs before and after import,
package hashes, complete build logs, build exit records, payload checksums,
EditMode XML, and navigation JSON/logs. Supporting review scripts are preserved
with hashes; their static dependency traversal is supplementary evidence.

Rendering, participant controls/recording/replay, immutable container rebuilding,
all-asset import correctness, deterministic trajectories, and navigation
performance remain unvalidated. ORCA, GDC, and STEPS work remain deferred.

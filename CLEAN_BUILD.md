# Clean-source Unity player build

## Scope and result

This check asks whether a fresh checkout of the committed Unity source imports
in Unity 2022.3.62f3 and produces a Linux x86_64 player in the existing
recorded environment. It does not rebuild or freeze the ROS container image,
validate camera rendering, or establish bit-for-bit reproducibility. Unity may
create editor metadata during import; preserve and report those changes rather
than folding them into the pinned source silently.

**Status: interrupted; not completed.** The remote Unity import/build was
stopped at the user's request before its outcome was recorded. Do not treat
this as a successful clean build. Resume by inspecting
`/scratch/tchauhan/sean3/builds/clean-source-20261027T002705Z` and its linked
validation record at
`/scratch/tchauhan/sean3/validation/clean-source/20261027T002705Z` before
deciding what evidence can be recovered. Preserve this interrupted output; any
resumed build must use a new output directory. The source revision is
`3e5f863a37f4f8139692f2e896c78dc715443142`; the runner is recorded in commit
`2559138`.

## Procedure

Run from the `sean3` repository on the recorded Linux build host. The output
directory must not already exist. The script checks that the source checkout's
HEAD matches the expected commit, records its dirty state without copying dirty
files, clones that commit into `output/project`, and initializes recursive
submodules from the matching local source checkout. It verifies the clone and
submodules are clean and pinned, and have no Unity `Library` or `UserSettings`
before import. The lower-level build writes the player and evidence to
`output/build`:

```sh
scripts/clean_build_unity_player.sh \
  /path/to/2022.3.62f3/Editor/Unity \
  /path/to/social_sim_unity \
  3e5f863a37f4f8139692f2e896c78dc715443142 \
  /scratch/tchauhan/sean3/builds/clean-source-<run-id>
```

The commit above is the current Unity revision in `sean3-candidate.repos`;
confirm it still matches the intended candidate before running. Choose a unique
run ID and do not create the output path beforehand. Do not edit source,
metadata, package pins, or Unity settings in the fresh output checkout before
building. Keep the original source checkout and editor state untouched.

The runner is recorded in `sean3` commit `2559138`. It retains source-origin
status/diffs, the clean checkout record, before/after recursive status and
diffs, missing `.meta` inventories, Unity editor version and executable hash,
package manifest and lock hashes, build command and status,
full `build.log`, player hash, and `player-tree.sha256`. The remote environment
snapshot is under
`/scratch/tchauhan/sean3/validation/clean-source/20261027T002705Z/` (`host.txt`,
`unity.txt`, `container.txt`, and `checkouts.txt`). Review import output and
every source change, including `.meta` files, before accepting the result.

## Acceptance

- The script confirms the expected commit, initialized pinned submodules, no
  pre-existing Unity `Library` or `UserSettings`, and a clean recursive checkout.
- Unity exits successfully, writes an executable Linux player at the recorded
  output path, and the complete log has no unresolved import or player build
  errors affecting the configured Warehouse player or its required assets.
  Import warnings are captured and classified; relevant warnings are
  investigated and recorded. A headless build does not establish that unused
  scenes or every imported asset are correct.
- Any post-import source changes are explained and preserved as evidence. They
  are not silently copied back to the pinned component source.
- Source/environment provenance and all result artifacts are reviewed
  together. A successful editor launch without a player and complete log is
  insufficient.

The build result is separate from functional validation. Run the existing
11-test Unity EditMode suite and three-stage live navigation check against the
freshly built player, then link their reports to the build record. These checks
cover specific behavior; they do not validate rendered camera images,
participant workflows, or all assets.

If the check fails, retain the output directory and diagnostics. Do not repair
the fresh checkout in place and rerun it as though it were the original clean
attempt. Use a separate new output path for a changed source or environment.

## Limits

This check uses an already installed Unity editor and host environment. It does
not freeze apt or base-image inputs, prove all third-party asset terms, or
establish identical output across machines or repeated builds. It does not
validate rendered camera images, participant controls, recording/replay, or
live ROS navigation. Those remain separate checks.

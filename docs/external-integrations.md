# External perception and navigation integrations

The launcher supplies a simulator/ROS baseline. Experimental RGB-D perception,
pedestrian maps, memory policies and alternative navigation stacks can remain
in their research repository while reusing its player, transport and validation.
The [outside-in-social-nav project](https://github.com/tanushchauhan/outside-in-social-nav)
uses this arrangement under `experiments/sensing_dwa/` and `src/oisn/navigation/`.
Its development findings are separate from SEAN controller qualification.

## Start without an automatic robot policy

```sh
./sean3 run --no-nav2 --scenario Random --seed 7 --logs /absolute/host/run-logs
```

`--no-nav2` skips both the built-in Nav2 launch and the task driver. The external
wrapper owns its navigation stack, readiness gate, driver and artifact lifecycle.
Use an isolated free TCP port and a new result directory. Keep one final robot
velocity owner; do not start the validated Pure Pursuit stack alongside another
policy writing the same final command topic.

The launcher exposes only its validated `None` and `Random` scenarios. The
research integration reported that a tested player rejected the advertised
`HandcraftedSocialSituations` value. Source assets contain inconsistent singular
and plural handcrafted names, so their presence alone does not establish a
player capability. The unsupported launcher advertisement was removed. Other
scenarios require explicit capability/runtime qualification before exposure.

## Readiness is observation state, not detection count

An external perception wrapper should release its task driver only after a
fresh **successful** observation. A successfully processed frame with zero
people is a valid observation. Never-received, failed, missing and expired
observations must remain distinguishable from an empty successful detection.
Retain observation timestamps, validity and the gate's release reason in logs.

There is currently no generic readiness-hook option in `./sean3`; the research
wrapper owns this gate. Adding a shared hook should preserve the existing
default startup path and receive its own missing/expired/valid-empty tests.

## Preserve artifacts before ephemeral-container cleanup

The launcher stops helpers, the player and its ROS container, then removes the
container. `--logs` captures launcher-owned logs; it does not automatically
discover or export an external application's files inside that container.

Prefer a dedicated host-mounted results directory for external processes so
artifacts survive removal. Otherwise, the owning wrapper must copy and verify
its artifacts **before** allowing launcher/container cleanup to proceed. Stop
the external task driver and navigation stack with bounded waits, save partial
results even after failure, then release player/endpoint/container cleanup.
Do not wait for an already-removed container to supply research logs. The
launcher has no generic external-process shutdown-hook API at present.

Do not stop unrelated services or reuse another experiment's occupied port.
Retain process exits, forced-stop indicators and cleanup results alongside the
behavioral metrics.

## Performance and policy scope

The research integration reports useful development improvements from limiting
BLAS/OpenMP thread pools in its Python workers and publishing occupancy grids
as signed-byte arrays rather than Python lists. Apply and measure those settings
in the research worker, with its chosen libraries and CPU allocation. They are
not simulator-wide environment defaults.

Its DWB development traces support further testing, not controller qualification.
A lower chosen controller rate and remaining deadline warnings should be
reported with observation ages, exceptions, motion/contact outcomes and hardware
load. The validated SEAN Kuri Pure Pursuit default is unchanged. Keep DWB tuning,
sensing interventions, pedestrian-memory policies and their evaluation protocols
in the research repository.

# Python 02 setup

The owner selected [research result a83ffe21-90eb-4674-99e3-7c80d6871a6c](http://192.168.51.10:8877/exit/results/a83ffe21-90eb-4674-99e3-7c80d6871a6c)
on 27 November 2026. This adds an independent experiment under the existing
[practice trading rules](../PROJECT_BRIEF.md); it does not change those rules.
Current completion and verification belong in [project status](STATUS.md#python-02).

| Binding | Selection |
| --- | --- |
| Display name | Python 02 |
| Controller | `practice-b` |
| Notebook | `notebook-b` |
| Strategy | `drm_adaptive_bandpass_v1` |
| C1 | Distributional Rank Momentum \| NAL |
| C1 events | Long on `BullishFlip`; Short on `BearishFlip` |
| Exit | [blackcat] L2 Ehlers Adaptive BandPass Filter |
| Exit events | `doLongExit` closes shorts; `doShortExit` closes longs |
| Account | Owner's native v20 AUD practice account named Python 2, ending 003 |
| Division | OANDA Australia Pty Ltd, confirmed by the owner in this chat |
| Private connection prefix | `PRACTICE_B` |

The [registry entry](../deploy/python02-experiment.toml) is installed in production.
The [manifest](../strategies/drm_adaptive_bandpass_v1/manifest.json) owns all
indicator defaults, signal bindings, source identities and the qualified history
window. Its hash is saved in the separate notebook. The account ID and token
remain private; the screenshot balance is not a notebook baseline.

## Implementation boundary

Both saved indicator conversions are copied with only their import paths changed.
The registered Pine compatibility dependency is copied exactly. Sizing retains
the previously qualified lab ATR(14) simple average; the Exit indicator's internal
ATR is part of that indicator and does not replace trade-sizing ATR.

The saved conversions are evaluated on the practice run's current partial candle,
as specified in the brief. The lab's completed-input confirmation flags and
accepted Exit direction mapping are retained. Internal indicator position states
are calculation inputs, not claims about actual OANDA trades.

[Explicit strategy selection](../nnfx_practice/strategy.py) validates each binding
against one packaged manifest and its exact candle count. Management, entry,
lifecycle and qualification use that binding. There is no automatic selection,
default fallback, runtime import from the lab checkout or shared notebook.
Python 01's strategy files and immutable manifest remain unchanged.

## Verification and deployment order

1. Compare packaged calculations with the archived result and original lab code,
   including rolling windows, modified partial candles and sizing ATR. Run the
   independent-account and existing trading regression checks.
2. Read the intended practice account with the private connection. Confirm its
   identity, currency, division, empty starting state, instrument metadata and
   conversion factors. The owner has confirmed the division; this is separate
   from the API observations.
3. Deploy under administrator-controlled maintenance. Preserve Python 01's
   notebook, Q0, open trades, claims and timers. The registry and application are
   shared, so update its protected code/configuration identities only with fresh
   matching host-control verification. The old Python 01-only installer and M10
   migration are not suitable for adding this experiment.
4. Install the private connection and strategy manifest, create the native
   notebook with the service identity, and verify reader isolation and both
   controller service instances. Restart the observational dashboard to load the
   expanded registry.
5. Collect Python 02's own 28-pair candle coverage at a weekday 16:50 New York
   launch. A daytime candle read does not satisfy this requirement. Initialize
   Python 02's Q0 through the existing
   guarded lifecycle using a fresh broker snapshot. Review and seal its own
   account/strategy authority and automatic qualification plan before scheduling.

The [scoped installer](../deploy/add_python02.py) implements the deployment and
records a receipt. It requires the captured protected-plan identity, unchanged
Python 01 configuration, a distinct verified account, the matching wheel and
passing application/setup checks. It refreshes the actual system-control
fixtures, verifies preservation of Python 01 files and restores its prior
qualification timer. A failure during shared-code maintenance leaves that timer
stopped for explicit investigation; do not blindly rerun the installer.

The installed [one-time setup job](../deploy/python02_bootstrap.py) captures
Python 02's 28-pair candle evidence as the native writer at the next weekday
16:50 New York window. Only a passed, matching capture with a clear account can
proceed through the existing guarded Q0 initialization. It then enables the
unchanged weekday qualification schedule, with first dispatch set to the next
weekday. It never invokes a trading run in the capture window. A retained
exclusive receipt prevents a failed or interrupted setup from replaying.

For the completed 27 November installation, the capture is **28 November at
08:50 Melbourne**. If all prerequisites pass, the first regular qualification
run is **1 December at 08:50 Melbourne**. Those are scheduled intentions until
the corresponding reports and notebook evidence exist. Ordinary activation is
not enabled by this setup.

The existing login has only the scoped dashboard-deploy sudo grant. It cannot
install trading code, modify protected qualification plans or initialize the
production notebook. Development preparation and actual deployment must be
reported separately. The owner completed the read-only protected-host export
and ran this administrator installation command on 27 November:

```sh
sudo python3 /mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/release/deploy/add_python02.py
```

The installation succeeded; **do not rerun it**. The owner also restarted
`nnfx-practice-dashboard.service` to load Python 02. The source installer now
includes that restart; the frozen USB release retains the exact executed version.
Current observed completion belongs in [status](STATUS.md#python-02).

All new development data and evidence live under
`/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/`. The source branch
uses the existing checkout, so no new worktree was created. Existing unrelated
documentation edits were preserved.

To reproduce the archived comparison, use the lab's environment for its validation
dependencies, with the practice checkout as the current directory and temporary
files on USB:

```sh
PYTHONDONTWRITEBYTECODE=1 \
TMPDIR=/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/tmp \
/home/codexdev/projects/nnfx-indicator-lab/.venv/bin/python \
  -m tests.check_python02_reference \
  --lab /home/codexdev/projects/nnfx-indicator-lab \
  --count 512 \
  --output /mnt/nnfx-usb/development/data/nnfx-practice-lab/python-02/evidence/reference-512-repeat.json
```

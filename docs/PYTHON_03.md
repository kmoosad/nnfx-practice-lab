# Python 03 setup

The owner selected [research result 18771091-9f76-4daf-bee9-a23f28634bae](http://192.168.51.10:8877/exit/results/18771091-9f76-4daf-bee9-a23f28634bae)
on 27 November 2026. This is an independent experiment under the existing
[practice trading rules](../PROJECT_BRIEF.md). No trading criteria changed.

| Binding | Selection |
| --- | --- |
| Display name | Python 03 |
| Controller | `practice-c` |
| Notebook | `notebook-c` |
| Strategy | `eye_age_supertrend_v1` |
| C1 | Eye Trend Zones [EyeAlgo] |
| C1 events | Long on `confluence_buy`; Short on `confluence_sell` |
| Exit | Age Adaptive Supertrend |
| Exit events | `buySignal` closes shorts; `sellSignal` closes longs |
| Account | Owner's native v20 AUD practice account named Python 3, ending 002 |
| Division | OANDA Australia Pty Ltd; the owner confirmed existing OANDA details continue |
| Private connection prefix | `PRACTICE_C` |

The [registry entry](../deploy/python03-experiment.toml) was installed on
27 November 2026. Its controller and notebook are visible on the live dashboard.
The [provenance record](../strategies/eye_age_supertrend_v1/provenance.json) retains
the exact selected sources, rules, parameters and dependency identities. Account
ID and token are in private USB configuration, outside version control. The
screenshot balance is not an initialized notebook baseline.

## Calculation boundary

The saved conversions are copied with import-path changes only. Each role uses
its own exact registered Pine compatibility version: C1's older dependency and
Exit's newer dependency are separate. Sizing uses the existing lab ATR(14) simple
average. The indicators' internal ATR calculations do not replace sizing ATR.

The selected C1 uses the confluence events, not its other plain BUY/SELL rule.
The saved conversion evaluates its completed-input confirmation flags on the
practice run's partial candle, as specified by the brief. Exit regime and trend
duration statistics are indicator calculations, not broker positions.

Age Adaptive Supertrend accumulates trend-duration statistics from earlier
history. The owner authorized history support after unanchored rolling windows,
including 5,000 candles, failed to preserve an Exit event. The manifest pins
**1 January 2013 at 22:00 UTC**, the first candle in the selected research dataset.
Every run requests **5,000 raw daily candles**, then initializes C1, Exit and
sizing ATR from the weekday history starting at that fixed origin. Completed
Friday/Saturday-start candles are excluded. This exactly reproduces all 2,072
research dates and OHLC values per pair from the retained OANDA history.

The capture records the received count, origin, retained indicator count and
excluded non-session count. The current partial candle keeps its existing strict
session validation. The underlying conversions, parameters and ATR formula are
unchanged; this is an explicit initialization/data-history policy.

The origin must remain within every 5,000-candle request. If it is missing,
capture is unavailable; no silent truncation or restart is allowed. This provides
several years of present headroom, not unbounded history retention. Extending that
bound in future requires a separately qualified binding. No candle database,
schema migration or mutable indicator checkpoint is introduced.

## Verification and deployment order

1. Reproduce the archived outputs and sizing ATR with the original role-specific
   dependencies, then qualify the fixed-origin history and modified partial snapshots.
   Additional historical market-data samples are offline calculation evidence,
   not scheduled account qualification or broker execution evidence.
2. Verify the independent account and controller/notebook routing, existing
   experiments, signal mapping, entry/exit paths and qualification gates.
3. Prepare a scoped administrator installation that preserves both existing
   notebooks, Python 01's schedule and Python 02's pending setup. Shared code and
   registry changes require refreshed protected identities and host controls,
   including Python 02's setup context if it has not yet initialized.
4. After installation, capture Python 03's own 28-pair candle coverage at weekday
   16:50 New York. Only a passed matching capture and fresh clear account can
   proceed through guarded Q0 initialization and future qualification scheduling.

The old Python 02 installer assumes only one existing experiment and must not
be reused for Python 03. Current completion and evidence belong in
[project status](STATUS.md#python-03).

The [scoped installer](../deploy/add_python03.py) targets the inspected state:
Python 01 has its active qualification schedule, and Python 02 has an unattempted
setup job. It checks the protected plan/context, installed code, registry, private
bindings, verified package and offline checks before shared-code maintenance.
It locks both existing notebooks, temporarily stops their scheduling triggers,
refreshes native host controls, checks notebook/claim preservation, and restores
Python 01's schedule plus Python 02's unchanged setup units with an updated code
and registry reference. If Python 02 has already attempted setup, it stops before
deployment and requires a newly reviewed migration.

Python 03 receives its own empty native notebook and
[one-time setup job](../deploy/python03_bootstrap.py). That job captures its
scheduled candle evidence, initializes Q0 only after all prerequisites and a
fresh clear account pass, then enables future weekday qualification. It does not
trade during the capture window or enable ordinary activation. Failed or
interrupted setup retains an exclusive receipt and cannot automatically repeat.

The administrator exported the protected host identities with
[the read-only inspector](../deploy/inspect_python03_host.py), then installed the
corrected frozen USB release with this command (retained for the deployment record):

```sh
sudo python3 /mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/release/deploy/add_python03.py
```

**Installation is complete; do not rerun this command.** The first attempt stopped
before maintenance because the uninitialized Python 02 controller had no lock
file. The corrected installer creates that lock with native writer ownership;
the subsequent installation and native host checks passed. Both existing
notebooks and schedules were preserved.

Python 03's one-time check is scheduled for **28 November 2026 at 08:50
Melbourne**. Its starting balance (Q0) remains unset until that check and fresh
account validation pass. Successful setup enables the first possible regular
qualification run on **1 December at 08:50 Melbourne**. Ordinary activation
remains disabled. See [observed installation evidence](STATUS.md#verified-python-03-installation).

Development uses `codex/python-03` in the existing checkout. All new development
data, private configuration, notebooks and artifacts belong under
`/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/`. The mounted USB is
required; there is no internal-storage fallback.

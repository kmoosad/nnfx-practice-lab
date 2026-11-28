# Python 03 experiment

Owner selected [research result 18771091-9f76-4daf-bee9-a23f28634bae](http://192.168.51.10:8877/exit/results/18771091-9f76-4daf-bee9-a23f28634bae)
on 27 November 2026 under the existing [practice rules](../PROJECT_BRIEF.md).
This document owns selection, integration boundary and installation evidence;
[status](STATUS.md#python-03) owns current operation.

| Binding | Selection |
| --- | --- |
| Display / controller / notebook | Python 03 / `practice-c` / `notebook-c` |
| Strategy | `eye_age_supertrend_v1`, 5,000 raw candles with fixed origin |
| C1 | Eye Trend Zones: confluence_buy long / confluence_sell short |
| Exit | Age Adaptive Supertrend: buySignal closes shorts / sellSignal closes longs |
| Account / division | Native-v20 AUD Python 3 ending 002; owner confirmed existing OANDA Australia details continue |
| Private prefix | `PRACTICE_C` |

The [registry](../deploy/python03-experiment.toml), [manifest](../strategies/eye_age_supertrend_v1/manifest.json)
and [provenance](../strategies/eye_age_supertrend_v1/provenance.json) own exact source,
parameters, rules and dependency identities. Account/token stay in private
configuration; screenshot balance is not Q0.

## Calculation boundary

Copy saved conversions with import-path changes only. C1's older registered Pine
dependency and Exit's newer one are deliberately separate. Sizing uses lab simple
ATR(14); internal indicator ATR is separate. Use confluence events, not C1's plain
BUY/SELL rule. Retain saved confirmation flags on the practice partial candle;
regime/trend statistics are calculation state, not broker positions.

Rolling windows, including exhaustive 5,000, missed Exit events. Owner authorized
fixed-origin support while preserving selected calculations/trading rules. The
manifest pins **1 January 2013 22:00 UTC**, the research first candle. Each 5,000-raw-
candle capture initializes C1/Exit/ATR from that origin's weekday suffix, excluding
completed Friday/Saturday-start bars; current partial validation stays strict.
This reproduces all 2,072 archived dates/OHLC per pair. Record raw/retained/excluded
counts and origin. [History contract](../PROJECT_BRIEF.md#strategy-selection) owns
the rule; [comparison evidence](VERIFICATION.md#strategy-comparisons) retains failed
alternatives and 11,256 passing endpoints/156 partials.

Origin must remain available inside the window; missing origin fails capture,
never truncates/restarts. This is bounded headroom, not unlimited retention.
Extending the bound needs a separately qualified immutable binding. No schema
migration, candle database or mutable indicator checkpoint was introduced.

## Installation and setup boundary

The [scoped installer](../deploy/add_python03.py) was reviewed for Python 01's active
qualification and Python 02's **unattempted** setup. It validates protected plan/
context, code/registry/private bindings/package/checks, locks both notebooks,
stops their triggers, refreshes native controls and verifies records/claim
preservation. It restores original schedules with updated shared identities;
Python 02 helper/setup-unit bytes remain unchanged. The old Python 02 installer
cannot add Python 03. After Python 02 attempts setup this migration refuses and
requires new review; both setups have now completed.

[Bootstrap](../deploy/python03_bootstrap.py) captures its own scheduled 28-pair
partial-candle coverage and requires a fresh clear account before Q0/future
qualification. It never trades in that window or enables ordinary activation;
a failed/interrupted exclusive receipt prevents automatic repeat. Division is
owner evidence, separate from intended-account API observations.

## Recorded installation evidence

27 November 23:21 Melbourne [post-install verification](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/post-deployment.json)
matched all 72 application/resource files and code
`a345c96c4d7e6076299c7695d30f84b2f28cf26a13237a73ff1f7a8458185bc4`, five HTTP pages,
clean native fixtures and receipt `python03-337bdc27b2c1-deployment.json`.
[USB evidence](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence) retains
clear-account AUD preflight (50,000.9696), 42 application checks (431.407 s),
15 final history/deployment/bootstrap guards and the wheel check. Offline fixtures
are distinct from actual host checks and account reads.

The first administrator attempt stopped before maintenance for Python 02's
missing lock, creating only a protected backup. The [failure record](/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/evidence/pre-maintenance-lock-failure.json)
retains unchanged installed hashes/schedules. Correction creates a missing lock
with native ownership, preserves existing inodes and records lock-open failures;
real contention/invalid-lock guards passed. Successful installation preserved both
notebooks/claims/schedules and refreshed shared protected identities. No broker
requests, Q0 or trading run occurred during installation; Python 01 then had 16 rows.

Prepared development notebook integrity was ok with Q0/A0 unset; the earlier
`preliminary-prepared` notebook remains separate. Build tools/evidence stayed on
USB without dependency downloads. The retained root is
`/mnt/nnfx-usb/development/data/nnfx-practice-lab/python-03/`.

Setup **completed 28 November at 08:50 Melbourne**, with Q0 and qualification
scheduled for **1 December 08:50 Melbourne**, per the preserved
[observation](STATUS.md#python-02-and-python-03-scheduled-setup-verification).
Actual trading remains pending and ordinary activation disabled. Installation
and bootstrap are complete; do not rerun them.

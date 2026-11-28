# Project status

Updated 28 November 2026 (Melbourne). Latest trading/service observations below
are from 09:38–09:39 Melbourne that day. No new broker or service checks were
performed for this documentation cleanup.

## Current position

The checkout is on `main` with Python 01–03 implementation, schema-3 transaction
comparison, the single-table journal and guarded qualification/ordinary adapters.
All three experiments are installed. Automatic **qualification** is enabled under
its existing authority; **ordinary activation is unset and ordinary scheduling
is disabled** in the latest recorded observations. These are the installed mode
labels; the existing schedule continues. **M10 was removed by the owner on
28 November**, following about a week of practice operation with trades resolved;
see the [accepted operating decision](../PROJECT_BRIEF.md#delivery-sequence).

| Delivery | State and evidence boundary |
| --- | --- |
| Brief / architecture / design / plan | Brief final 10 November; architecture decisions 15 November; design and plan approved 16 November. No repeated stage approval is needed. |
| M01–M09 delivery history | Implementation and host-control results are retained in [dated verification](VERIFICATION.md#approved-decisions-and-offline-milestones), with their evidence limits. No milestone review is queued. |
| Dashboard | Single-table journal, filters, labels and two-line dates deployed; dated [saved-data/browser verification](VERIFICATION.md#dashboard-releases-and-access) preserved. |

The last shared-code installation check (27 November 23:21 Melbourne) matched
72 application/resource files in installed source and native package, with clean
host fixtures and all five dashboard pages returning 200. This is distinct from
a fresh checkout-wide test run. Python 03's 42 application and 15 final setup guards,
Python 02's earlier 16/9 checks and the 566-test incident suite retain their own
revision scopes in [verification](VERIFICATION.md).

## Python 01

`practice-a` / `notebook-a` uses manually selected `t3_bandpass_v1`, qualified at
386 candles. Its account/candle preflight passed; original Q0 is AUD 50,000.1007,
snapshot `c245f517b15448cabb2edbb5336a53aa` at transaction 2249. The
[strategy and account evidence](VERIFICATION.md#python-01-account-and-host-evidence)
is retained independently of subsequent trading.

At the 28 November observation, run `m10-auto-bfeea7da7de9-20261127` had completed
at **08:50:21 Melbourne / 27 November 21:50:21 UTC**, checking 4/4 open-trade pairs
and 28/28 entry pairs, zero failed pair checks and successful final account refresh.
Its service exited 0. This observation did not review every execution requirement.

The failed GBP-CAD trade is closed and its notebook issue resolved. On 23 November
21:01:29, schema 3 reconciled through 2259: leg 1 closed by fill 2257, leg 2 never
opened, original incomplete set/failure/attempt/Q0/claims retained, A0 unset.
The 21:05 independent account check showed zero trades/positions/pending orders,
AUD 50,000.0032, trading loss -43.8956, financing -6.2319 and owner funding +50.03
as cash, not profit. Those are **23 November facts**, not today's account state.
[Recovery evidence](VERIFICATION.md#gbp-cad-incident-and-recovery) includes actual
close/funding, reader-before-writer deployment, native permissions/host checks,
operator disposition, backups and restored qualification scheduling. Do not rerun
incident helpers, reset Q0 or complete the unsent second leg.

## Python 02

`practice-b` / `notebook-b` uses DRM/adaptive BandPass at 512 candles.
[Selection and installation evidence](PYTHON_02.md) retain the independent AUD
account, source rules and preserved Python 01 records/schedule. Installation
27 November and scheduled setup 28 November are complete; its first regular
qualification run remains a future scheduled action in the observation below.

## Python 03

`practice-c` / `notebook-c` uses Eye Trend Zones/Age Adaptive Supertrend with a
5,000-candle raw capture and immutable research origin. [Setup](PYTHON_03.md) and
[comparison evidence](VERIFICATION.md#strategy-comparisons) retain the authorized
weekday normalization, failed rolling-window alternatives and exact final results.
Corrected installation 27 November preserved both earlier notebooks/schedules.
Scheduled setup is complete; actual Python 03 trading execution remains pending.

## Python 02 and Python 03 scheduled setup verification

**Observed 28 November 09:38–09:39 Melbourne / 27 November 22:38–22:39 UTC.**
Read-only live service properties and saved dashboard records confirmed both setup
services succeeded: Result=success, ExecMainCode=1 (normal process exit),
ExecMainStatus=0. Preserve these recorded observations:

| Controller | Setup start → finish (28 Nov Melbourne) | Q0 AUD | Transaction |
| --- | --- | ---: | --- |
| Python 02 | 08:50:00 → 08:50:12 | 50,000.6603 | 773 |
| Python 03 | 08:50:00 → 08:50:22 | 50,000.9696 | 1662 |

Notebook Q0 records are `a71bc581a216485283d4b47bad7554ab` and
`21dd5295531e47bd8aaa197ce2990f8d`, refreshed respectively at 27 November
21:50:11.044964 and 21:50:21.302247 UTC. Port 8879 notebook GETs returned 200,
showing those balances, no trade records, broker mutation requests or issues;
ordinary activation remained unset. Successful services, Q0 and enabled timers
confirm guarded initialization. Protected candle reports/setup receipts were
**not reopened** during that check; system journal entries were unreadable to the
login. No standalone export of this observation is cited in the original notes.

Both qualification timers were enabled/active/waiting, next due **Tuesday
1 December 08:50 Melbourne / 30 November 21:50 UTC**. Neither new trading service
had a start timestamp or qualification timer a previous trigger. “No runs recorded”
is expected: setup checks candles and initializes Q0 without invoking trading.
All three qualification timers shared that next expiry; all three ordinary timers
were disabled/inactive with no expiry. Verification did not rerun setup, trade,
modify files/schedules or send broker requests. Actual Python 02/03 trading had
not started in this observation. Do not rerun installers/bootstrap.

## Operational follow-up

The [operating checklist](IMPLEMENTATION_PLAN.md#operating-checklist) covers routine
dashboard monitoring, new experiments' first runs and focused fixes. M01–M09 are
delivery history; the M10 completion review and work list are retired.

The owner prefers continuous Q0 performance. Reporting and dispatch still use the
installed Q0/A0 lifecycle; changing that implementation is optional future work.
Manual Tuesday–Saturday 09:30 Melbourne dashboard checks continue.

Collector and host-inspector limitations remain in [operations](OPERATIONS.md)
for use when needed; they are outside the active checklist.

## Current handoff

Work: continue existing practice schedules; the owner has removed M10.
Verification: retained offline, host, account and execution evidence is linked
above; 28 November setup passed, but Python 02/03 have no recorded trading run yet.
Next: review Python 02/03 after 1 December 08:50 Melbourne; continue dashboard
checks and address errors.
Preserve Q0, claims, failures and current schedules; no daily arming or setup replay.

# Project status

Updated 28 November 2026 (Melbourne). Latest trading/service observations below
are from 09:38–09:39 Melbourne that day. No new broker or service checks were
performed for this documentation cleanup.

Feature work: [requirements, code and checks](../README.md#code-and-test-map).

## Current position

The checkout is on `main` with Python 01–03 implementation, schema-3 transaction
comparison, the single-table journal and guarded qualification/ordinary adapters.
All three experiments are installed. Automatic **qualification** is enabled under
its existing authority; **ordinary activation is unset and ordinary scheduling
is disabled** in the latest recorded observations. These are the installed mode
labels; the existing schedule continues. The [accepted operating decision](../PROJECT_BRIEF.md#delivery-sequence)
removed M10; M01–M09 are delivery history, with no milestone review queued.

| Delivery | State and evidence boundary |
| --- | --- |
| Approvals and M01–M09 | Approved stages and implementation/host-control results remain in [dated verification](VERIFICATION.md#approved-decisions-and-offline-milestones), with their evidence limits. No repeated stage approval is needed. |
| Dashboard | Single-table journal, filters, labels and two-line dates deployed; dated [saved-data/browser verification](VERIFICATION.md#dashboard-releases-and-access) preserved. |

The last shared-code installation check (27 November 23:21 Melbourne) matched
installed source/package files, with clean host fixtures and five dashboard pages
returning 200; [Python 03's installation record](PYTHON_03.md#recorded-installation-evidence)
owns the details. Retained suite results have their own revision scopes; this is
not a fresh checkout-wide test run.

## Python 01

`practice-a` / `notebook-a` uses manually selected `t3_bandpass_v1`, qualified at
386 candles. [Account/candle preflight and original Q0](VERIFICATION.md#python-01-account-and-host-evidence)
remain recorded independently of subsequent trading.

At the 28 November observation, run `m10-auto-bfeea7da7de9-20261127` had completed
at **08:50:21 Melbourne / 27 November 21:50:21 UTC**, checking 4/4 open-trade pairs
and 28/28 entry pairs, zero failed pair checks and successful final account refresh.
Its service exited 0. This observation did not review every execution requirement.

The failed GBP-CAD trade is closed and its notebook issue resolved. The
[23 November recovery record](VERIFICATION.md#gbp-cad-incident-and-recovery) retains
fills, cash funding, reconciliation, disposition and preserved failure history.
Its account figures are historical. [Completed procedures](OPERATIONS.md#completed-procedures-are-not-retries)
must not be replayed; the unsent second leg must not be completed.

## Python 02

`practice-b` / `notebook-b` uses DRM/adaptive BandPass at 512 candles.
[Selection and installation evidence](PYTHON_02.md) retain the independent AUD
account, source rules and preserved Python 01 records/schedule. Setup passed;
its first trading run had not started in the observation below.

## Python 03

`practice-c` / `notebook-c` uses Eye Trend Zones/Age Adaptive Supertrend with a
5,000-candle raw capture and immutable research origin. [Integration and installation](PYTHON_03.md)
retain its history decision, comparison references and preservation of both earlier
notebooks/schedules. Setup passed; its first trading run had not started in the
observation below.

## Python 02 and Python 03 scheduled setup verification

At the 28 November observation, both setup services had succeeded and Q0 was
recorded. All three qualification timers were enabled/active/waiting, next due
**Tuesday 1 December 08:50 Melbourne / 30 November 21:50 UTC**; ordinary timers
were disabled/inactive. Python 02/03 had no trading run or previous timer trigger.
The [full dated record](VERIFICATION.md#python-02-and-python-03-scheduled-setup-verification)
retains service results, Q0 identities/amounts and the inspection's evidence limits.

## Current handoff

Work: the [two operating activities](IMPLEMENTATION_PLAN.md#operating-checklist).
Blockers: none recorded; Python 02/03 await their first scheduled trading run.
Verification: 28 November setup passed; dated evidence and limits are linked above.
Next: review Python 02/03 after 1 December 08:50 Melbourne; continue the agreed
dashboard checks and address errors.
Preserve Q0, claims, failures and current schedules; no daily arming or setup replay.

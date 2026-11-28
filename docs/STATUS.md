# Project status

Updated 28 November 2026 (Melbourne). Trading observations below are from
09:38–09:39; cleanup checks are from 16:40. Single practice mode was installed
at 21:50 and independently verified afterward, without broker requests or test trades.

Feature work: [requirements, code and checks](../README.md#code-and-test-map).

## Cleanup

Cleanup is complete. The old preview and obsolete M09/M10 units are removed,
port 8880 is closed, and 139 generated build, packaging and bytecode files are gone.
[Final verification](/mnt/nnfx-usb/development/data/nnfx-practice-lab/host-cleanup-20261128-ft4lhowm/completion-verification.json)
confirmed live service identities, schedules and unit files match the original
snapshots, no manager reload is pending, and all five dashboard pages return 200.
The administrator receipt verified retained evidence and runtime data unchanged,
including the collection unavailable to this login. Preview source/captures,
retired unit copies and the original failed cleanup receipt remain preserved.

## Current position

Single practice mode is installed for all three experiments. Ordinary execution,
activation and unused timers are removed; reports continue from the original Q0.
[Independent verification](/mnt/nnfx-usb/development/data/nnfx-practice-lab/single-practice-mode-0oqfmwj5/evidence/final-verification.json)
matched all 71 runtime files in the installed source, package and dashboard.
The 44 schema, strategy, sizing, order, reconciliation and active schedule files
match the original baseline. Native host fixtures passed with clean removal;
all five dashboard pages return 200 and restrictions/deployer permissions are unchanged.

The administrator receipt verified notebook/sidecar/claim/raw-capture fingerprints,
credentials and registry unchanged. Protected originals remain in
`/etc/nnfx-practice/upgrades/single-mode-d82d9d8e1279`. This login cannot read those
private files directly; independent saved-page comparisons matched all three Q0s,
opening balances, account totals and displayed trade/ledger/request records.
No trading controller was started. Reload cleared Python 01's inactive systemd
invocation cache; saved run history remains intact. The dashboard was restarted.

All three existing qualification-named practice timers remain enabled/active/waiting,
with unchanged calendars and next triggers: **1 December 08:50 Melbourne / 30 November
21:50 UTC**. Their names remain compatibility identifiers, not separate modes.
[Offline validation](/mnt/nnfx-usb/development/data/nnfx-practice-lab/single-practice-mode-0oqfmwj5/evidence/validation.json)
retains 164 focused cases with corrected fixture reruns, upgrade guards and 40
preflight/deployment checks. Interrupted broader runs are not full-suite passes.
The failed preflight's screenshot, source and protected partial backup are preserved;
the corrected procedure is in [operations](OPERATIONS.md#single-practice-mode-upgrade). The
[accepted operating decision](../PROJECT_BRIEF.md#delivery-sequence)
removed M10; M01–M09 are delivery history, with no milestone review queued.

| Delivery | State and evidence boundary |
| --- | --- |
| Approvals and M01–M09 | Approved stages and implementation/host-control results remain in [dated verification](VERIFICATION.md#approved-decisions-and-offline-milestones), with their evidence limits. No repeated stage approval is needed. |
| Dashboard | Single-table journal, filters, labels and two-line dates deployed; dated [saved-data/browser verification](VERIFICATION.md#dashboard-releases-and-access) preserved. |

Earlier installation results remain in
[Python 03's record](PYTHON_03.md#recorded-installation-evidence), scoped to that release.

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
Blockers: none recorded; single-mode installation and verification are complete.
Next: review Python 02/03 after their first scheduled run on 1 December 08:50 Melbourne.
Preserve Q0, claims, failures and evidence; do not replay the completed upgrade,
bootstrap accounts or trigger a manual run to verify scheduling.

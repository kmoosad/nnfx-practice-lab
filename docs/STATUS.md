# Project status

Updated 28 November 2026 (Melbourne). Observations below are dated records,
not a fresh availability or broker check. For feature work, use the
[README map and commands](../README.md#code-and-test-map).

## Current position

The checkout implements one practice trading mode, installed for all three
experiments on 28 November at 21:50 and independently verified afterward.
Ordinary execution, activation and unused timers are removed; reports retain the
original Q0 and all history. [Installation evidence](VERIFICATION.md#single-practice-mode-installation)
records file/data preservation, native host and dashboard checks, offline test
limits and the protected failed attempt. No broker requests or test trades were
used for installation verification.

The [accepted operating decision](../PROJECT_BRIEF.md#delivery-sequence) removed M10.
M01–M09 remain [delivery history with prior approvals](VERIFICATION.md#approved-decisions-and-offline-milestones),
with no milestone review queued. Dashboard releases and access have
[dated verification](VERIFICATION.md#dashboard-releases-and-access).

## Python 01

`practice-a` / `notebook-a`: manually selected `t3_bandpass_v1`, 386 candles.
[Account/candle preflight and Q0](VERIFICATION.md#python-01-account-and-host-evidence)
remain separate from subsequent trading.

At the 28 November 09:38–09:39 observation, run `m10-auto-bfeea7da7de9-20261127`
had completed at **08:50:21 Melbourne / 27 November 21:50:21 UTC**: 4/4 open-trade
pairs, 28/28 entry pairs, zero failed pair checks, successful final refresh and
service exit 0. This did not review every execution requirement.

The failed GBP-CAD trade is closed and its issue resolved. The
[recovery record](VERIFICATION.md#gbp-cad-incident-and-recovery) preserves fills,
funding and failure history; its account figures are historical. Do not complete
the unsent second leg or replay [completed procedures](OPERATIONS.md#completed-procedures-are-not-retries).

## Python 02

`practice-b` / `notebook-b`: DRM/adaptive BandPass, 512 candles.
[Selection and installation](PYTHON_02.md) retain its independent AUD account and
preservation of Python 01.

## Python 03

`practice-c` / `notebook-c`: Eye Trend Zones/Age Adaptive Supertrend, 5,000 raw
candles and immutable research origin. [Integration and installation](PYTHON_03.md)
retain its history decision and preservation of both earlier experiments.

## Python 02 and Python 03 scheduled setup verification

[Observed 28 November 09:38–09:39](VERIFICATION.md#python-02-and-python-03-scheduled-setup-verification):
both setup services succeeded with Q0 recorded; neither had traded or triggered
its practice timer. All three timers' next trigger was **1 December 08:50 Melbourne /
30 November 21:50 UTC**, unchanged by the later single-mode installation.
Qualification-named timers are compatibility identifiers for that single mode.

## Cleanup

[Verified 28 November 16:40](VERIFICATION.md#host-cleanup): obsolete preview/M09/M10
units and generated build files removed; evidence and runtime data preserved.

## Current handoff

Work: the [two operating activities](IMPLEMENTATION_PLAN.md#operating-checklist).
Blockers: none recorded. Installation verification is linked above.
Next: continue the agreed dashboard checks; review Python 02/03 after their first
scheduled run on 1 December at 08:50 Melbourne.
Preserve Q0, claims, failures and evidence. Do not replay upgrades/bootstrap or
trigger a manual run to verify scheduling.

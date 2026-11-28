# Implementation plan

Approved by the owner on 16 November 2026 after three review fixes. The
[brief](../PROJECT_BRIEF.md) owns behaviour, [design](DETAILED_DESIGN.md) owns
contracts and [acceptance](ACCEPTANCE.md) owns scenarios and test variations.
[Status](STATUS.md) owns current operation; this plan retains delivery history and
guidance for bounded feature/fix requests.

## Delivery history

Architecture → detailed design → planning reviews are complete. M01–M09 below
record the original delivery sequence and dependencies, with dated results in
[verification](VERIFICATION.md). They are not an outstanding review queue. Use the
bounded brief below for routine work. Do not repeat earlier approvals or treat
them as account evidence. No automatic strategy selection,
repair service, signal forcing or unreviewed Trade 2 size change is permitted.

| Former milestone | Original dependency | Delivered scope and verification coverage |
| --- | --- | --- |
| M01 configuration/storage | Approved plan | Immutable bindings, schema, durable intent and scripted test foundation; A12/A15/A16. |
| M02 broker/reconciliation/ledger | M01 | Account-pinned reads, complete atomic imports and reporting boundaries; A11/A12/A14/A16. |
| M03 candles/strategy | M01–M02 and manual selection | Exact calculations, events, count/history qualification; A01–A03. |
| M04 intended-account preflight | M02/account; M03 for candle pass | Account/profile, 28 instruments/conversions and scheduled partial-candle coverage; A01/A03/A05/A13/A16. |
| M05 open-trade management | M01–M03 contracts | Registered IDs, due stops, ordered independent exits and guarded outcomes; A03/A07/A10–A12. |
| M06 sizing/two-leg entry | M01–M03; account findings | Decimal risk/margin, conditional protected entry and incomplete-set cases; A03/A05/A06/A12. |
| M07 master/lifecycle/disposition | M01–M06 | Full sequence, independent entry signal, exclusions, Q0/A0 atomicity; A02–A16 as applicable. |
| M08 dashboard | M01–M02 records and M07 outcomes | Read-only views, snapshot-consistent totals and visible failures; A14–A16. |
| M09 host controls | M07; M08 for dashboard | Timing, exclusion, permissions, restart/replay protection and deployed display; A01/A12/A13/A15/A16. |

For new experiments, offline work can proceed while account checks are pending;
fixtures do not establish broker support. Each notebook/strategy needs its own
selection, calculation and account qualification.
Strategy/count bindings now exist for Python 01–03; they are not pending selections.
Account-specific execution remains conditional, including equal-size protected
trades, client extensions, precision and targeted closes. A one-unit-increment
Trade 2 reduction remains only a review option if actual restrictions require it.

The [state rules](DETAILED_DESIGN.md#state-rules) own no-fill release and attempt
guards; the lifecycle below owns Q0/A0. Approved review fixes and their evidence
remain in [verification](VERIFICATION.md#approved-decisions-and-offline-milestones).

## Operating checklist

The [operating decision](../PROJECT_BRIEF.md#delivery-sequence) retired M10's
completion review and initial/final qualification work list. Retain
[dated evidence](VERIFICATION.md) and its limits; removing the milestone does not
mark unobserved acceptance scenarios as verified.

Only two operating activities remain:

1. Review the dashboard Tuesday–Saturday at 09:30 Melbourne and address errors
   promptly, as agreed on 20 November.
2. Review Python 02/03's first trading runs against their setup records;
   [status](STATUS.md) owns the dated Python 02/03 observations and next run.

Use [acceptance scenarios](ACCEPTANCE.md) for focused verification of changes and
investigation of operating issues. There is no further M10 sign-off to schedule.

Apply the [account and execution evidence requirements](ACCEPTANCE.md#account-and-execution-evidence).
Account incompatibilities, unsupported monetary shapes and unresolved outcomes
return to review. Reuse observations only while their code/configuration/strategy/
account conditions apply; verify affected behaviour when those conditions change.

## Practice lifecycle

On 28 November the owner requested one practice trading mode, removing ordinary
activation while preserving trading behaviour, schedules and all history.
[Status](STATUS.md) distinguishes implementation from installed operation.

1. **Initialize once.** Under maintenance, validate the immutable binding,
   strategy/count and account-specific prerequisites. Commit a reconciled opening
   snapshot and import boundary together before orders. The existing Q0 is that
   starting balance. Reopening reconciles forward and never replaces it.
2. **Run the existing controller.** Retain the weekday 16:50 New York trigger,
   partial-candle calculations, sizing, management, broker guards and raw captures.
   Verify the protected account/code/configuration/strategy/host authority and
   claim the New York date durably before network activity. No catch-up, daily
   arming, forced signals, duplicate claims or automatic failure retries.
3. **Report one history.** Practice totals cover postings after Q0 through the
   last reconciled snapshot. There is no new balance boundary or activation step.
   Deposits, financing and charges remain distinct from trading results.

Existing `qualification` plan, timer, directory and invocation names remain
compatibility identifiers for this single path. Keep all old claims, exports,
failures and Q0/A0 fields unchanged; the schema and immutable triggers remain.
Read-only legacy interval queries can reproduce archived qualification/ordinary
results. They cannot authorize execution or create another A0. An existing
historical A0 does not truncate the unified practice report.

Native broker mutations still require the verified practice permit; the default
transport is GET-only. Initialization requires its read-only permit before private
configuration, service operations or notebook writes. Offline fixtures do not
establish account authority. An ordinary plan or invocation is rejected.

The [upgrade procedure](OPERATIONS.md#single-practice-mode-upgrade) refreshes
protected code/control identities for all installed accounts while preserving
notebooks, bindings, claims, evidence and each schedule's original state.

## Feature brief template

Use directly in a task prompt; no new file is required for each feature.

```text
Outcome: <observable improvement for this increment>
Requirements: <authoritative document/section links>
Implementation and tests: <entry points from the README map>
Scope: <included work and explicit boundaries>
Constraints: <trading, persistence, account or authority constraints>
Acceptance (up to five): <observable criteria, referencing existing rules>
Verification: <focused checks; required evidence class; success signal>
Unresolved decisions: <material questions, or none>
```

## Handover and evidence discipline

For a requested milestone handover, name the work, prerequisites, applicable
checks and stopping point; carry unfinished work and existing authority forward.
Stop for its agreed review before another explicitly requested milestone.
For routine work, update existing status/guidance only with consequential
decisions and findings.

Keep one current status handoff. Record scenario/variation, evidence class, date,
code/configuration/strategy identities, input location, run/set IDs, expected and
actual result and pass/fail/blocked reason with the retained evidence. Preserve
non-secret broker IDs and failures. A scenario closes only when its controlled
checks and applicable host/account observations exist; unknown remains pending.

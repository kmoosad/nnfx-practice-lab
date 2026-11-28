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

The approved review fixes remain binding: only a wholly rejected set with neither
leg opened and no issue qualifies for no-fill release; M01/M02/M07 own the tested
Q0/A0 lifecycle. The design also retains exact windows, prior-attempt guards,
maintenance exclusion through reads/writes and snapshot-aligned totals.

## Operating checklist

The owner removed M10 on 28 November under the
[operating decision](../PROJECT_BRIEF.md#delivery-sequence). Its completion review
and initial/final qualification work list are retired. The practice account has
been running for about a week with trades resolved, as reported by the owner.
Retain [dated evidence](VERIFICATION.md) and its limits; this decision does not
mark unobserved acceptance scenarios as verified.

Continue routine operation and bounded follow-up:

1. Review the dashboard Tuesday–Saturday at 09:30 Melbourne and address errors
   promptly, as agreed on 20 November.
2. Review new experiments' first trading runs against their own setup records;
   [status](STATUS.md) owns the dated Python 02/03 observations and next run.

Use [acceptance scenarios](ACCEPTANCE.md) for focused verification of changes and
investigation of operating issues. There is no further M10 sign-off to schedule.

Account incompatibilities, unsupported monetary shapes and unresolved outcomes
return to review. `hedgingEnabled`, API documentation, simulated fills and pass
flags cannot replace execution evidence. Reuse observations only while their
code/configuration/strategy/account conditions apply; verify affected behaviour
when those conditions change. Profitability is not an acceptance gate.

## Optional work

The owner's preference for continuous performance from Q0 remains recorded.
Changing the Q0/A0 reporting or dispatch implementation would be separate work.
The existing qualification schedule and notebook history continue; an ordinary-mode
transition is not a remaining delivery step.

Alerts/reminders are optional ideas. Collector and host-inspector enhancements
are deferred until needed; their current limitations stay in [operations](OPERATIONS.md).

## Qualification records and ordinary activation

This section describes the installed lifecycle, including the optional ordinary
transition. Removing M10 does not change its runtime checks or reporting labels.
Use one immutable notebook and the same controller throughout. The owner's
19 November Python 01 execution authority and 20 November recurring qualification
instruction remain valid within their prerequisites. Python 02/03 have separate
protected setup/qualification bindings; none grants ordinary authority.

The native [broker](../nnfx_practice/broker.py) defaults to GET-only. Native
mutations require a verified qualification or ordinary execution permit.
[Initialization](../nnfx_practice/lifecycle.py) rejects an unpermitted transport
before loading private configuration, touching services or creating Q0; native
initialization requires its verified read-only permit. Scripted transports are
for offline checks. Nonempty prerequisite references alone establish no live
qualification or authority.

1. **Initialize Q0 under maintenance.** Validate manifest/count, registry and
   account/currency; finish account preflight and resolve existing/unexplained
   activity. Commit a consistent qualification snapshot Q0, its evidence and
   initial imported-through boundary together before orders. Leave A0/time unset.
   Reopening preserves Q0 and history and reconciles forward, never resets them.
2. **Run qualification.** Require an initialized, unactivated notebook and
   evidence of the completed prerequisites above. A protected weekday plan targets
   the same service at 16:50 New York while ordinary scheduling is disabled. Each dispatch
   checks authority, code/configuration/account/strategy, host evidence, clock and
   process identity, then fsyncs an exclusive New York date claim before network
   activity. Claims survive failures, dated-plan replacement and ordinary
   transition. No catch-up, daily arming or forced signals. Use the same master,
   attempt guards and operator disposition; retain every run and failure.
3. **Report qualification.** Post-Q0 entries through a successful snapshot are
   labelled qualification; ordinary totals are unavailable before A0. At A0 cap
   qualification reporting there permanently. Do not count its results again.
4. **If an ordinary transition is requested.** The installed verifier requires
   the protected A01–A16 review and authority in [operations](OPERATIONS.md#ordinary-review-and-activation).
   Under maintenance require no trades/orders/unresolved sets, attempts or
   issues, then reconcile a fresh A0. Commit A0, history/cursor, evidence and time
   atomically. Failure leaves activation unset; repetition verifies the same A0.
   Preserve binding, manifest, Q0 and history; never rewind the cursor.
5. **Start ordinary operation separately.** A0 is its opening balance. Include
   only later postings through the displayed snapshot. After maintenance releases,
   separately enable the authorized ordinary timer. Qualification rejects an
   activated notebook; ordinary dispatch requires activation and protected review.

Controlled transitions must cover interrupts before/after both commits, repeated
calls, unresolved qualification sets and changed bindings. The +100 before A0 /
+20 after A0 example retains qualification +100, includes it in ordinary opening
balance, and reports ordinary profit +20 exactly once; see A12/A14/A16.

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

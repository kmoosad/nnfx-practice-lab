# Implementation plan

Approved by the owner on 16 November 2026 after three review fixes. The
[brief](../PROJECT_BRIEF.md) owns behaviour, [design](DETAILED_DESIGN.md) owns
contracts and [acceptance](ACCEPTANCE.md) owns scenarios and test variations.
[Status](STATUS.md) owns completion; this plan owns dependencies and remaining work.

## Delivery boundaries and dependencies

Architecture → detailed design → planning reviews are complete. Preserve the
owner's one-requested-milestone-per-chat review boundary for milestone work;
straightforward feature fixes use the bounded brief below. Do not repeat earlier
approvals or treat them as account evidence. No automatic strategy selection,
repair service, signal forcing or unreviewed Trade 2 size change is permitted.

| Milestone | Dependency | Delivered scope and verification obligation |
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
| M10 observed practice/activation | See below | Actual execution path, final integration and separate ordinary activation review. |

Offline work can proceed against defined interfaces while an account dependency
is pending; fixtures cannot complete the account-dependent milestone. Every new
notebook/strategy needs its own selection, calculation and account qualification.
Strategy/count bindings now exist for Python 01–03; they are not pending selections.
Account-specific execution remains conditional, including equal-size protected
trades, client extensions, precision and targeted closes. A one-unit-increment
Trade 2 reduction remains only a review option if actual restrictions require it.

The approved review fixes remain binding: only a wholly rejected set with neither
leg opened and no issue qualifies for no-fill release; M01/M02/M07 own the tested
Q0/A0 lifecycle; initial execution does not wait for the dashboard, but final
integration does. The design also retains exact windows, prior-attempt guards,
maintenance exclusion through reads/writes and snapshot-aligned totals.

## Remaining work

M01–M08 implementations and substantial M09 controls have evidence in
[verification](VERIFICATION.md). M10 remains open; the following is the retained
work list, not a claim that every item is wholly unobserved.

1. **Initial account-path qualification:** needs M01–M07, strategy qualification,
   intended-account preflight, essential M09 controls and account-scoped execution
   authority. Essential controls are synchronized clock/calendar and broker-free
   dispatch, single-service/overlap exclusion, private credentials/notebook
   permissions, no restart/replay and maintenance restoration. M08 and final host
   observations may follow. Observe natural long, short and cross-currency sets:
   distinct trade IDs/units, actual fills and historical fill-relative stops/target;
   Trade 1 TP and Trade 2's confirmed scheduled stop-to-own-entry; targeted closes;
   restrictions/precision and estimated versus broker margin. Inspect notebook
   transactions directly; no dashboard is required for this initial check.
2. **Final integration qualification:** needs M01–M09 and successful initial path.
   Retain a completed 16:50 run with both stages' actual captures, ordered 28-pair
   entry coverage/skips, duration and reporting. Reconcile fills, closures, daily
   financing, closure summaries and other charges to the final snapshot and traded
   dashboard. Finish the current-kernel unattended scheduled window and A01–A16
   review. Existing -43 startup proof remains; inspect observer evidence before
   arranging another window. The old -42 window's unattended context is unknown.
3. **Ordinary transition:** close qualification trades/orders, resolve issues by
   evidence, protect the actual reviewed packet, obtain final ordinary authority,
   and commit fresh A0 under maintenance. Enable ordinary scheduling separately
   only after release. Use [operations](OPERATIONS.md#ordinary-review-and-activation).

Account incompatibilities, unsupported monetary shapes and unresolved outcomes
return to review. `hedgingEnabled`, API documentation, simulated fills and pass
flags cannot replace execution evidence. Reuse observations only while their
code/configuration/strategy/account conditions apply; verify affected behaviour
when those conditions change. Profitability is not an acceptance gate.

The owner agreed on 20 November to leave automatic qualification running and
review the dashboard Tuesday–Saturday at 09:30 Melbourne, addressing errors
promptly. Alerts are deferred. The intended joint performance/M10 review was
27 November 2026; completion is not recorded and no reminder was scheduled.

The owner prefers continuous performance from Q0 with qualification completion
as a milestone. This lifecycle/reporting simplification is discussed, **not
accepted as an implemented replacement**. Decide the transition before ordinary
activation; until then the Q0/A0 procedure below remains authoritative.

## Qualification records and ordinary activation

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
4. **Activate after final qualification.** Under maintenance require completed
   M10/A01–A16 and final authority, no trades/orders/unresolved sets, attempts or
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
Stop for its agreed review before the next milestone. After M10 provide completion
handover, not another invented milestone. For routine work, update existing
status/guidance only with consequential decisions and findings.

Keep one current status handoff. Record scenario/variation, evidence class, date,
code/configuration/strategy identities, input location, run/set IDs, expected and
actual result and pass/fail/blocked reason with the retained evidence. Preserve
non-secret broker IDs and failures. A scenario closes only when its controlled
checks and applicable host/account observations exist; unknown remains pending.

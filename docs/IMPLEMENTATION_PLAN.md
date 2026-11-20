# NNFX Practice Lab implementation plan

Status: Approved by the owner on 16 November 2026 after the three review fixes.
Implementation progress and verification evidence are recorded in [status](STATUS.md).

This plan orders delivery of the [approved detailed design](DETAILED_DESIGN.md).
The [brief](../PROJECT_BRIEF.md) owns behaviour, the
[architecture](ARCHITECTURE.md) owns the numbered workflow, and the
[acceptance checklist](ACCEPTANCE.md) owns required scenarios A01–A16.
The design's [test cases](DETAILED_DESIGN.md#8-acceptance-test-design) supply
the variations and assertions; the summaries below do not replace them.

This planning chat ends with approval and handover. Implementation begins in a
separate chat for the requested milestone; no runtime work or broker activity
is performed here.

## Delivery boundaries and dependencies

Keep one Python process with two sequential child modules, one SQLite notebook
per account, a small practice-only broker client and a separate Flask/Jinja
dashboard. Use the design's ordinary functions and records, with a scripted
transport for controlled checks. Add no queues, recovery service, automatic
strategy selection or research framework.

| Dependency | Current state | What it gates |
| --- | --- | --- |
| Owner review of this plan | Approved, 16 November 2026 | M01 may begin when requested in its new chat; plan and design approval need not be repeated. |
| Manually selected first C1/Exit strategy and provenance | Pending | Extracting and qualifying its exact calculations in M03. No default combination is selected by this plan. |
| Qualified rolling candle count | Pending | Completing M03 and binding a runnable strategy. ATR's minimum of 15 total bars is not a chosen lookback. |
| Intended dedicated practice account and private connection | Pending | Actual read-only preflight in M04. No account capability is assumed. |
| Account findings and observed execution | Pending | M10's initial account-path check, then final integration qualification before ordinary activation. M04 reads alone cannot qualify execution. |

Milestones are in delivery order. Their stated dependencies allow independent
offline work to continue when strategy or account inputs are missing. A milestone
with missing qualification evidence remains incomplete; fixture-based controller
checks do not complete strategy or account qualification.

M10 has an initial account-path check and a final integration check. The initial
check can follow M07 and M09's essential controller controls without waiting for
M08 or dashboard deployment. Final qualification still requires all milestones.

The candidate equal-size, two-leg path remains conditional. Client extensions,
protected-size/FIFO restrictions, separate trade identities and fill-relative
protection must work on the intended account. The proposed one-unit-increment
reduction for Trade 2 remains a review option, never an automatic fallback.
Bring account incompatibilities and any proposed behavioural adjustment to review
before activation, following the [design's activation contract](DETAILED_DESIGN.md#2-configuration-and-activation).

## Ordered milestones

### M01 — Configuration, notebook and controlled-check foundation

**Depends on:** plan approval.

- Establish the small package and notebook layout from design section 1, explicit
  dependencies, non-secret configuration examples and private/data exclusions.
- Implement registry validation, immutable notebook/strategy bindings and the
  section 4 schema with decimal text, UTC timestamps, uniqueness, foreign keys,
  WAL and short durable transactions. Preserve existing records on schema changes.
  Support the pending activation fields and separately identified qualification
  snapshot in the [qualification lifecycle below](#qualification-records-and-ordinary-activation).
- Add a temporary-notebook test setup, controllable clock and scripted transport
  that records ordered calls and can interrupt at commit boundaries. It uses the
  real controller functions as they are added, without broker access.

**Verification / exit:** offline A12, A15 and A16 foundation checks prove binding
rejection, pair reservation, derived progress counts and durable prepared attempts.
Check that secret fields never enter logs or notebook evidence. The storage and
configuration boundary is usable by later milestones; no trading is enabled.

### M02 — Read-only broker access, reconciliation and ledger

**Depends on:** M01.

- Implement practice-host/account pinning, reusable connections, timeouts,
  redacted evidence and the design's account, instrument, pricing, candle,
  transaction and trade/order reads. Distinguish response status from broker facts.
- Import complete transaction intervals through a snapshot boundary, atomically
  committing derived fills, ledger entries and cursor. Deduplicate broker IDs,
  preserve newer confirmed state and expose unexpected or unexplained activity.
- Build snapshot reconciliation and reporting queries with an explicit opening
  snapshot: qualification uses Q0; ordinary reporting uses activation snapshot A0
  as defined below. Exercise both with temporary notebooks. Preserve separate
  posted P/L, financing, charges and cash adjustments without duplicate postings.

**Verification / exit:** offline A11, A12, A14 and A16 cover missing closing evidence,
duplicate/page imports, history gaps, older snapshots, interrupted writes,
unexplained balance differences and account isolation. Broker-shaped fixtures
verify importer behaviour; actual account and charge mapping remain pending M04/M10.

### M03 — Candle validation and selected strategy qualification

**Depends on:** M01–M02; manual strategy selection for numerical qualification.

- Implement the shared daily-mid candle function and capture metadata. Require
  exactly the bound count, completed preceding bars and the intended partial
  candle due to end at 17:00 New York on the run's local date. Each stage captures
  its own input; no padding, shortened window or completed-candle fallback.
- Once selected, inspect and copy only the strategy's lab calculations and exact
  transitive helpers into its versioned package. Record provenance, hashes,
  parameters, output bindings and accepted rule identities. Keep runtime
  independent of the sibling lab checkout and database.
- Compare identical inputs with the selected lab code, preserving its ATR,
  comparison and fresh-event semantics. Qualify the shortest sufficient rolling
  window for C1, Exit, prior observations and ATR, and bind that count to the
  manifest. Record evidence for initialization and shorter-window failures.

**Verification / exit:** offline A01–A03 cover DST/session boundaries, malformed or
wrong-count windows, crossings, continuing states, equality, missing operands,
invalid simultaneous outputs, ATR ties/gaps and initialization. Check that invalid
ATR leaves a valid exit actionable. Candle plumbing can proceed while selection
is pending; M03 completes only with the selected strategy and qualified count.

### M04 — Intended practice-account read-only preflight

**Depends on:** M02 and the intended private connection; M03 for final candle-window
coverage. Identity, instrument and conversion checks can precede M03 completion.

- Verify account identity/division, currency, balance, existing trades/orders and
  all 28 permitted instruments, including precision, size and margin metadata.
  Record client-extension and protected-trade restrictions for execution review.
- Retain actual pricing with `includeHomeConversions=true`, including cross-currency
  cases. Apply every A05 preflight check and applicability rule in design section 8:
  required quote `accountLoss` values must be present, finite and positive.
- Capture intended weekday 16:50 candles for the permitted pairs, recording exact
  window coverage, response times and captures unavailable before rollover.

**Verification / exit:** actual read-only account evidence supports A01, A03, A05,
A13 and A16. Require a live matching-quote case only when a permitted pair quotes
in the home currency. Independently check returned home-currency `accountLoss = 1`
when that currency occurs as base or quote in a permitted pair; otherwise record
the relevant live case as not applicable with its reason. Keep the controlled
matching-quote test for every configuration. Missing/invalid required conversions
or a non-1 home-currency factor where applicable prevent preflight completion.
Record findings for M06/M10; do not label the order
path qualified or send any order as part of M04.

### M05 — Manage Open Trades

**Depends on:** M01–M02 and M03's calculation contract. Selected-strategy qualification
is required before any actual strategy run; scripted observations can test flow.

- Reconcile registered sets and both leg records first, including an already
  closed Trade 1. Resolve actual closures and check due stop-to-entry changes
  before fetching signal candles.
- Implement guarded stop changes and per-leg signal closes under the design's
  [state rules](DETAILED_DESIGN.md#state-rules). Commit an attempt before each
  mutation and its outcome before the next. Prior failed/unresolved attempts
  stay with the operator; protection issues do not suppress an eligible exit.
- Process surviving pairs in brief order, independently evaluate C1 and Exit,
  retain both triggers when applicable and commit each outcome before advancing.

**Verification / exit:** offline A03, A07 and A10–A12 exercise long/short opposite
events, one unavailable indicator, missing legs, mixed closure causes, intervening
closures and next-run retry guards. A requested close/stop change never becomes
confirmed without broker evidence. Actual mutations await M10 qualification work.

### M06 — Sizing and candidate two-leg entry

**Depends on:** M01–M03 interfaces; M04 findings for account-specific decisions.
Pure sizing and candidate request sequencing may be checked offline while M04
is pending; the path remains conditional until M10 succeeds.

- Implement decimal sizing with the fixed 4.1 balance, executable 1.5 × entry-ATR
  stop distance and returned quote-currency `accountLoss`, even for a home-matching
  quote. Round base units down within each leg's 1% budget and instrument limits.
  Use base `positionValue` for margin and recheck margin before Trade 2.
- Implement the candidate sequence against the scripted transport: reserve set
  and both legs; Trade 1 market/stop; confirmed fill-relative target; confirm
  survival/protection and margin; Trade 2 market/stop with no target. Follow the
  exact [request contract](DETAILED_DESIGN.md#conditional-two-leg-request-sequence).
- Confirm distinct identities, fills and protection established together before
  completing a set. Retain frozen ATR and original levels. Stop a failed sequence
  and record an issue when effects or required protection remain incomplete or
  unresolved. Only a wholly rejected entry with both expected legs confirmed never
  opened and no open issue releases its reservation without a lasting block.
  A rejected Trade 2 after Trade 1 fills remains an incomplete set requiring
  operator disposition, even when both request outcomes are known or Trade 1 later
  closes. Add no repair orders, resized second-leg fallback, trailing stop or
  combined account risk cap.

**Verification / exit:** offline A03, A05, A06 and A12 cover both directions,
currency/precision limits, absent/invalid conversions without fallback, pre-set
and second-leg margin failures, target rejection, reductions instead of new trades,
wrong units, missing protection and price exits before/after establishment.
Explicitly contrast a wholly rejected/no-fill set with a filled Trade 1 followed
by a rejected Trade 2, retaining the latter's issue until evidenced disposition.
Compare request traces and committed evidence; successful fixtures do not establish
account support or actual fill-relative protection.

### M07 — Full master workflow, entry loop and operator disposition

**Depends on:** M01–M06 components; unresolved M03/M04 qualification still blocks
actual strategy operation, but not integrated offline checks.

- Wire master → Manage Open Trades → one 4.1 sizing-balance refresh → Manage New
  Trades → final reporting refresh. Preserve separate sizing, margin and reporting
  purposes. A fatal Stage 1/balance failure prevents new entries; isolated pair
  failures allow continuation when account state and notebook writes remain usable.
- Visit all 28 pairs in brief order. Check notebook eligibility before pair-specific
  requests; capture fresh candles for eligible pairs and use only their C1/ATR.
  Flat, clear pairs can enter either fresh direction after any closure reason.
- Complete durable progress/error reporting and the small local disposition
  action. It reads broker evidence and writes the notebook without orders,
  excluding controller launches throughout reads and writes as design section 6
  requires. Reconciliation alone does not clear operator-owned issues.
- Implement qualification initialization, the explicit qualification invocation
  and the atomic activation transition described in the
  [qualification lifecycle](#qualification-records-and-ordinary-activation).
  Use the existing notebook and controller functions; ordinary startup continues
  to reject an unactivated notebook.

**Verification / exit:** integrated offline A02–A13 and A16 exercise the design's
controller variations through real components. Assert ordered requests and committed state,
including no pair-specific calls for blocked pairs, fixed sizing balance,
independent entry signals, no mutation replay, interruptions between requests,
and visible failures when writes cease. Validate disposition evidence and exclusion
logic; real service/timer exclusion is checked in M09.
Add A12/A14/A16 cases for interrupted initialization/activation, unresolved issues
blocking activation, unchanged bindings and preserved history across the reporting
baseline change. These checks must pass before M10's initial account-path check.

### M08 — Observational dashboard

**Depends on:** M01–M02 records/queries and M07 run outcomes.

- Build only the Controller, Notebooks and notebook-detail GET views, following
  the approved presentation reference and journal columns.
- Derive progress counts from final pair outcomes. Align all account totals with
  the displayed reconciled snapshot; show newer journal activity separately,
  alongside unfinished runs, failures, issues and New York times with offsets.
- Use read-only notebook access that sees committed WAL updates, registry-bound
  paths and no private credentials, broker client or controller invocation.

**Verification / exit:** offline A14–A16 verify long/short and JPY pips, reductions,
charges, signed colours, missing values, stale/failed refreshes and the design's
snapshot-S/+100 case. Exercise GET views and reject mutation requests using
read-only database permissions and no credentials. Actual records are checked
again during M10's final check. Verify qualification labels and the A0 reporting
boundary; no dashboard action starts trading, activates a notebook or resolves issues.

### M09 — Host operation, scheduling and maintenance exclusion

**Depends on:** M07 for controller operation and maintenance; M08 only for dashboard
deployment; target Ubuntu host access. Complete the controller controls before
M10's initial account-path check; dashboard deployment may follow independently.

- Prepare the virtual environment, per-controller oneshot service/timer templates
  and separate dashboard service. Preserve the approved weekday 16:50 New York
  schedule, `AccuracySec=1s`, `Persistent=false` and `Restart=no`.
- Verify clock synchronization, host wakefulness, startup without login, permissions
  and single-service execution. Keep ordinary trading timers inactive until the
  activation gate below; use a harmless broker-free command for dispatch tests.
- Verify maintenance pauses the timer, requires an inactive service with no pending
  launch, excludes launches throughout broker reads and notebook writes, and
  restores the prior timer state only after release, including on failure.
  Add real setup/run/maintenance commands to the README when they exist.

The essential controller controls required before any practice mutation are the
clock/calendar and broker-free dispatch checks, the single service and its tested
exclusion of overlapping runs, private credentials and notebook permissions, no
automatic restart/replay, and tested maintenance exclusion/restoration on success
and failure. Qualification dispatch uses this service at the agreed time with
ordinary recurring launches inactive. Only the dashboard deployment and its
permissions/display checks depend on M08 and may follow the initial account check.

**Verification / exit:** offline calendar and host operational A01, A12, A13,
A15 and A16 checks cover both DST transitions/weekends, actual timer dispatch,
inactive missed launches, no catch-up/restart/overlap, active-service deferral,
maintenance failure and an initially paused timer. Retain host dispatch evidence
separately from calendar calculations; neither proves broker execution.

### M10 — Observed practice execution and activation readiness

**Depends on:** for the initial account-path check, completed M01–M07 (including
strategy qualification and account preflight), M09's essential controller controls,
and authority to conduct practice execution. M08 and remaining M09 work are not
prerequisites for that initial check. Final qualification requires completed
M01–M09 and successful initial account-path evidence. This planning task authorises
no practice execution. Review any account-dependent change before using it.

- **Initial account-path check:** use M07's tested qualification initialization
  and invocation, the intended account binding and its single service. Observe
  long and short two-leg sets and a cross-currency set. Verify separate
  trade IDs, actual fills and units, fill-relative stops and Trade 1 target,
  Trade 1 take-profit followed by Trade 2's confirmed stop at its own entry
  during scheduled management, targeted closes, precision/restrictions and
  estimated versus broker margin. Check actual notebook records and transaction
  reconciliation directly; this evidence does not depend on a dashboard.
- **Final integration check:** after M08 and remaining M09 checks, observe a 16:50
  qualification run, both stages' captures and ordered progress, availability/skips
  across all 28 pairs, duration and reporting. Reconcile actual fills,
  closures, financing and applicable charges, including daily postings and
  closure summaries, through the final account snapshot and dashboard.

**Verification / exit:** retain actual request outcomes, broker IDs/transactions,
account boundaries, notebook records and discrepancies against the mapping below.
Read-only responses, `hedgingEnabled`, simulated fills and injected failures do
not replace observed execution. An incompatible path or unresolved result leaves
qualification incomplete; record the finding and return any change to review.
Passing the initial check does not complete M10 or permit ordinary activation.
Reuse its evidence only while the relevant code, strategy and account conditions
remain unchanged; recheck affected behaviour when later work changes them.

## Acceptance coverage and evidence

Use these distinct evidence labels:

- **Offline:** deterministic fixtures, identical-input lab comparisons and calendar
  calculations; no actual broker behaviour is claimed.
- **Host:** observed service/timer, permissions and maintenance checks without
  broker mutations. These supplement offline scheduling checks.
- **Practice read-only:** actual responses from the intended account in M04.
- **Practice execution:** actual orders, fills, transactions and observed run in M10.

| Scenario | Offline delivery/checks | Host or actual practice evidence still required |
| --- | --- | --- |
| A01 | M03 session/capture checks; M09 DST calendar cases | M09 dispatch; M04/M10 intended 16:50 captures and M10 run duration. |
| A02 | M03 exact events; M07 entry independence from Stage 1 | M10 run decisions and captures corroborate integration; controlled event variations remain offline. |
| A03 | M03 exact lab equivalence/count qualification; M05–M07 ATR isolation/frozen levels | M04/M10 real window availability in both stages, tied to the qualified manifest. |
| A04 | M07 no/confirmed/unconfirmed close and balance-failure cases | M10 purpose-labelled balance/margin requests and preserved sizing/reporting boundaries. |
| A05 | M06 home/cross-currency risk, precision, conversion failures and margin | M04 conversion checks/applicability; M10 initial long/short/cross-currency fills, precision and margin. |
| A06 | M06–M07 28-pair order, eligibility and complete-set checks | M10 initial distinct protected legs for both directions; final ordered run trace. |
| A07 | M05 opposite C1/Exit, simultaneous triggers and unavailable inputs | M10 targeted trade-ID closes and actual outcomes; event combinations are controlled offline. |
| A08 | M07 C1-close followed by either fresh direction/no event; unresolved survivor | M10 validates underlying close/entry operations; label any observed reversal separately from fixtures. |
| A09 | M07 Exit/TP/SL/mixed close followed by either fresh direction/no event | M10 actual closure causes and entry operations; no claim that every offline sequence occurred live. |
| A10 | M05/M07 TP, already-equal/closed, prior failure/uncertainty and next-run cases | M10 actual Trade 1 TP and surviving Trade 2 stop-to-own-entry confirmation. |
| A11 | M02/M05 both missing legs, mixed causes and missing evidence | M10 actual closing transactions, per-leg causes, times and fills. |
| A12 | M01–M02/M05–M07 commit failures, whole-set no-fill versus incomplete entry, uncertainty, no retries, disposition and interrupted qualification/activation | M09 essential exclusion before M10 initial mutations; M10 actual request/outcome mapping and any encountered failures. Fault injection remains offline. |
| A13 | M03/M06–M07 missing/untradeable inputs and no queued entry | M09 inactive-timer/next-dispatch evidence; M04/M10 current-session availability. |
| A14 | M02/M07–M08 pips, reductions, postings, deduplication, snapshot cutoff and qualification-to-activation totals | M10 initial notebook reconciliation; final complete ledger/balance and dashboard comparison, including financing/charges. |
| A15 | M07–M08 progress, read-only views, failures, WAL and reporting cutoff | M09 deployed permissions/staleness; M10 dashboard against recorded practice results. |
| A16 | M01/M02/M07 duplicate/mutated bindings, two independent configurations and unchanged qualification/activation identity | M04 intended account/currency match; M09 service isolation/maintenance. Repeat account and strategy qualification for each additional notebook. |

For each executed variation, record its acceptance ID, evidence label, date,
strategy/code/configuration identities, inputs/evidence location, run/set IDs,
expected and actual result, and pass/fail/blocked reason. Preserve non-secret
broker IDs and response evidence. Keep qualification fixtures and retained candles
separate from ordinary notebook storage; ordinary runs do not become a candle
archive. Link results from [status](STATUS.md) as they are produced.

Mark a scenario complete only when its required controlled checks and applicable
host/account evidence are recorded. The explicit A05 live applicability exceptions
do not waive its controlled matching-quote case or missing required conversions.
Unknown or unobserved outcomes remain pending, not passed.

## Qualification records and ordinary activation

M01 provides the records; M02 provides snapshot/import/reporting functions; M07
implements and checks the following procedure offline before any M10 execution.
It uses the design's single notebook, snapshot purposes and evidence references,
without a second trading service or a replacement notebook for the same account.

1. **Initialize qualification.** With maintenance exclusion established, validate
   the selected qualified manifest/count, registry and broker account/currency.
   Bind the notebook once to that controller/notebook/account/home currency and
   manifest. Keep ordinary activation time and activation baseline unset while
   collecting qualification evidence references. After preflight and operator
   resolution of existing trades/orders or unexplained activity, save a consistent
   account snapshot Q0 with qualification
   purpose. Commit Q0, its evidence reference and the initial imported-through
   cursor at Q0's transaction boundary together, before qualification orders.
   Reopening an initialized notebook preserves this baseline and cursor and
   reconciles forward; it never discards history or resets an interrupted attempt.
2. **Run explicit qualification.** M07's invocation requires this initialized,
   unactivated notebook, completed strategy qualification/preflight and the M10
   execution prerequisites. It uses the same binding checks, request guards,
   commit boundaries and controller functions. Record qualification run IDs in
   its evidence and retain attempts, fills, transactions, issues and snapshots
   in the same notebook. Ordinary invocation rejects missing activation; the
   qualification invocation cannot enable ordinary timers or run after activation.
3. **Report qualification separately.** Reconcile qualification postings after Q0
   through each successful snapshot using the normal ledger queries. Label these
   figures and journal activity as qualification. Before activation, ordinary
   experiment totals are unavailable; Q0 is never presented as its activation
   baseline. At activation, cap the qualification reporting interval at A0;
   later snapshots do not extend it. Retain the records and labels.
4. **Activate only after final qualification.** Under maintenance exclusion, require
   completed M10 and all required A01–A16 evidence, confirmed closure of qualification
   trades, no remaining qualification orders and evidenced disposition of issues.
   Reconcile through a fresh account snapshot A0, then atomically commit the
   ordinary activation snapshot/transaction boundary, evidence references and time.
   Keep the original identity/manifest and Q0 history unchanged; never rewind the
   import cursor. A failure before this commit leaves the notebook unactivated.
   A repeated activation request verifies the existing record without replacing A0.
5. **Start ordinary reporting and scheduling.** A0's realised balance is the opening
   balance; ordinary profit/loss and charges include only postings after A0 through
   the displayed reconciled snapshot. Qualification results are already reflected
   in that opening balance and are not counted again. Enable the ordinary timer
   only after activation commits and maintenance releases the notebook. Keep the
   no-missed-launch-replay behaviour and the approved trading workflow.

Controlled A12/A14/A16 transition checks cover interruption before/after the Q0
and A0 commits, an unresolved qualification set preventing activation, repeat
initialization/activation, and mismatched bindings. Use qualification profit of
+100 followed by ordinary profit of +20: qualification evidence retains +100,
the ordinary opening balance includes it, and ordinary realised profit is +20
exactly once. M08 verifies the corresponding labels and snapshot boundaries.
These are planned checks, not executed results or new trading rules.

Repeat qualification for each new notebook/strategy; keep existing controllers
on their original rules. Profitability is not an activation or acceptance test.

## Implementation handover

Implement one requested milestone per new chat. Read project guidance, current
status, this approved plan and the relevant design/acceptance sections. Keep the
work within that milestone, run its applicable checks and update status with
completed work, evidence, limitations and remaining dependencies. Stop for review
before proceeding to another milestone.

When the owner requests the next handover, provide a concise, self-contained
prompt naming the next milestone, its prerequisites, verification and stopping
point. Carry forward unfinished work, pending decisions and the scope of any
existing broker authorisation explicitly; do not imply completion or additional
broker authority through the handover.
After M10, provide a completion handover rather than inventing another milestone.

Approval does not select a strategy/lookback, prove account suitability or count
as application acceptance. Practice execution retains M10's authority and
qualification requirements; ordinary activation retains its separate prerequisites.

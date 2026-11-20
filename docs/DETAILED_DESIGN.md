# NNFX Practice Lab detailed design

Status: Approved by the owner on 16 November 2026.
This document defines the approved implementation details of the
[numbered workflow](ARCHITECTURE.md).
The [project brief](../PROJECT_BRIEF.md) remains authoritative for trading and
operating rules. No implementation or application acceptance is claimed here.

The first C1/Exit strategy, its qualified lookback and the intended practice
account's execution capabilities remain pending. The two-leg order path below
is conditional on evidence from that account. Design approval retains these
open dependencies; they must be resolved before ordinary trading.

## 1. Responsibilities and boundaries

Use one Python process per controller, two sequential child modules, one SQLite
notebook per account and a separate Flask/Jinja dashboard. A child is a recorded
stage within the master process, not another service or worker. Use ordinary
functions and explicit records; no queue, background reconciliation service or
strategy-selection framework is needed.

| Component | Responsibility and boundary |
| --- | --- |
| `master` | Load and validate the binding, create the run, call Manage Open Trades, obtain the step 4.1 balance, call Manage New Trades, and record final refresh and completion. Own the broker client and notebook connection. |
| `manage_open` | Steps 3.1–3.6: load registered sets, reconcile broker evidence, apply due stop-to-entry changes, then evaluate and close surviving pairs sequentially. |
| `manage_new` | Steps 4.2–4.5: visit all 28 pairs in brief order, check notebook eligibility, capture fresh inputs, calculate C1/ATR, size and establish eligible sets. Receive the immutable step 4.1 balance. |
| `strategy` | A self-contained, versioned copy of the selected lab calculations and required helpers. Pure candle-to-observation calculations; no broker or notebook access. |
| `broker` | Practice-only requests, account identity, decimal parsing, timeouts, response classification and transaction retrieval. Apply the mutation restrictions in the state rules; make no trading decisions. |
| `notebook` | Short SQLite transactions, attempt records, confirmed trade state, transaction import, ledger and read queries. No network calls while a write transaction is open. |
| `dashboard` | GET views over committed records. No private `.env`, broker client, controller invocation or write connection. |

Keep these modules in a small `nnfx_practice/` package, with `templates/` for
the dashboard, `strategies/<version>/` for reviewed calculation packages and
`var/notebooks/<notebook-id>.sqlite3` for data. The folder names are design
proposals, not existing runtime files. Strategy packages include provenance and
qualification references and do not import the sibling lab at runtime.

The existing Ubuntu host and service/timer arrangement remain as specified in
[architecture](ARCHITECTURE.md#runtime-and-deployment). The scheduler owns the
weekday 16:50 `America/New_York` launch, DST, no missed-launch replay and no
automatic restart. All runs use the single service instance for their controller;
independent accounts may run concurrently. Notebook maintenance follows the
exclusive operating procedure in [section 6](#6-failure-handling-and-operator-disposition).
No dashboard route starts either operation.

## 2. Configuration and activation

| Location | Required contents |
| --- | --- |
| `config.toml` | For each experiment: stable `controller_id`, `notebook_id`, notebook display name, `strategy_version`, and `connection_key`. Derive the notebook path from its validated ID. |
| Private `.env` | For each connection prefix: `ACCOUNT_ID`, `TOKEN`, `HOME_CURRENCY`, `LOOKBACK_CANDLES`. For example, `PRACTICE_A_LOOKBACK_CANDLES` is a field name, not a selected value. Owner-only access; never copy its contents into the notebook or logs. |
| Strategy manifest | Research-result identity, source commit, implementation/conversion/dependency hashes, parameters, output bindings, accepted C1/Exit rule definitions, lab numeric semantics, qualified total candle count and qualification evidence references. |
| Notebook activation record | Original controller/notebook/account/home-currency binding, immutable manifest copy/hash, baseline account snapshot and transaction cursor, account-specific execution qualification reference and activation time. |

Pin the client to `https://api-fxpractice.oanda.com`. Use the configured account
on every request, including when its token permits access to other accounts.
Account IDs belong in private configuration and the local binding; credentials
and authorization headers never belong in broker evidence. Display the notebook
name rather than connection information.

At activation and each run, validate unique controller, notebook and account
bindings across the registry, safe notebook paths, the database's original
binding, the strategy hash and the configured lookback against its qualified
value. Match OANDA's account ID and currency to the binding. A configuration
mismatch fails before trading requests. Record the failure in the existing
notebook when its identity is safe to use, otherwise in the service log.

There is no default strategy or guessed warm-up count. The qualified count is
the total window including the partial candle, at least 15 for ATR and potentially
longer for C1/Exit. A change to it, an indicator parameter or an accepted signal
rule creates a new strategy/controller/account/notebook combination. Token
rotation and display-name edits do not alter the immutable trading binding.

Before activating ordinary scheduled trading, record:

1. Strategy selection and identical-input lab equivalence, including the chosen
   rolling-window initialization and signal observations.
2. Read-only preflight on the intended dedicated account: identity, division,
   home currency, balance, existing trades/orders, all 28 instruments, precision,
   size limits, pricing, conversions and the intended partial candle. Include
   the account-specific `accountLoss` checks and applicability records in A05.
3. Observed execution qualification of the proposed two-leg path on that account,
   with long/short and cross-currency cases, protection, targeted closes, margin
   and ledger evidence. Identify qualification activity separately; reconcile
   and clear it before establishing the experiment baseline.

Neither a documentation example nor `hedgingEnabled` is proof of two-leg support.
The protected-size/FIFO restrictions and client-extension support described in
[architecture](ARCHITECTURE.md#integration-evidence-and-review-items) remain
account-specific. The suggested one-unit-increment difference for Trade 2 is
still a review option, not an enabled fallback. If the account requires a change,
bring the evidence and proposed adjustment to review before activation.

### Protected scheduled qualification and native activation

The owner's 20 November 2026 instruction adds automatic qualification scheduling.
Version-1 dated plans and their claims remain readable. Version-2 qualification
plans use a separate weekday timer targeting the existing controller service;
ordinary scheduling stays disabled. Each dispatch validates protected authority,
account/strategy/code/configuration identities, essential host evidence, the
clock, service process and approved New York minute. It creates an exclusive,
fsynced New York date claim before network activity. Existing claims survive
plan changes, failures and the transition to ordinary operation. A missed day
is never replayed. Later regular runs manage existing qualification trades with
the same reconciliation, attempt guards and operator disposition rules.

Both schedules are paused during local maintenance, with independent restoration
of their prior states after notebook release. A service mask excludes external
launches. Version-2 permits pin the tested kernel and code; a same-kernel reboot
can resume the regular schedule without login, while a changed kernel or code
requires refreshed relevant evidence. Prior startup and window observations
retain their original scope. Final host acceptance does not become a prerequisite
for initial qualification where the implementation plan excludes it.

The [native ordinary adapter](../nnfx_practice/ordinary.py) accepts only a separate
protected ordinary plan and final owner authorization. Its
[evidence verifier](../nnfx_practice/qualification_review.py) checks completed
prerequisite observations, the full reviewed notebook record digest, actual
long/short/cross-currency complete sets, distinct IDs/units and historical
fill-relative protection, sizing/margin evidence, confirmed scheduled stop-to-entry
and targeted closes, daily financing, a completed both-stage final run, retained
session claims and matching raw broker responses. It checks the current-kernel
startup/window evidence, traded dashboard comparison and reviewed A01–A16
observations and named tests from a retained passing offline suite. References
and pass flags alone are insufficient. Missing or inapplicable account evidence
requires review; the verifier never manufactures a waiver or strategy change.

Under maintenance, activation verifies those records, then reconciles a fresh
account snapshot and requires no trades/orders, unresolved attempts/sets or
issues. A0/evidence/time commit atomically. Repeat activation verifies the existing
record; it cannot replace A0 or its review. The activation command never enables
a timer. A native ordinary dispatch requires that committed activation and the
same protected review, uses the shared daily claim and existing master, and keeps
ordinary candle windows in memory. Commands and review-packet fields are in the
[README](../README.md#automatic-m10-qualification-and-ordinary-activation).

## 3. Run and calculation contracts

At step 2, create the master row and both child rows before account work. Save
UTC start time, New York session date, strategy/configuration/code identities
and the effective lookback once on the master. Record elapsed durations using
a monotonic clock on normal completion. A crash leaves unfinished rows and the
last committed progress; never manufacture a finish time or resume the old run.

| Workflow step | Inputs, action and durable result |
| --- | --- |
| 3.1 | Load registered sets with an open leg and both leg records, including closed Trade 1. Also load unresolved attempts/issues for reconciliation. Read broker state and transactions; commit confirmed activity and due stop changes before signal management. |
| 3.2–3.3 | For each surviving registered pair in brief order, fetch one candle window and independently evaluate Exit and C1. Commit observations and any close reasons before sending closes. |
| 3.4–3.6 | Close each confirmed surviving leg when either event is opposite to its direction. Record both triggers when both apply. Commit the pair's outcome before advancing. Uncertain closures leave that pair occupied or blocked. |
| 4.1 | After Stage 1 finishes, the master requests the realised account balance once, even with no trades or unresolved pair closures. Save the balance, response time and transaction ID as immutable sizing inputs. A failed request prevents Stage 2 and is not replaced with an old balance. |
| 4.2–4.3 | Visit all 28 pairs sequentially. Commit a skip for an occupied or blocked pair before making any pair-specific request. Otherwise fetch a new window and calculate C1/ATR solely from it and the bound strategy. |
| 4.4–4.5 | With a fresh event and valid ATR, obtain pricing/conversions and current margin, size and establish the set. Commit this pair's completed, skipped or failed outcome before advancing. |
| 5 | On normal loop completion, fetch final account state, import through its transaction boundary and save a reconciled reporting snapshot. Finish the stage/master rows. A failed refresh retains the earlier snapshot and records the failure. Never replace the sizing balance. |

An account-wide failure that ends Stage 1 early prevents the entry stage. A
Stage 1 that finishes with isolated pair failures still proceeds to 4.1. Margin
and reporting requests may return another balance; they are labelled by purpose
and never become a second sizing-balance request.

### Candle and signal inputs

One shared candle function returns an in-memory ordered window and capture
metadata. Request `D`, mid prices, `smooth=false`, alignment at 17:00 in
`America/New_York`, and `count=run.lookback`. The returned calculation window
must contain exactly the qualified count: the intended final partial candle
and `run.lookback - 1` completed bars, all ordered, non-duplicated and with valid
OHLC values. A different received count makes the input unavailable for that
pair and stage, even if it exceeds nominal indicator warm-up requirements.
Do not calculate on a shorter window or pad it to meet the count.
Store request/response UTC times, signal candle start, intended New York session
date, received count and data-validation result with the pair decision.

Identify the intended session from the broker candle start and New York 17:00
boundary, including DST and market weekends; do not subtract a fixed UTC day.
The signal candle must be incomplete and due to end at 17:00 on the run's New
York date. A fetch returning only completed candles or the next session makes
this stage's input unavailable. Do not use an older candle. After a valid capture,
use its signal through that stage's actions even if execution crosses 17:00.

Keep windows in memory; ordinary notebooks store observations, decisions and
entry ATR, not a candle archive. Controlled qualification fixtures may retain
their input candles separately for reproducible comparison.

The calculation result distinguishes `long`, `short`, `no_event` and
`unavailable`, with errors separate from ordinary no-event results. Save relevant
current/prior output operands and rule IDs. Preserve the lab's comparison and
transition helpers, including equality, missing operands and invalid simultaneous
directional outputs; do not invent an event precedence. Evaluate C1 and Exit
independently: one valid opposite event can require a close when the other
calculation is unavailable. ATR failure never suppresses a valid required exit.

Retain the lab's true-range candidate order, nine-decimal half-away-from-zero
comparison, full-precision winner on ties and `math.fsum` simple ATR(14).
Lift only the research assessment's fixed-length guard when packaging the pure
calculation. Convert its final finite ATR to a round-trippable decimal string at
the sizing boundary; do not change arithmetic inside the indicator package.
[Lab ATR rules](../../nnfx-indicator-lab/docs/standards/ASSESSMENT.md#true-range-and-atr)
and [signal helpers](../../nnfx-indicator-lab/nnfx/signals.py) are the reference.

Stage 2 does not receive Stage 1's indicator result or former direction as an
entry input. If flat and clear, either direction of its own fresh C1 event is
eligible after any closure reason, including re-entry in the former direction.
No event means no entry. A broker closure after Stage 1 that has not yet reached
the notebook can leave the pair conservatively skipped for this run.

## 4. SQLite records and state changes

Use SQLite foreign keys, WAL, short transactions and durable commits before
broker mutations (`synchronous=FULL`). Keep schema versioning simple and explicit.
Prices, units and monetary values are decimal text, broker IDs are text, and
times are UTC with broker timestamp precision preserved. JSON holds bounded
evidence and calculation details; fields needed for relationships, eligibility
and dashboard queries have explicit columns. No token or secret-bearing headers
are stored. Use decimal arithmetic outside the inherited lab calculations.

### Record definitions

| Table and key | Required fields and meaning |
| --- | --- |
| `notebook` — singleton | Schema version; immutable controller/notebook/account/home currency and strategy identity/manifest; activation/evidence references; baseline snapshot ID and transaction ID; mutable imported-through cursor. |
| `runs` — `run_id` | Strategy/config/code hashes, UTC start/end, duration, New York session date, effective lookback, status, last progress time, immutable sizing balance/time/transaction ID, final snapshot ID and refresh error. |
| `stages` — `(run_id, stage)` | `manage_open` or `manage_new`, status, start/end/duration, current step/pair, reconciliation progress, expected pair count and failure summary. |
| `pair_decisions` — `(run_id, stage, pair)` | Pair order, start/end, capture metadata, C1/Exit observations and operands, ATR/value validity, trigger reasons, sizing inputs, requested action, final outcome/reason and related set/issue IDs. |
| `trade_sets` — `set_id` | Entry decision/run/strategy, pair/direction, frozen ATR and executable stop distance, sizing balance reference, expected leg count 2, establishment status/time and terminal time. |
| `trade_legs` — `(set_id, leg_no)` | Leg 1 or 2; unique nullable broker trade ID; planned/initial/current units; last confirmed broker state/time/transaction boundary; entry fill/time; original stop, current stop and their order IDs; intended/confirmed target and order ID; stop-to-entry status; final exit summary and reason. Unknown values remain null. |
| `broker_attempts` — `attempt_id` | Run/stage/pair/set/leg, purpose, method/path and redacted payload, local/client IDs, prepared time, response time, HTTP status, OANDA `RequestID`, broker order/trade/transaction IDs, response evidence, outcome/error. |
| `broker_transactions` — broker `transaction_id` | Broker time/type/batch/request IDs, first import time and cumulative accepted non-secret transaction facts. Unique per notebook/account. Retain all transaction types in the imported interval. |
| `broker_transaction_observations` — `(transaction_id, body_json)` | Each distinct accepted source body, unmodified except secret redaction, with its first observation time. Repeated identical bodies do not create another row. |
| `fills` — `(transaction_id, broker_trade_id, effect)` | Open/reduce/close effect, order ID, units, per-trade actual price, time and broker reason; link to registered leg when known. Preserve every reduction, not only the final close. |
| `ledger_entries` — `(transaction_id, component_key)` | Signed home-currency amount, category (trading P/L, financing, commission, other charge, cash adjustment), optional trade allocation, source field and posted-versus-informational status. |
| `account_snapshots` — `snapshot_id` | Purpose, request/response times, broker transaction boundary, balance, unrealised P/L, margin, currency, relevant broker state and reconciliation status/error. Only reconciled snapshots qualify for the dashboard's latest account figures. |
| `issues` — `issue_id` | Pair or account scope, code, first/last observed times, related set/leg/attempt, broker evidence, open/resolved status, operator disposition/identity/time and supporting broker IDs. |

Derive finished, skipped and failed pair counts from `pair_decisions` with a
committed final outcome, grouped by run and stage. An in-progress decision does
not count. Store no separate finished/progress counters. Stage 1's expected
pair count is the number of surviving registered pairs selected after 3.1;
Stage 2's is 28. Retain the stage's current step/pair and the run's last progress
time to show work underway between outcomes.

M05 storage detail: a stop-to-entry attempt at 3.1 precedes the surviving-pair
decision. It stores the registered set, leg and broker trade ID; its nullable
decision-pair field is empty and its pair is obtained from `trade_sets`. Its
issues retain the pair explicitly. Reconciliation progress records these stop
actions separately, so only the selected surviving pairs contribute to the
Stage 1 decision count. Signal-close attempts link to their pair decision.

M06 storage detail: `pair_decisions.sizing_json` retains the instrument,
pricing/conversion and both purpose-labelled margin reads, the exact sizing
calculation, Trade 1 verification reads and the establishment proof's transaction,
batch, trade and order IDs. `trade_sets.run_id` references the immutable 4.1
balance. Attempts retain the exact market/stop and target payloads; transaction,
fill and leg tables retain the confirmed effects. No schema change or live
execution enablement is required for this scripted candidate boundary.

M07 storage detail: schema 2 adds `run_invocations`, keyed by run ID, with an
ordinary/qualification label and qualification prerequisite references. New
master/child/invocation rows share one commit. Version-1 writer migration checks
the binding and preserves existing rows; legacy component-only runs have no
invented invocation label. Q0/A0 references and their bound snapshots become
immutable once recorded. The sizing-summary evidence is purpose-labelled and
remains `pending`, outside reconciled reporting queries; the master keeps its
balance, time and transaction boundary. Margin evidence remains on pair decisions.
Qualification initialization commits Q0 and its initial cursor together. Activation
uses the reconciliation transaction to commit A0, imported history/cursor,
references and activation time together. Reporting retains the plan's Q0/A0
intervals. Implementation references are in the
[local interfaces](../README.md#master-and-local-maintenance-interfaces).

Transaction comparison storage: schema 3 adds `broker_transaction_observations`
and seeds it with the existing transaction bodies and import times. Writer
migration from schema 1 or 2 runs atomically after binding validation; it preserves
Q0/A0, cursor, runs, issues and derived records. New readers accept schemas 2 and 3
without migrating. The deployed schema-2-only dashboard reader must be updated
before the controller migrates its shared notebook. Observation evidence is
included in qualification record digests and collector exports. Each accepted
merge, observation, fill/ledger projection and history advance shares the same
commit; a conflict or balance failure rolls them all back.

Original protective levels are the first confirmed broker levels and remain
immutable. Intended levels stay in the decision/attempt even if the broker
returned different ones. Later transactions update current levels without
rewriting the original. Broker fills are the authoritative exit facts; a
controller's signal-close reasons are retained separately from the actual
broker cause, which may instead be a stop, target or operator closure.

Use uniqueness for broker trade IDs, attempt client IDs and transaction-derived
records. Enforce one set reserving a pair with a partial unique index on
`trade_sets(pair)` while its terminal time is null. A set reserves the pair from
its pre-order commit until all legs are confirmed closed/not opened and its
entry uncertainty is resolved. Terminal sets do not erase open issues.
Index open issues by pair and runs/decisions by start time and run ID.

### State rules

This table is the authoritative home within this design for mutation retries,
recovery restrictions and entry blocks. The request and failure procedures use
these rules when deciding whether an action is eligible.

| Record | Allowed changes and evidence |
| --- | --- |
| Run/stage | `not_started` (child only) → `running` → `completed`, `completed_with_errors` or `failed`; an unstarted child can be `blocked` by an earlier fatal failure. A `running` row with no finish after process interruption remains visibly unfinished and is not resumed. Account-wide uncertainty or unusable notebook writes ends the run and prevents further broker mutations. |
| Attempt | `prepared` is committed before sending and means outcome not yet known. Its creating operation may send it once; a prepared record left by an interruption is unresolved even if the crash may have preceded sending. Broker evidence can establish `confirmed`, `rejected`, `cancelled` or `pending`; a timeout/ambiguous response becomes `unknown`. Resolve earlier unresolved attempts through broker evidence. Never automatically resend an uncertain or failed mutation, issue a repair order or create a replacement leg. |
| Set establishment | `pending` → `complete` only with evidence both distinct legs and all required protection were established together; otherwise `incomplete`. A failed or uncertain entry/protection step stops the entry sequence and creates an issue if effects or required protection remain incomplete/unresolved. A wholly rejected/no-fill entry is `not_opened` and releases its reservation once both legs are known not opened. A formerly complete set stays complete historically as its legs close. Interrupted pending sets become incomplete/uncertain on reconciliation, with an issue. |
| Leg | Starts planned with no broker ID/state. Only broker evidence sets `open` or `closed`, or establishes that an attempt never opened a trade. Missing from an open list does not overwrite the last confirmed state with closed; attach an unresolved issue and preserve the last evidence. |
| Stop-to-entry | After confirmed Trade 1 TP, record a closed Trade 2 or an already-equal confirmed stop without a mutation. Before preparing any due change for a surviving Trade 2, check its earlier stop-change attempts and issues. A prior failed change or an unresolved attempt (`prepared` after interruption, `pending` or `unknown`) stays with the operator and prevents automatic reissue. An eligible adjustment moves `not_due` → `due` → `confirmed` on broker confirmation; rejection/uncertainty sets `failed`/`unknown` and opens an issue. Later broker evidence may confirm the stop or closure without clearing the operator-owned issue. |
| Signal close | Apply the attempt guard separately to each surviving leg. A rejected or unresolved close creates a pair issue and is not resubmitted automatically. Other confirmed surviving legs remain eligible for their independently required exit; an issue with protection alone does not suppress that exit. |
| Issue | Remains open across runs. Reconciliation can add evidence and correct actual trade state. An operator disposition with matching broker evidence is required to clear an entry block for uncertain orders, incomplete sets or failed protection. Never delete the failure history. |
| Entry eligibility | Query the records: no open or unresolved registered leg, no reserved set and no open issue for the pair. Do not store a separately toggled eligibility flag. Clearing an issue cannot make an open leg eligible, and acknowledgement without broker evidence cannot resolve uncertainty. A confirmed no-fill rejection remains a visible failure but needs no lasting block when all outcomes are known and no issue remains. |

### Commit boundaries

1. Commit the pair observation/decision, set and both expected legs before the
   first entry. Commit each mutation's own attempt before sending it.
2. Release the SQLite write transaction, make one broker change, then commit
   the response, confirmed transactions/fills, leg/protection changes and any
   issue together. Do this before the next broker change.
3. When importing an interval of broker history, commit its transaction rows,
   derived state/ledger entries and the imported-through cursor atomically.
   A response's high transaction ID alone must never advance this cursor.
4. Commit the pair outcome and last progress time before visiting the next
   pair. Dashboard counts derive from those committed outcomes. An interruption
   between steps leaves enough identity and intent to reconcile, with no claim
   that the entry or run completed.

## 5. OANDA requests and reconciliation

All paths below are relative to `/v3/accounts/{boundAccountID}`. Use a reusable
HTTPS connection, bounded connect/read timeouts and no secret-bearing request
dumps. Apply the [state rules](#state-rules) before every mutation. Correlation
IDs identify attempts; they do not override the attempt guard.

| Purpose | Request and evidence |
| --- | --- |
| Account state | `GET /` (the account path itself) supplies open trades, pending orders and account values at its `lastTransactionID`. Use for 3.1 and final reporting. |
| Metadata | `GET /instruments` for all permitted instruments before pair processing; retain the precision/limits/margin inputs actually used with sizing decisions. Translate brief names such as `EUR-USD` to OANDA `EUR_USD`. |
| Candles | `GET /instruments/{instrument}/candles` with the parameters in section 3. One request per eligible pair/stage; no reuse of Stage 1's window in Stage 2. |
| Sizing balance / margin | `GET /summary`, explicitly labelled `sizing_balance` once at 4.1, `margin_before_set` per intended set and `margin_before_leg_2` after Trade 1 protection. |
| Pricing / conversions | `GET /pricing?instruments={instrument}&includeHomeConversions=true`; keep time, tradeable status, bid/ask and required base/quote conversions. |
| History | `GET /transactions/sinceid?id={cursor}`; use transaction pages/ID ranges for bounded imports. Targeted `GET /transactions/{id}` supplies missing referenced evidence. |
| Trade/order verification | `GET /trades/{tradeID}` and `GET /orders/{orderID}` as needed, together with transactions; do not infer closure from a 404 or absent open-list entry. |
| Entry | Conditional `POST /orders` using the request sequence below. |
| Protection / close | `PUT /trades/{tradeID}/orders` for dependent orders; `PUT /trades/{tradeID}/close` with `units="ALL"` for each surviving leg. |

The full account representation provides a single boundary for trades and orders,
avoiding unrelated list snapshots. The API definitions support these requests;
they do not establish account suitability. See [account endpoints](https://developer.oanda.com/rest-live-v20/account-ep/),
[pricing endpoints](https://developer.oanda.com/rest-live-v20/pricing-ep/),
[trade endpoints](https://developer.oanda.com/rest-live-v20/trade-ep/) and
[order definitions](https://developer.oanda.com/rest-live-v20/order-df/).

### Reconciliation procedure

Start from the registered notebook sets, then reconcile all account activity,
including unfinished attempts and unexpected trades/orders:

1. Capture the account snapshot and its boundary `S`. Retrieve all transaction
   history after the saved cursor through `S`, with no transaction-type filter.
   Import in broker sequence and keep batches together. When a response extends
   beyond `S`, retain that evidence for a subsequent consistent boundary rather
   than mixing it into the snapshot being checked.
2. Match account, trade, order, transaction and available client/request IDs.
   Deduplicate by broker IDs. Response-supplied transactions may already be
   stored; importing them again changes neither units nor monetary totals.
   Apply the field-aware comparison policy below to response/history echoes and
   duplicate IDs within a fetched batch. Keep each actual source body as evidence;
   use their compatible cumulative facts for projection. The
   [21 November diagnosis](STATUS.md#transaction-import-failure-on-21-november)
   owns the observed practice difference and offline validation.
   Advance the cursor only over fully retrieved and applied history; do not
   assume IDs are consecutive integers or skip to the highest ID seen.
3. Compare registered legs/protection with the snapshot at `S`. For missing legs,
   retrieve the trade's closing transaction references and actual fills. For
   both missing legs, check both stop orders and retain separate actual causes.
   A missing closure creates an issue; confirmed closures can release occupancy.
4. Unknown account trades/orders produce issues on their instruments. Retain
   their broker identities without inventing a registered strategy set. If an
   inconsistency cannot be isolated to a pair, stop the run. Do not cancel or
   adopt unexpected activity automatically.
5. Record the reconciled snapshot and refresh time only when its transaction
   boundary and monetary records agree. Isolated pair issues remain visible
   alongside the snapshot and keep those pairs blocked. Missing account history
   or an unexplained balance difference makes account state unreliable.

**Repeated-transaction comparison policy (owner agreed 21 November).**

- Identity, instrument, time, reason, trade membership and protection instructions
  remain strict. Missing required/core information is not treated as a default.
  Changed quantities or prices remain conflicts.
- Compare known decimal fields by exact decimal value, accepting spelling changes
  such as `0.00` versus `0.0000`. This covers fill and per-trade amounts, order and
  protection prices/distances, transfer/financing totals and known nested quote/
  conversion numbers. IDs and arbitrary strings never receive numeric coercion;
  null, booleans, JSON numbers and invalid decimal strings are not equivalent.
- Match `tradesClosed` by trade ID, allowing array reordering but rejecting
  duplicate IDs or changed membership. Other arrays retain their original order.
- Known supplemental fields may be added or omitted in a later echo without
  discarding earlier facts. These are fill/per-trade commission, guaranteed
  execution fee and dividend adjustment; per-trade realised P/L and financing;
  half-spread cost and initial margin; client-extension tags/comments; and fund
  transfer comments. Shared supplied values must agree. Spread cost and initial
  margin are descriptive amounts, not additional account debits.
- The four observed conversion-cost names (`baseFinancingHomeConversionCost`,
  `guaranteedExecutionFeeHomeConversionCost`, `homeConversionCost`,
  `plHomeConversionCost`) are accepted as zero-valued supplements in fills and
  their opened/reduced/closed trade details. Their nonzero accounting treatment
  remains unqualified, so a nonzero/invalid value blocks import. Unknown field
  additions/removals/changes also remain conflicts; there is no ignore-all rule.
- New supported monetary components use the existing ledger mappings and unique
  source keys. A nonzero posted addition to an existing transaction requires its
  broker `accountBalance` evidence and an ID beyond the previously imported
  cursor. Complete history must reconcile before the cursor or reporting snapshot
  advances. Already imported account totals cannot be rewritten. Later per-trade
  allocations remain informational and never repost an account total. Nonzero
  fill allocations require their account-level total; once all affected trades
  supply a component, their sum must match that total. Existing
  ledger entries must match; they are never silently overwritten or ignored.

The explicit field locations are implemented in
[transaction_records.py](../nnfx_practice/transaction_records.py). A conflict
records the transaction ID and field paths. The policy covers representations
and supported accounting enrichment; it grants no order retries, replacement
legs, issue resolution or strategy changes. The
[OANDA transaction definitions](https://developer.oanda.com/rest-live-v20/transaction-df/)
describe the known numeric, fee, spread, margin and per-trade fields; actual
nonzero conversion-cost semantics still need account evidence.

If the cursor is already beyond an older response, never roll derived trade
state back; obtain a fresh snapshot or end the read with a visible failure.
Likewise, importing older history must not overwrite a leg/order state already
confirmed at a later transaction boundary. Fill and ledger inserts remain unique
by their source identities. Before a dependent broker change, fill any history
gap through the preceding response's boundary so earlier account activity is
accounted for; if that read fails, preserve the response evidence and end the run.
Broker changes can occur after a snapshot. Subsequent request results and their
transaction sequence establish what actually happened, including price exits
during a close or protection request. Request eligibility follows the state rules.
[OANDA transaction retrieval](https://developer.oanda.com/rest-live-v20/transaction-ep/)
defines the history endpoints and page boundaries used here.

### Sizing and price precision

Let `B` be the fixed 4.1 balance, `a` the frozen signal ATR, `q` the quote-to-home
loss conversion and `u_step = 10 ** -tradeUnitsPrecision`. Always obtain `q`
from the quote currency's `accountLoss` in the current OANDA `homeConversions`
response, including when quote and home currency match. Require a present,
finite, positive factor; otherwise skip the entry with its reason. Do not
substitute a local factor of 1 or another conversion field. Home-currency
`accountLoss` is expected to be 1; verify it where applicable under the A05
practice-account preflight checks.
[OANDA home conversions](https://developer.oanda.com/rest-live-v20/pricing-df/#HomeConversions)

The proposed executable-price rounding is nearest tick with half-away-from-zero
ties. Record raw and rounded values; reject zero/wrong-side levels or unsupported
distances.
This specifies broker tick handling and does not replace lab numeric semantics.

```text
budget per leg = B × 0.01
d = round_to_price_tick(1.5 × a)
units = floor((budget / (d × q)) / u_step) × u_step
planned risk per leg = units × d × q  <= budget
```

Bound each leg by the broker order limit and the combined intended set by the
remaining instrument position limit, rounding units down; reject if below
minimum or inputs are non-finite/non-positive. Apply direction to the
order units only after sizing. No combined account risk limit is introduced.
Persist B, a, d, q, quote currency, pricing response time, unit precision/limits,
units and each leg's planned risk. The proposed default is equal per-leg units,
subject to account qualification; no silent size change to satisfy an unknown
account restriction.

Estimate both legs' margin using absolute base units, base-to-home
`positionValue` (1 for home base) and the applicable account/instrument margin
rate. Record that rate's source. Require current available margin for the set;
recheck remaining margin before Trade 2. The balance returned by those checks
does not change B. A post-Trade-1 margin failure creates an incomplete set; it
does not shrink or queue Trade 2. Broker acceptance remains authoritative.

Targets use Trade 1's actual entry plus/minus `a`, rounded to a valid tick on
the correct side. Initial stops use the executable distance `d` from each leg's
own fill. Confirm actual levels and retain differences. If an entry price cannot
be represented exactly for the agreed stop-to-entry request, treat it as a
qualification/protection issue rather than silently selecting a different level.
Planned risk describes sizing inputs, not a guarantee against slippage or charges.
[Instrument metadata](https://developer.oanda.com/rest-live-v20/primitives-df/)
supplies the instrument precision and size fields.

### Conditional two-leg request sequence

Only the intended account's verified path may be activated. For the candidate
native v20 path, commit the expected set and legs, then:

1. Prepare Trade 1's attempt, send a `MARKET` order with signed units, `FOK`,
   `OPEN_ONLY`, supported order/trade client extensions and
   `stopLossOnFill={distance: d, timeInForce: GTC}`. Confirm the distinct opened
   trade, actual units/fill and live fill-relative stop; commit them.
2. Prepare a target attempt and set Trade 1's GTC `takeProfit.price` via its
   dependent-order endpoint. Omit `stopLoss` so its existing stop remains.
   Verify and commit the target before proceeding. The stop-only interval is
   explicit; a rejected target, including a price move past it, leaves an
   incomplete set for the operator.
3. Confirm Trade 1 still survives with its required orders, obtain the remaining
   margin, prepare Trade 2's attempt and send the same market/stop mechanism
   without a target. Confirm its distinct identity, actual fill and initial stop.
4. Use transaction order and trade/order evidence to establish that both legs
   and required protection existed together. Commit establishment before the
   pair outcome. A price exit after that point is ordinary management even if
   first observed in this response; an exit before establishment is incomplete.

Apply the state table's establishment and attempt rules at each step; an HTTP
success alone does not make Trade 2 eligible. A response that reduces another
trade, has the wrong units or lacks a separate trade ID is an
account-path failure, not a successful set. Keep all actual broker effects.
OANDA documents stop distance relative to the open price in
[protection details](https://developer.oanda.com/rest-live-v20/transaction-df/).

### Closures and the stop-to-entry adjustment

After confirmed Trade 1 take-profit, check Trade 2 at 3.1 even when the take-profit
was recorded on a previous run. Apply the state table's stop-to-entry rule,
including its earlier-attempt and issue check, before preparing a request.
Only if that rule permits a due adjustment, submit the dependent stop-order
change to Trade 2's exact entry and verify the new order ID/price or an
intervening closure. Record broker observations under the leg/issue rules.
No candle or new ATR is needed.

For signal exits, save C1/Exit triggers and apply the state table's signal-close
guard per leg. Request `ALL` for each eligible confirmed live trade ID, Trade 1
then Trade 2 where both survive. Commit each result before the next and apply
the resulting attempt/leg/issue state. Never infer the actual cause from the
request alone, or describe a requested stop change as confirmed.

## 6. Failure handling and operator disposition

The [state rules](#state-rules) determine retries, entry blocks and disposition.
This table describes reporting and continuation for each failure condition.

| Condition | Record and continuation |
| --- | --- |
| Occupied/blocked pair | Stage 2 skip, referring to leg/set/issue; no pair-specific broker request. Continue in order. |
| Missing partial candle/history, unavailable event, invalid entry ATR, unavailable market/pricing/conversion, insufficient pre-set margin | Specific skip reason and available inputs. No queued entry. Continue other pairs when account state remains usable. Signal-calculation errors are visible failures, not normal no-event signals. |
| Confirmed rejected/no-fill entry | Failed attempt/decision with broker rejection; apply the set-establishment rule and record the resulting reservation state. |
| One-leg fill, missing protection, uncertain request or failed stop change | Preserve actual effects and apply the relevant set/attempt/stop/issue rules. Other pairs may continue while account state and notebook writes remain usable. |
| Confirmed close rejection or unresolved close | Record failure and last confirmed units; apply the signal-close and issue rules. |
| Authentication, account-binding, account-wide history or balance failure | End the run; no new orders using stale account inputs. A balance failure at 4.1 blocks Stage 2. |
| Notebook write failure | Make no further broker mutations. Exit with a redacted service error; the prior committed attempt remains evidence if the broker already acted. The dashboard may show an unfinished run because the failure itself could not be persisted. |
| Interrupted process | Next regular run gets its own candle, imports broker activity and exposes unfinished attempts/incomplete sets under the run and attempt rules. |
| Final refresh failure | Keep the last successful reconciled snapshot and its time, mark the refresh failed and finish with errors where writes remain possible. |

The operator resolves orders/trades in OANDA between runs. A small local notebook
maintenance action records the issue ID, explanation, operator/time and broker
evidence after a read-only broker reconciliation. It sends no orders and applies
the state table's issue and entry-eligibility rules when recording disposition.
The dashboard only shows the issue and disposition.

The M07 local action records one disposition at a time against a fresh reconciled
snapshot. It retains broker trade/order/transaction identities and any unsent
planned legs. A prepared entry remains uncertain without matching broker evidence.
For an uncertain dependent target on a trade now confirmed closed, disposition
records the terminal evidence and prior attempt outcome; it cannot reopen or
repair the trade. Pending orders still prevent disposition. Unsupported or
unattributed uncertainty remains open for investigation. Reconciliation alone
never clears these issues. The tested local lock is shared with master startup;
M09's [systemd adapter](../nnfx_practice/host.py) supplies real service/timer
exclusion. The [host evidence](STATUS.md#m09-host-operation-and-maintenance-exclusion)
distinguishes verified user-scope fixtures from unmet system deployment checks;
the [README](../README.md#notebook-maintenance-on-the-deployed-host) owns commands.

Keep the controller excluded for the whole maintenance operation, including
broker-evidence reads and notebook writes. Pause its timer first, then confirm
that its service is inactive with no launch pending. If the timer cannot be
paused or the service is active, defer maintenance without interrupting a trading
run. Do not manually start the service during maintenance. Restore the timer's
prior state only after maintenance has finished and released the notebook,
including on failure. Retain the agreed no-missed-launch-replay behaviour;
restoring the timer does not launch a catch-up run.

## 7. Monetary records and the read-only dashboard

Derive the journal from broker fills and posted ledger entries. For a fully
closed leg with several reductions, use the absolute-unit-weighted exit price
and final closing time, retaining individual fills and mixed reasons in detail.
Apply the brief's signed long/short pip formula with `10 ** pipLocation`.
An open or partly reduced leg has no final realised exit price/pips/result;
already posted reductions and charges remain visible in its activity and enter
account-summary totals at the reporting boundary defined below. Missing broker
amounts are unknown, not zero.

Use the activation snapshot as the opening balance for this notebook's reporting
period. Reconcile subsequent signed postings to each account boundary:

```text
opening balance + trading P/L + financing + other signed charges
                + cash adjustments = broker realised balance
```

Normalise charges to signed balance effects (for example a positive broker
commission amount is a debit), retaining the raw field. Import each posting
once. Trade/position allocations explain account amounts; do not also count the
parent aggregate. Cumulative trade financing/realised totals are cross-checks,
not extra postings. Retain unallocated amounts at account level. Spread is
already reflected in fills. Unknown monetary fields or reconciliation differences
remain visible and must not be hidden with a balancing adjustment. Qualification
must verify the intended account's financing mode and charge mapping against
actual transactions, including daily postings and closure summaries.

For account summaries, select the latest successful reconciled snapshot and its
transaction boundary `S`. Take balance, unrealised P/L and home currency from
that snapshot. Include posted ledger entries after the activation baseline and
through `S` in broker transaction order. Sum positive trading-P/L postings as
realised profit and negative postings as realised loss, with financing,
commissions/other charges and cash adjustments separate. Calculate net posted
result over the same interval. All these figures share the snapshot's refresh
time and boundary, including when a later refresh fails.

Keep newer confirmed fills, trade state and ledger activity visible in the
journal with their broker timestamps and a label that they postdate the account
snapshot. Do not include them in the account-summary totals until a reconciled
snapshot covers them. For example, a confirmed close posting +100 after `S`
remains visible when the final refresh fails, while the displayed balance and
summary profit remain at `S`. This display cutoff never rolls back current
trade state or affects trading eligibility.

| GET view | Content and source |
| --- | --- |
| `/controllers` | Latest controller/master run, both child stages, durations, current step/pair, counts derived from pair decisions, skips/failures and outstanding issues. Stage 1 distinguishes reconciliation from surviving-pair progress; Stage 2 shows finished outcomes out of 28. History lists only run metadata and problem indicators, with links to full details. |
| `/controllers/<controller_id>/runs/<run_id>` | Read-only details for one run in the registered controller's notebook. Load its stages, decisions, exact timings and reconciliation records only when this separate page is requested. Unknown controllers/runs cannot select other notebooks; unavailable notebooks show an explicit error. |
| `/notebooks` | Name, linked controller, immutable strategy and signal rules; balance and separate realised profit/loss at the common reporting boundary above, refresh time and failure/staleness indicators. |
| `/notebooks/<id>` | Account-summary figures at that same reporting boundary, grouped trade sets with complete expandable records, issues, request outcomes and broker-backed activity detail, with newer activity labelled. Strategy/rules and qualification identity remain available below. |

The owner accepted the Controller layout update on 20 November 2026. Lead with
the notebook name, secondary controller identity, account-data freshness and open
issues, followed by the latest run and two stacked stage summaries. Empty issues
use one line. Keep stale/failed refreshes, latest-run failed pair outcomes and
unfinished decisions visible. Place “Previous run history” immediately beneath the latest
run's “Run and reconciliation details”, ahead of account-data details. Show the
previous-run count and an empty message when there is only one run; exclude the
latest run from history. History lists dates, status, duration, invocation mode
and error/unfinished indicators. Each run link opens a separate window or tab
(browser preference), with no embedded or prefetched historical run content.
The controller request reads summary metadata and problem flags only for older
runs; it does not load their stages, decision reasons or reconciliation records.
Expand the history list by default when it contains errors or unfinished records.
The latest-run view and separate historical-run page use native expandable
details to retain full IDs, exact timestamps
and durations, current/last steps and pairs, reconciliation records and resolved
issues. Main timestamps remain explicitly New York time with offset; readable
duration rounding never changes stored values. Display recorded skip reasons,
not an assumed lack of signals. “No new entries” requires a completed entry stage
with all expected pairs skipped and no trade set recorded for that run. A stage's
“Account records matched to broker” label requires its referenced snapshot to be
reconciled.
These summaries describe saved outcomes, not current service liveness.

The owner requested clearer Controller wording on 20 November 2026. Display entry
outcomes recorded as `skipped` as “with no entry”, retaining their exact recorded
reasons. For open-trade management, the same stored outcome means exit inputs were
unavailable: display “exit check(s) unavailable”, never “no action required”. Label
pair progress “checked”, explain that it includes failed checks and unavailable
inputs, and continue excluding decisions without a final outcome. A completed
empty management stage says “No open trades to manage”; omit its zero-only outcome
line. Use plain language for saved records, read-only access, account freshness,
reconciliation and operator responses. Preserve exact issue codes, IDs and times in
the expandable records. These presentation changes do not alter stored outcomes,
trading rules, reconciliation evidence or the qualification lifecycle.

The Notebooks overview follows the same account-first order: notebook name and
journal link, freshness/warnings and open-issue count, then account balance,
realised profit and realised loss at the common reporting snapshot. Label the
reporting period explicitly. Before ordinary activation, explain that the figures
are qualification results; do not display unavailable ordinary totals as zero.
After activation, show ordinary results first and retain capped qualification
results in a separate disclosure. Balance is neutral, without a profit-style
plus sign; result amounts retain signed green/red text and zero stays neutral.
Thousands separators improve readability without rounding or dropping stored
monetary precision. Financing and other charges remain separate in the journal.
Latest saved-run status and a controller link follow the figures. Strategy version,
candle count and indicator names stay visible below; full signal rules/parameters
and exact reporting snapshot IDs/boundaries/times remain in expandable details.
The trading journal follows the same presentation: freshness, visible issues and
latest saved-run status, then balance, unrealised result and separate realised
profit/loss. Balance/charge components and capped qualification results have
their own disclosures. Group both legs by set, newest sets first, and keep mixed
open/closed sets together under “Open or unconfirmed sets”. A set is “Finished”
only when every leg is closed or confirmed not opened. Show pair, direction,
recorded entry time and entry status above compact trade rows. Each row shows
status, entry/current units, current protection and final result. Closed trades
do not imply a missing active stop or unconfirmed planned target; their recorded
protection remains in the details. Stop-to-entry failures/unknown outcomes stay
visible. Small screens stack these fields with labels instead of requiring
horizontal scrolling.

Native per-trade disclosures retain identifiers, exact timestamps, original and
current protection, final exit evidence, charges and fills. Account activity and
request outcomes follow the trades in expandable sections. Show a top warning for
activity after the account snapshot and expand its activity section by default;
uncertain or unsuccessful requests also expand by default. Posted amounts remain
distinct from informational allocations. Strategy settings and notebook activation
records follow these sections. Presentation does not change accounting calculations
or the reporting boundary.

The complete journal fields are set ID, broker trade ID, leg number, pair, direction,
initial/current units, entry time, status, actual entry, original/current stop,
Trade 1 target, actual final exit time/price/reason, signed pips and home-currency
trading result, financing and other charges. Planned/unconfirmed legs are clearly
labelled and have no invented broker IDs or fills. The retained set ID groups legs.

Display UTC records in New York time with offset, explicitly labelled; local
browser timezone does not alter trading dates. Use signed text plus green/red
for positive/negative values. Show last successful refresh time and age, latest
run outcome and any failed/unfinished refresh. If a scheduled weekday launch
has passed without a later snapshot, flag staleness; this is display-only and
never starts a catch-up run. With no snapshot, show unavailable figures.

Use short, consistent read transactions and read-only SQLite connections that
can see committed WAL updates. Allowlist notebook IDs from the ordinary registry,
escape stored text and serve on the separate trusted-LAN port. No route accepts
trading/configuration/issue-resolution writes, and the dashboard service cannot
read the private credentials. Preserve the reference dashboard's simple
navigation, labels and tables; no live broker polling is required.

### Dashboard deployment authority

On 20 November 2026, the owner authorized a narrowly scoped deployment command
for `codexdev`, preserving the dashboard's separate `nnfx-view:nnfx-read` runtime
identity. This is a local operator command, not a dashboard control or trading
permission. The host permission requires one administrator installation; observed
installation and verification belong in [status](STATUS.md#scoped-dashboard-deployment-access).

- The sole sudo grant is the fixed root-owned
  `/usr/local/sbin/nnfx-dashboard-deploy` command **with no arguments**. No Python,
  shell, source-tree script, generic service command or timer operation is granted.
- Its isolated Python interpreter accepts bounded JSON text through stdin. Only
  `nnfx_practice/dashboard.py` and the nine named HTML/CSS files in its fixed
  allowlist may change. There is no caller-selected executable, installation path,
  service, environment, dependency installation or root-run test/import hook.
- Root copies submitted content as data into a protected dashboard release. Only
  the restricted `nnfx-view` process executes dashboard code. The service retains
  its read-only notebook access, blocked credential/control paths, denied outbound
  connections and existing LAN/port restrictions. Strategy, broker/controller,
  startup code, dependencies and the qualified trading installation cannot be
  submitted through this interface.
- A one-time setup changes the dashboard working directory to the protected
  `/opt/nnfx-dashboard/current` link. Subsequent deployments atomically switch
  that link and restart only `nnfx-practice-dashboard.service`; they never edit
  service definitions or reload the service manager. Releases are root-owned,
  immutable to `codexdev` and service users, and retained for rollback.
- The helper rejects stale expected releases, unknown/duplicate fields, oversized
  input, unsafe paths/ownership/permissions/links, changed non-dashboard files,
  changes to the pinned qualified trading files or service restrictions, concurrent
  deployment, active trading runs, pending trading jobs and the 16:35–17:10 New York
  weekday trading window. It does not pause, enable or disable trading schedules.
- Fixed localhost GET checks use no proxy or redirect and bounded responses.
  Failed restart/page/preservation checks restore the preceding dashboard link and
  restart that service. Receipts retain hashes, release identities and rollback
  outcome, including an explicit failed-rollback result requiring administrator
  attention. The helper does not open credentials, notebooks or protected plans.

The one-time installer validates the existing restricted service and qualified
code paths. It may tighten only the existing root:root `0775` package directories
`/opt/nnfx-practice/nnfx_practice` and `/opt/nnfx-practice/strategies` to `0755`;
all other unsafe ownership, links or permissions are refused. These mode-only
changes are retained on later failure and do not change application file hashes.
The installer prepares the
protected helper/configuration/link and validates the exact sudo rule before
granting access. Its setup checks and optional pending dashboard update are
separate outcomes. Revoking the sudo rule removes deployment access without
changing the dashboard or trading services. Qualified-code upgrades, new host
bindings and changes beyond the allowlist require separate administrator review.
Commands and the frozen setup bundle are in the
[README](../README.md#enable-scoped-dashboard-deployment).

## 8. Acceptance test design

The [acceptance checklist](ACCEPTANCE.md) owns the scenarios. The following maps
each to controlled inputs and observable assertions, without claiming execution.
Use the real controller functions, a temporary notebook, a scripted broker
transport and a controllable clock. The transport records ordered calls and can
return broker-shaped fixtures or interrupt at a commit boundary. Assert both
requests and committed state, including the absence of prohibited requests.
Calculation qualification uses the selected lab code on identical candles;
substituting test observations only exercises controller flow.

| ID | Controlled setup / variations | Assertions and retained evidence |
| --- | --- | --- |
| A01 | Calendar cases around March/November DST and weekends; captures just before/after 17:00, completed-only and next-session responses. | Timer resolves to weekday 16:50 New York; captures identify the intended partial candle, wrong-session inputs are unavailable, UTC capture/session/duration records agree. Retain calendar output and later actual timer dispatch evidence separately. |
| A02 | Fresh crossing/transition, continuing state, equality and missing operands. Repeat identical Stage 2 candles with different Stage 1 decisions/former directions. | C1/ATR results and chosen direction remain identical; only a fresh valid event opens a set. Save decision operands, rule identity and ordered request trace. |
| A03 | Qualified window versus selected lab on identical inputs; ATR ties/gaps; insufficient bars, including a response shorter than the qualified count but longer than nominal warm-up; configured lookback mismatch; invalid ATR with valid opposite event; changed ATR after entry. | Both stages require exactly the bound count, with preceding completed bars and the intended final partial candle; a shorter response is unavailable input and produces no signal-based action. Compare lab outputs/events/ATR exactly under inherited semantics; invalid ATR blocks entry but not a valid exit, frozen levels stay fixed, configured count mismatch fails startup. Strategy/count qualification remains pending. |
| A04 | First run/no trades, confirmed closures, unresolved pair close; balance-read failure; changing later summary/report balances. | One `sizing_balance` call follows finished Stage 1; successful read permits other eligible pairs despite unresolved close; all sizing uses B, margin reads stay current, final snapshot does not overwrite B. Failed 4.1 produces no Stage 2 pair requests. |
| A05 | Home/quote match with returned `accountLoss = 1`; cross currency with distinct `accountLoss`, `accountGain` and `positionValue` values; long/short, unit/tick boundary and minimum/maximum limits, inadequate margin. For both currency cases omit the quote entry or its `accountLoss`, and supply zero, negative, non-finite or malformed factors. | Per-leg decimal risk is at most 0.01B; units are base units rounded down. Both directions use the returned quote-currency `accountLoss`; record currency, factor, response time and executable distance. Missing/invalid factors yield a recorded skip and no order, including for home-matching quotes; no fallback to 1 or another field. Margin still uses base-currency `positionValue`. Compare margin estimate and actual account margin during practice qualification. |
| A06 | All 28 pairs with a mixture of open leg, issue, flat no-event and eligible long/short cases; include a leg closed at broker after Stage 1 but still open locally. | Exact brief order; blocked pairs have zero pair-specific calls; each eligible capture is fresh. Each outcome commits before the next pair starts. Complete entries have two broker IDs and required protection. Late unobserved closure leaves the local occupied pair skipped. |
| A07 | Surviving longs/shorts with opposite C1 only, Exit only, both opposite, one unavailable, same-direction and persistent states. | Correct opposite convention; all confirmed survivors close once when required; both triggers retained without duplicate closes. Pair result precedes next pair's candle call; data failure is visible. |
| A08 | Stage 1 C1 close, then independent Stage 2 fresh long, short or no event; repeat with one surviving leg/unconfirmed close. | Flat/clear pair follows either fresh direction, including its former direction; no-event produces no entry; survival/uncertainty causes a skip before candles. Assert actual close facts separately from entry decision. |
| A09 | Exit-triggered, TP, SL and mixed broker closures followed by each fresh C1 direction or no event. | Closure reason/former direction never supplies an entry signal. Only the new capture drives entry once flat/clear; a closure alone produces no order. |
| A10 | Trade 1 TP newly discovered/already recorded; Trade 2 live, already at entry, closed before change or closing during change. Repeat the next scheduled run with an earlier rejected stop change or an unresolved prepared/pending/unknown attempt; also return later broker confirmation of entry stop or closure. | Exactly one eligible due stop request to Trade 2's own entry. Already-equal/closed cases and prior failed/unresolved attempts send no stop request, including on the next run. Later broker evidence updates the actual stop/closure but leaves the operator-owned issue open until disposition; its entry block remains. |
| A11 | Both legs absent with SL/SL, TP/SL, operator or mixed reasons; one absent without closing evidence. | Resolve by both registered IDs and closing transactions; save per-leg cause/time/fill. Missing evidence remains unresolved; absence alone never sets closed or enables entry. |
| A12 | Reject first/second order; target failure; stop failure; 2xx cancel/pending; timeout after accepted order; crash before send, after fill commit, after target commit and before Trade 2; SQLite failure after broker action. Also price exit before/after establishment, duplicate history import, next-run stop cases from A10, and maintenance attempted with an active service or unpaused timer. | No mutation replay or replacement leg; prepared attempt/set/leg evidence survives. Complete means both legs/protection proved; earlier exit/incomplete/unknown retains a block. Import twice changes no totals. Cursor never passes unapplied history. Operator disposition needs evidence and cannot begin until maintenance exclusion is established. Other pairs continue only with usable account state and writes; fatal failure leaves visible error/unfinished rows. |
| A13 | Untradeable price, unavailable candles, inactive timer spanning a weekday launch and next regular launch. | Skip with reason, no queued order, no missed-launch replay; next run has its own session/capture. Use scheduler dispatch evidence in addition to offline call assertions. |
| A14 | Known long/short fills on ordinary and JPY pairs, split reductions, open legs, positive/negative P/L, financing, commission, cash transfer and duplicate transaction delivery. Save snapshot S, then commit a +100 closure and fail the final refresh; subsequently provide a successful snapshot covering that closure. | Check pip formulas/weighted exit/final time; open-leg final outcome remains blank. All account-summary components reconcile at S while the newer +100 appears only in timestamped journal activity. The later successful snapshot includes it once in summary profit/balance. Allocations and summaries are not double-counted; currency/sign/colour correct. Verify mapping against actual practice transactions. |
| A15 | Running/completed/failed/unfinished stages; committed success/skip/failure decisions alongside an unfinished decision; missing snapshot; the failed-refresh sequence from A14; missed expected run and DST display dates. | Derive finished/skip/failure counts from committed final pair outcomes, excluding the unfinished decision, with no stored finished counter. Show balance and totals at the same snapshot boundary, newer journal activity explicitly labelled, refresh failure, New York offset and unfinished records. GET routes work; mutation requests cannot start trading or write records. Test without credentials and with read-only database permissions, including live WAL reads. |
| A16 | Two distinct controllers/accounts/notebooks; duplicate account binding; wrong account/currency response; attempted strategy/rule/count mutation of an existing binding. Schedule a timer launch during maintenance, including maintenance failure, and test a timer initially paused. | Independent requests and records stay isolated. Invalid/mutated bindings fail before orders. A new strategy requires a new combination while the original manages under its stored version. No controller launch overlaps maintenance reads/writes; restore the prior timer state only after maintenance releases the notebook, with no missed-run replay. Record binding hashes and account-scoped request traces. |

For A05, perform a read-only check on the intended practice account. Retain
pricing responses requested with `includeHomeConversions=true` for permitted
pairs, including cross-currency quotes. Confirm that each requested quote
currency's `accountLoss` is present, finite and positive.

Require a live matching-quote case only when a permitted pair has the account's
home currency as its quote. Otherwise record that case as not applicable with
the account currency and reason; its absence does not prevent activation.
Independently, when the home currency appears as either base or quote in a
permitted pair, verify that currency's returned `accountLoss` is exactly 1.
For an EUR account, use the EUR conversion entry from EUR/USD for this check;
actual EUR/USD risk sizing still uses the USD entry. If no permitted pair
contains the home currency, record the live identity-factor check as not
applicable too.

A missing/invalid required conversion entry or a home-currency factor other
than 1 where that check applies leaves preflight incomplete and prevents
activation. Retain the controlled matching-quote test in the A05 table for every
configuration, including when the live case is not applicable. These are required
checks, not observed results.

Practice execution verification supplements these controlled checks. On the intended
account, record individual order/trade/transaction IDs and request outcomes for
both entry directions, a cross-currency set, fill-relative stops/target, stop to
entry, targeted closes, and complete ledger reconciliation. Include observed
16:50 candle captures and run duration across all pairs. Do not treat fabricated
timeout/rejection fixtures or research price simulations as broker evidence.

For each executed scenario record ID/variation, offline or practice classification,
date, strategy/code/configuration identities, input/evidence location, run/set IDs,
expected versus actual result and pass/fail/blocked reason. Keep qualification
fixtures/evidence separate from ordinary candle storage and omit credentials.
Link executed results from [status](STATUS.md); all scenarios currently remain
unexecuted.

## 9. Review boundary

The owner approved the controller contracts, schema/commit boundaries,
conditional broker path, failure behaviour, dashboard queries and acceptance
mapping on 16 November 2026. Implementation planning is the next stage and will
begin in a separate chat. The first strategy
and its qualified count, account preflight and observed execution qualification
remain explicit dependencies; this design does not fill them with assumptions.
No implementation plan, runtime code, account provisioning or broker orders are
part of this document change.

# Detailed design

Approved 16 November 2026; later comparison/history decisions incorporated.
[Brief](../PROJECT_BRIEF.md) owns trading rules; [architecture](ARCHITECTURE.md) owns
workflow/presentation. [Status](STATUS.md) records operation and the evidence
limits for each account.

## Configuration and records

Public `config.toml` binds controller/notebook IDs, name, strategy version and
connection key. Owner-only `.env` supplies prefixed ACCOUNT_ID, TOKEN,
HOME_CURRENCY and LOOKBACK_CANDLES. Pin requests to api-fxpractice.oanda.com and
the bound account, even with shared tokens. Exclude credentials/headers from evidence.

Manifest freezes research/source, conversion/dependency hashes, parameters, output/
rule identities, numeric semantics, qualified count/history and evidence references.
Startup validates unique bindings, safe paths, notebook identity,
manifest/count and broker account/currency before trading. Log mismatches only in
a safely bound notebook or redacted service log. Token/name changes preserve
binding; strategy/rule/parameter/count/origin changes need a new one. No defaults.
[Candle/ATR contract](ARCHITECTURE.md#candle-and-signal-inputs) owns calculation semantics.

One `var/notebooks/<notebook-id>.sqlite3` per account uses foreign keys, WAL, short
transactions and synchronous=FULL. IDs/decimal prices/units/money are text; UTC
preserves broker precision. JSON holds bounded evidence; relationships use columns.
No network inside a write transaction.

| Record | Durable meaning |
| --- | --- |
| `notebook` singleton | Schema, immutable controller/notebook/account/currency/manifest, Q0 and historical A0/evidence/time, imported-through cursor. |
| `runs`, `stages`, `run_invocations` | Run/config/code/strategy, count, UTC/session/duration, fixed sizing balance/time/boundary, snapshot/error, stage progress, mode/prerequisites. |
| `pair_decisions` | Run/stage/pair/order, capture and current/prior operands/rule IDs, ATR validity, triggers, sizing, action/outcome/reason and related set/issues. |
| `trade_sets`, `trade_legs` | Expected two legs, direction, frozen ATR/distance, run/balance reference, establishment/terminal time; unique broker IDs, planned/initial/current units, confirmed fills/state/boundary, original/current protection/order IDs, stop-to-entry and final exit. Unknown stays null. |
| `broker_attempts` | Local/client identity, run/stage/set/leg/pair, purpose, redacted method/path/payload, prepared/response times, HTTP status, RequestID, broker IDs/body and classified outcome/error. |
| `broker_transactions`, `broker_transaction_observations` | Unique broker ID, cumulative accepted facts; distinct redacted source bodies keyed by ID/body with first observation time. |
| `fills`, `ledger_entries` | Unique transaction/trade/effect: units/price/time/cause. Unique transaction/component: signed home amount, category/allocation/source, posted/informational. |
| `account_snapshots`, `issues` | Snapshot purpose/time/boundary/amounts/state/reconciliation; issue scope/code/identities/evidence, first/last observation and operator disposition/time. |

Progress derives from final pair decisions: Stage 1 survivors after 3.1; Stage 2,
28 pairs. A 3.1 stop attempt links its set, not a decision; issues name the pair.
Reconciliation progress stays separate from counts.
Sizing JSON retains metadata/conversions, both labelled margin reads, Trade 1
verification and establishment transaction/batch/trade/order proof.

Schema 2 adds invocation labels and immutable Q0/A0; master/children/invocation
commit together. Legacy component runs receive no invented mode. Schema 3 seeds
source observations atomically after binding validation, preserving all records/
baselines/cursor. Readers accept schemas 2/3 without migration; deploy compatible
reader before writer upgrade. Review digests/exports include observations.

## Run and commit contracts

Create master/children before account work with UTC start, New York session,
identities and count; duration uses a monotonic clock. Crashes stay unfinished;
never resume run IDs. [Workflow](ARCHITECTURE.md#numbered-workflow) owns sequencing.
Keep pending sizing evidence outside reporting; later balances never replace it.
Fatal Stage 1/balance failure blocks entry; isolated pair failure can continue
only with reliable account reads/writes.

1. Commit observations/triggers, reserved set/both planned legs and each mutation's
   own attempt before sending. Release the write transaction for the one send.
2. Commit response, confirmed facts/fills/protection/issues together before another
   change. Fill history gaps first; a response's high ID never advances the cursor.
3. Atomically commit complete history, source observations, projections and cursor;
   conflict/balance failure rolls everything back.
4. Commit pair outcome/progress/time before advancing. Final reporting imports to its
   snapshot boundary; failed refresh retains the last good snapshot.

## State rules

HTTP success is not proof; these rules own retries and eligibility.

| Record | Allowed transition and evidence |
| --- | --- |
| Run/stage | Child `not_started` → `running` → `completed`, `completed_with_errors` or `failed`; earlier fatal failure can leave a child `blocked`. Interrupted running rows remain unfinished. Account-wide uncertainty/write failure ends mutations. |
| Attempt | Commit `prepared`; only its creator may send once. Interrupted attempts stay unresolved even if possibly unsent. Evidence establishes confirmed/rejected/cancelled/pending; ambiguous response/timeout is unknown. Never automatically resend failed/uncertain mutations, repair orders or replace legs. |
| Establishment | Pending → complete requires both distinct legs/protection proved together. Failed/uncertain steps stop entry; unresolved effects/protection need an issue. Interrupted pending sets reconcile as incomplete/uncertain with an issue. Wholly rejected/no-fill is not_opened; release requires both legs known never opened and no issue. Filled Trade 1/rejected Trade 2 stays incomplete after closure; exits never erase historical completion. |
| Leg | Only broker evidence sets open/closed/not_opened. Missing from open list preserves last confirmed state and creates uncertainty; absence/404 never proves closure. |
| Stop-to-entry | Confirm Trade 1 TP; closed Trade 2/already-equal stop needs no request. Prior failed or prepared/pending/unknown change prevents reissue. Confirm the new stop ID/price or intervening closure from broker evidence; rejection/uncertainty creates failed/unknown issue. Later confirmation does not clear it. |
| Signal close | Guard each surviving leg separately. Rejected/unresolved close creates an issue and cannot automatically repeat; other independently eligible legs may close. Protection issue alone never suppresses an otherwise valid exit. |
| Issue/eligibility | Derive eligibility from records, never a mutable flag. Entry requires no open/unresolved leg, reserved set or open pair issue. Reconciliation never clears issues. Evidenced disposition resolves only its issue without deleting failure history or overriding occupancy/uncertainty. |

Unique broker/client/derived IDs prevent duplicates. A partial unique set index
reserves each pair until all legs are closed/not opened and entry uncertainty
resolved; terminal sets retain issues. First confirmed protection stays immutable;
attempts retain requests, evidence updates current levels. Signal reasons
remain separate from actual broker closure cause.

## Reconciliation procedure

At boundary S capture full account trades/orders/amounts. Under `/v3/accounts/{boundAccountID}` use `GET /`,
`/instruments`, `/summary`, `/pricing?instruments={instrument}&includeHomeConversions=true`,
instrument candles, `/transactions/sinceid?id={cursor}` or bounded pages/ranges,
targeted transaction/trade/order GETs. Retain pricing time, tradeable status,
bid/ask and base/quote conversions. Translate `EUR-USD` to `EUR_USD`. Metadata
precedes pairs; label summary reads sizing_balance, margin_before_set or margin_before_leg_2.

Import unfiltered history after the cursor through S in broker order/batches.
Retain beyond-S evidence for a later consistent boundary. IDs may be sparse:
never infer missing transactions merely from integer gaps or advance to the
highest observed ID. Require complete retrieval and all referenced/known facts;
unobserved omissions with no balance effect or reference cannot be inferred.
Match account/trade/order/transaction/client/request identities and deduplicate.
For missing legs retrieve closing references/fills, checking both stops when both
legs are absent. Preserve each cause; unresolved legs block their pair.

Unexpected trades/orders produce instrument issues without automatic adoption or
cancellation. Unattributable activity, missing history or unexplained balance
makes account state unreliable. Publish a snapshot only when its history and money
reconcile. Isolated pair issues may coexist with a reconciled snapshot.
Older observations/history must not roll back newer confirmed leg/order state;
if a snapshot precedes the cursor obtain a fresh one or fail visibly. Failure to
fill history through a prior response ends dependent work while retaining evidence.

### Repeated transaction policy

Owner agreed field-aware comparison on 21 November; later single-close evidence is
incorporated. [transaction_records.py](../nnfx_practice/transaction_records.py) owns
explicit field locations; arbitrary differences remain conflicts.

- Identity, instrument, time, reason, trade membership and protection remain strict;
  missing core fields or changed prices/quantities conflict. Known decimal strings
  compare by exact value, including nested price/conversion/fee fields. No coercion
  of IDs, arbitrary strings, null, booleans, JSON numbers or invalid decimals.
- Match `tradesClosed` by unique trade ID; reject duplicates/membership changes.
  Other arrays retain order. Apply the same comparison within a fetched batch.
- Known supplements may appear/disappear without erasing facts: fill/per-trade
  commission, guaranteed execution fee, dividend adjustment; per-trade P/L/financing;
  half-spread cost/initial margin; client tags/comments and transfer comments.
  Shared supplied values must agree. Spread/margin descriptions are not extra debits.
- Accept zero-valued `baseFinancingHomeConversionCost`,
  `guaranteedExecutionFeeHomeConversionCost`, `homeConversionCost` and
  `plHomeConversionCost` on fills and opened/reduced/closed details. Nonzero support
  is limited to a fill closing exactly one trade, opening/reducing none, with
  accountBalance, matching transaction/trade nonzero P/L and identical
  plHomeConversionCost/homeConversionCost at both levels. Cost must be nonpositive
  and no larger than absolute P/L; financing/guaranteed-fee conversion components
  are zero at both levels. These disclosures are already included in P/L, never
  additional debits. Complete history must explain transaction/snapshot balances.
  Other nonzero shapes, invalid values and unknown changes block import.
- New posted amounts use unique existing mappings; a nonzero addition requires
  broker accountBalance and a transaction beyond the prior imported cursor.
  Never rewrite completed account totals. Later allocations are informational;
  nonzero fill allocations need their account total and complete allocations must
  sum to it. Existing postings must match, never silently overwrite or ignore them.

Keep distinct redacted bodies/cumulative facts. Conflicts name ID/paths and roll
back the import. Comparison permits no retry, replacement leg or issue resolution.

## Sizing and two-leg entry

Let B be the fixed 4.1 balance, a frozen signal ATR and q the returned quote-currency
`accountLoss`, always finite/positive, even for a home-matching quote. Never substitute
1, accountGain or positionValue. [A05](ACCEPTANCE.md#a05-sizing-and-margin) owns live
identity-factor/applicability checks. Round price ticks nearest, half-away-from-zero;
retain raw/rounded values and reject zero/wrong-side/unsupported distances.

```text
budget = B × 0.01
step = 10 ** -tradeUnitsPrecision
d = round_to_price_tick(1.5 × a)
units = floor((budget / (d × q)) / step) × step
planned risk per leg = units × d × q <= budget
```

Bound order size and combined remaining instrument position limit, round down and
reject below minimum/nonpositive/nonfinite inputs; apply direction afterwards.
Default equal units remain conditional on account evidence; no silent size fallback.
Retain B/a/d/q, currency, pricing time, limits/precision and risk. Margin uses base
`positionValue` (1 when base is home), applicable instrument/account override rate
and its source. Require current margin for both legs, recheck before Trade 2 without
changing B. Failure after Trade 1 means incomplete, not a smaller or queued leg.

After reserving both legs, each step uses the commit/attempt guards:

1. Trade 1 `MARKET`, signed units, `FOK`, `OPEN_ONLY`, supported order/trade client
   extensions and GTC `stopLossOnFill.distance=d`; confirm distinct ID/units/fill/stop.
2. Set GTC takeProfit.price at its actual fill ± a, valid tick/correct side, through
   `PUT /trades/{id}/orders`, omitting stopLoss. Verify before proceeding. The
   stop-only interval is explicit; target rejection leaves an incomplete set.
3. Verify Trade 1 survives protected, recheck margin, send Trade 2 by the same
   market/stop mechanism with no target. Confirm distinct ID/units/fill/stop.
4. Prove from transaction order and trade/orders that both legs/protection existed
   together. Earlier price exit is incomplete; exit after establishment is normal.

Reduction of another trade, wrong units or missing ID/protection is a path failure;
retain actual effects. Stops use each actual fill and d; later ATR changes nothing.
Scheduled TP management needs no candle/new ATR and requests Trade 2's exact entry
stop only when eligible; unrepresentable entry is an issue, never a substitute level. Signal close uses
`PUT /trades/{id}/close`, `units="ALL"`, Trade 1 then Trade 2, confirming each.
A queued close still occupies the pair; an intervening closure retains its actual
cause. Planned risk never guarantees realised loss or zero after an entry stop.

## Failure and disposition

Unavailable input/market/conversion or pre-set margin produces a reasoned skip;
calculation errors remain failures. Isolated pair failures may continue; binding,
authentication, history/balance or write failure ends reliable account work.
A write failure after broker action leaves committed intent and redacted service
error; the dashboard may remain unfinished.
Local disposition under [maintenance exclusion](OPERATIONS.md#maintenance-and-evidence-collection)
uses fresh read-only reconciliation and stores issue/operator/time/explanation
and matching terminal/restored-protection evidence. It sends no orders. It can
record unsent planned legs or an uncertain target on a confirmed closed trade;
prepared entry, pending orders, unsupported/unattributed uncertainty stay open.
A restored stop does not release an open leg. The dashboard only observes.

## Monetary records

Closed legs retain reductions, absolute-unit-weighted exit price, final time and
mixed causes; pips use `10 ** pipLocation` per the brief. Open/part-reduced legs
have no final exit/pips/result; posted reductions/charges still enter totals.
Missing values stay unknown.

Opening balance + trading P/L + financing + other signed charges + cash adjustments
must equal realised balance. Normalize charges, preserving raw fields. Count posted
amounts once; allocations/cumulative trade totals only explain/cross-check them.
Keep unallocated account amounts.
Spread is in fills; unknown money or unexplained differences remain errors.

Use [practice totals from Q0](IMPLEMENTATION_PLAN.md#practice-lifecycle); preserve legacy intervals read-only.
Summaries end at reconciled snapshot S: balance, unrealised result, currency/time,
net posted result, positive/negative trading postings and distinct financing/charges/cash.
A +100 close after S stays visible in activity but outside summary profit until a
covering snapshot; failed refresh preserves S. Display cutoffs never rewind trade
state or change eligibility.

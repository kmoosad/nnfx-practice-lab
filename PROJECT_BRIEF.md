# NNFX Practice Lab project brief

Status: Final, version 1. Accepted on 10 November 2026 and updated with the owner's architecture review decisions on 15 November 2026. The owner clarified the single-table journal and filter requirement on 25 November 2026 (UTC).

## Purpose and principles

Run a forward test of a manually selected C1 and Exit indicator combination from `nnfx-indicator-lab`, using current OANDA market data and an OANDA practice account. Record actual execution and account results in a digital trading notebook.

Keep architecture, design, code and operation extremely simple. Use a repeatable account, controller and notebook configuration so additional independent practice experiments can be added without duplicating the application. Detailed architecture and concurrency choices follow brief finalisation.

This project uses practice accounts. A future real-money system is outside this release.

## Strategy selection

Select the indicator combination manually through work with Codex. Record its source research result, exact indicator implementations, parameters and accepted C1 and Exit signal rules against the notebook. A different strategy, including a change to Exit rules, requires a new controller with its own practice account and notebook. The existing controller continues to manage its trades under its original rules.

Use the trading and signal semantics of `nnfx-indicator-lab`, with the execution timing and actual broker-fill behaviour specified here. The lab currently assesses four pairs; this project extends the selected combination to the 28 pairs below. Its practice results therefore cover a broader market set.

For a history-dependent combination, the owner authorized additional history
support on 27 November 2026. Its manifest pins the research dataset's first candle.
Each calculation retains every supplied candle from that origin through the
current partial candle; earlier candles in the requested window do not initialize
the indicators. The full origin must remain available in the configured window.
For this history mode, omit historical candles starting Friday or Saturday at
17:00 New York, matching the research dataset's weekday series. Record the
excluded count. The current partial candle retains the existing strict session
validation, and C1, Exit and sizing ATR use the resulting weekday series.
If it is missing, report unavailable input rather than reset or truncate the
indicator history. This preserves the selected indicator rules and parameters;
changing the origin requires a new immutable strategy binding. Ordinary candle
windows remain in memory, without a new persistent indicator-state store.

## Accounts and permitted pairs

Each configured master controller is linked to one distinct OANDA practice account and its notebook. An individual master run is one execution of that controller. OANDA supplies the actual account balance, including the first run's balance.

The assigned controller is the only source of new trade entries on its practice account. The operator may resolve issues with existing trades or orders between controller runs.

Only these pairs may be traded:

EUR-USD, GBP-USD, AUD-USD, NZD-USD, USD-CHF, USD-JPY, USD-CAD,
EUR-CHF, GBP-CHF, AUD-CHF, NZD-CHF, CAD-CHF, EUR-GBP, GBP-JPY,
GBP-AUD, GBP-CAD, GBP-NZD, EUR-JPY, CAD-JPY, AUD-JPY, CHF-JPY,
NZD-JPY, EUR-AUD, EUR-NZD, AUD-NZD, EUR-CAD, AUD-CAD, NZD-CAD.

A trade set consists of Trade 1 and Trade 2 for one pair, direction and entry event. At most one trade set may remain open for a pair within an account. Either surviving trade keeps that pair occupied.

## Execution time and market data

Start the trading process Monday through Friday at 4:50 pm in `America/New_York`, following New York daylight-saving changes. The controller relies on the scheduler for start time. Evaluate that day's still-forming daily candle during this run. Record run duration for observation. The candle boundary is 5:00 pm New York time.

Fetch one OANDA daily mid-price candle window for each evaluated pair in each stage, using the controller's configured lookback. It includes the current partial candle and enough completed bars to initialise C1 and Exit, apply their signal rules and calculate ATR. Evaluate crossings and transitions on the current partial candle. Keep the price series in memory for the calculation and record the resulting signals, decisions and entry ATR in the notebook.

Entry and indicator-exit decisions occur during this scheduled run. Stop-loss and take-profit orders are held with OANDA and may execute between runs. Reconcile their actual results during trade management.

If the market or an instrument is unavailable, record the reason and skip its new entry rather than queueing it for a later opening.

If the server is unavailable, the next regular scheduled run uses its own partial candle.

## Trading sequence

The master controller executes Manage Open Trades, refreshes the balance and executes Manage New Trades. Manage New Trades prepares entry inputs and handles each pair in turn. The master records the outcome and ends the run after Manage New Trades finishes. Each child records its progress, results and failures.

### Manage open trades

1. Start with registered trade sets in the notebook that have an open leg. Group them by pair and reconcile their trade IDs with OANDA's trades, orders and transactions. OANDA determines actual trade status, fill prices and execution times.
2. For any registered leg missing from OANDA's open list, check the broker's closing transactions. If both legs are missing, check whether each stop-loss order executed and record each actual closure reason. Keep a missing leg unresolved until its status is confirmed.
3. If OANDA confirms that Trade 1 closed by take-profit and Trade 2 remains open, move Trade 2's stop to its own actual entry price during the 4:50 pm run. Record the confirmed stop change. This adjustment does not require a completed daily candle. If Trade 2 has already closed, record that closure instead.
4. Process surviving pairs one at a time in the order listed above. For the current pair, use the partial daily candle from OANDA to calculate Exit and C1. An opposite Exit event or opposite C1 event closes every surviving trade in the set.
5. Record the current pair's closure outcome, actual closing fills where available, and the triggering reasons before advancing to the next surviving pair.

An Exit event's direction follows the lab convention: a Short event closes longs, and a Long event closes shorts. A continuing indicator state is not a new event.

### Manage new trades

Repeat the steps below for all 28 permitted FX pairs in the order listed above. Finish the current pair's entry decision and outcome before processing the next pair.

1. Check the reconciled notebook for the current pair. If it has an open leg or an unresolved broker issue, record a skip and move to the next pair without a pair-specific OANDA request. Otherwise fetch a fresh partial candle and history using the configured lookback.
2. Calculate the C1 event and entry ATR using only the candles just fetched and the configured indicator and signal rules. An ongoing bullish or bearish state does not create another entry.
3. For an eligible long or short event with valid ATR, calculate units and check current available margin for the intended two-trade set. A blocked pair advances to the next pair in the loop.
4. Open the two trades in the signal direction and record their individual broker identities, fills and attached protection.

The fresh C1 event calculated during Manage New Trades determines the direction for any eligible flat pair, including a pair that closed earlier in the same run. Both directions are eligible regardless of the previous trade direction or closure reason. A closure alone does not create an entry.

## ATR, position sizing and protection

Use the exact true-range and simple-average ATR(14) calculation and precision rules from `nnfx-indicator-lab`. Calculate entry ATR from the signal candle used during the run and retain that value for the trade set. Missing or invalid ATR prevents a new entry but does not prevent a required exit.

Each trade's planned loss at its initial stop is at most 1% of the sizing balance. The intended two-trade set therefore has up to 2% planned initial risk.

After Manage Open Trades finishes, request the actual realised OANDA account balance once, regardless of the closure outcomes. A successful balance refresh starts the new-trade loop. An unresolved closure blocks new orders for its pair. Use the refreshed balance for all new entries and reversals in the run, checking available margin again before each set. The balance includes the effect of closed trades and excludes unrealised profit or loss.

Calculate units of the pair's base currency from the risk budget and stop distance by converting quote-currency loss to the account's configured home currency. Use the home currency for margin and monetary results. Respect broker precision and round units down where necessary to remain within the planned risk budget.

| Rule | Trade 1 | Trade 2 |
| --- | --- | --- |
| Direction | C1 signal direction | Same direction |
| Initial stop distance | 1.5 × signal ATR | 1.5 × signal ATR |
| Planned initial risk | Up to 1% of sizing balance | Up to 1% of sizing balance |
| Take-profit distance | 1 × signal ATR | No take-profit target |
| After Trade 1 takes profit | Closed | Move stop to its own entry price at the scheduled management run |

Stops and targets are relative to each trade's actual entry price. Long stops are below entry and targets above; short stops are above entry and targets below. Later ATR changes do not move the original levels. Trade 2's agreed move to entry is the stop adjustment; no trailing-stop rule is added.

Each eligible pair may have its own 2% trade set, subject to available margin. There is no combined account risk cap in this release. Such a cap may be added in a future version.

Record actual broker fills, including differences from requested levels. The 2% figure describes planned initial stop risk, not a guaranteed realised-loss limit. A stop placed at entry does not imply that actual execution or the result after charges will be exactly zero.

## Notebook and observational dashboard

Use the existing NNFX dashboard at <http://192.168.51.10:8877/> as the presentation reference. The new dashboard is purely observational and does not start runs, change strategies or place or modify trades.

The Controller page shows master runs, child-process progress, completion status, timing and failures. The Notebooks page lists each notebook's name, linked controller, strategy and signal rules, account balance, realised profit and realised loss. Clicking a notebook opens its detailed trading journal.

The detailed notebook shows account balance, unrealised result, strategy rules and last refresh time, together with one trade table containing all recorded trades. Filters narrow the displayed records. The table contains:

- Shared trade-set ID, individual trade ID and leg number.
- FX pair, direction, units and entry date and time.
- Status, actual entry price, original stop, current stop and take-profit target where applicable.
- Actual exit date and time, exit price and exit reason.
- Realised pips and realised result in the account's home currency, with financing and other applicable charges distinguished.

For a closed long, pips equal `(exit price − entry price) / pip size`. For a closed short, pips equal `(entry price − exit price) / pip size`. Use the instrument's pip size. Show positive results in green and negative results in red; open trades have no realised exit outcome.

Keep realised profit, realised loss, financing, other charges and unrealised results distinguishable so totals can be reconciled with OANDA. Show failed or stale information clearly.

## Simple failure handling

Reconcile broker activity during normal scheduled trade management and retain the identities and outcomes of order requests. An entry is complete only when the required trades and protection are confirmed.

Record controller errors, including rejected orders, uncertain responses, incomplete two-trade sets, failed stop adjustments and missing data. A controller may exit on error. An interrupted run can remain recorded as unfinished. The operator handles uncertain orders, incomplete entries and failed protection changes in OANDA. Block new entries for the affected pair while the issue is open. Automated recovery is outside this release.

## Project organisation

Retain the simple master and two-child-controller structure. Organise the Python trading code and SQLite data clearly within the project. Architecture and detailed design will determine the exact folders and whether independent accounts share or separate storage.

Provide a private `.env` for account connection information, credentials, home currency and one candle lookback per controller, maintaining the one-to-one controller/account mapping. Keep credentials out of committed files, notebooks and displayed logs. Strategy selection and ordinary configuration remain explicit and understandable.

## Acceptance criteria

1. The scheduled run uses the agreed candle, indicators, ATR, sizing and trade-management rules, including New York daylight-saving changes.
2. Existing trades are managed before new entries. Entries produce the intended two-trade set in the direction of the fresh entry-stage C1 event. An occupied pair or a pair with unresolved orders cannot receive another set.
3. The notebook agrees with OANDA on trade identities, actual fills, status, stop changes, exit reasons, pip results and monetary results, including applicable charges.
4. Order failures and unfinished runs are visible. Uncertain orders, incomplete entries and failed protection changes are handled by the operator, with new entries blocked for affected pairs while issues remain open.
5. The observational dashboard accurately presents controller outcomes and notebook/account information with refresh times and visible failures.
6. Qualify each notebook and strategy with controlled checks covering lab calculation equivalence, long and short entries, opposite C1 and Exit events, reversals, simultaneous signals, stops, targets, break-even adjustments, position sizing and failure reporting. An observed OANDA practice-account run confirms the integration.

Acceptance establishes correct operation. Profitability is an outcome of the practice experiment rather than a software acceptance requirement.

## Delivery sequence

Maintain project guidance in an `AGENTS.md` of at most 300 lines and the necessary supporting documents. The remaining delivery sequence is architecture and OANDA integration, detailed design, implementation planning, and implementation. Review each stage before progressing to the next.

Further decisions about operational deployment and account provisioning belong in those stages. The strategy combination is selected manually before the practice experiment starts.

The [project overview](README.md) links to the supporting documents. [Project status](docs/STATUS.md) records delivery progress separately from these accepted requirements.

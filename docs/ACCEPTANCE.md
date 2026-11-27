# Acceptance checklist

Status: Required scenarios derived from final brief version 1. Verification has
not been executed. This checklist expands the brief's acceptance criteria without
choosing an implementation or claiming application acceptance.

The [project brief](../PROJECT_BRIEF.md#acceptance-criteria) owns acceptance scope.
Detailed design must make each expected result testable, including how the
notebook records partially successful broker actions.

## Trading and operating scenarios

| ID | Scenario | Expected result |
| --- | --- | --- |
| A01 | Weekday run in standard time and daylight-saving time | The scheduler starts the run at 4:50 pm New York local time. Each stage uses the partial candle due to close at 5:00 pm that day and records the capture time. A fetch after rollover leaves the intended input unavailable. The master records elapsed duration. |
| A02 | Fresh event and continuing state | Step 4.3 calculates C1 and ATR from the candles fetched in 4.2. Holding those candles and the strategy fixed gives the same 4.3 result regardless of Stage 1 decisions. Only a fresh eligible C1 event on the current partial candle creates an entry. The notebook records the signal result and decision. |
| A03 | OANDA lookback, calculation equivalence and invalid ATR | Both stages use the candle count bound to the qualified strategy, including the partial candle, and record the effective count once per master run. Qualification verifies that the window supplies C1 and Exit warm-up, prior signal observations and ATR history. Compare the selected lab calculations on identical inputs. For an anchored strategy, verify the immutable research origin, independence from pre-origin candles, accumulating history and unavailable input when the origin is missing; record the origin and actual indicator count. Invalid entry ATR prevents entry while a valid signal exit can proceed. Later ATR changes leave existing trade levels unchanged. |
| A04 | Balance refresh with no, confirmed or unconfirmed closures | After Stage 1 finishes, the master requests the actual realised OANDA sizing balance once, including on the first run. A successful balance request starts Stage 2 even if an earlier close remains unconfirmed. All entries use this fixed balance, with current margin checked again for each set. A later reporting snapshot preserves the original sizing balance. |
| A05 | Home and cross-currency sizing | Each leg's planned initial stop risk is at most 1% of the sizing balance after allowed unit rounding. Convert quote-currency loss to the home currency in the private account configuration and express orders in the pair's base units. Missing conversion or sizing inputs prevent entry. |
| A06 | Notebook eligibility and sequential processing of 28 pairs | Stage 2 checks every permitted pair in the notebook in order. An open leg or unresolved issue skips the pair before any pair-specific OANDA request. Eligible pairs get a fresh candle window. Each pair's outcome or skip is recorded before advancing. Successful long and short entries have two individually identified trades with the required protection. |
| A07 | Surviving pairs with opposite C1 or Exit events | Stage 1 fetches candles, evaluates signals, submits required closes and records the outcome for one surviving pair before checking the next. An opposite C1 or Exit event closes the surviving trades for that pair. A persistent indicator state produces no fresh event. |
| A08 | Fresh C1 entry after a C1-triggered closure | A fresh opposite C1 event triggers closure in Stage 1. Once the pair is flat and clear of unresolved orders, step 4.4 can enter in either direction supplied by 4.3, including the direction of the former trade. A surviving trade or unresolved close prevents entry on that pair. |
| A09 | Entry after an Exit or broker price closure | A flat pair can enter on a fresh C1 event from 4.3 after an Exit or price closure, regardless of the previous trade direction. A closure with no fresh entry-stage C1 event produces no entry. |
| A10 | Registered Trade 1 missing after a take-profit | Start from the notebook's registered set. If OANDA confirms Trade 1 closed by take-profit and Trade 2 survives, the scheduled run moves Trade 2's stop to its actual entry price and records confirmation. If the current stop is already at entry, the run records the adjustment as complete without another stop request. A closed Trade 2 is not modified. Actual fills and monetary outcomes are preserved. |
| A11 | Both registered legs missing or other broker closure | Look up closing transactions for both missing trade IDs and check for stop-loss executions. Record the actual cause, time and fill for each leg, including mixed closure reasons. A missing leg without a confirmed closure is recorded as unresolved. |
| A12 | Rejected entry, one-leg fill, uncertain response, failed stop change or interruption | A failure or unfinished attempt is visible. If the controller stops after committing a confirmed Trade 1 fill and before sending Trade 2, the notebook identifies the fill and the incomplete set. A set is complete only when both legs and required protection are confirmed. Unresolved orders, incomplete entries and failed protection changes block new entries on that pair until the operator's disposition is recorded. Other pairs can continue while account-wide reads and notebook writes remain usable. |
| A13 | Unavailable market or missed launch while the timer is inactive | Record the reason for an unavailable entry. The next regular scheduled launch uses its own partial candle. No entry is queued and no missed launch is replayed. |

## Notebook and dashboard scenarios

| ID | Scenario | Expected result |
| --- | --- | --- |
| A14 | Closed and open trades, including a JPY pair | Pip size is applied correctly in both directions. Open trades have no realised exit outcome. Positive and negative results display correctly. Monetary results are in the account home currency, with financing and other charges distinguishable and reconciled with the broker. |
| A15 | Master/child results, refresh and failures | The dashboard shows each stage's recorded progress and the latest reconciled account snapshot with its broker refresh time. UTC records display in New York time with the UTC offset. A failed final refresh leaves the previous successful snapshot visible with a failure indicator. The dashboard provides observation only. |
| A16 | Independent account/notebook configurations and strategy changes | Each account has one controller authorised to open trades. Records and actions stay associated with the configured account, controller and notebook. A strategy or Exit rule change uses a new controller and a distinct account and notebook. The original controller manages its existing trades under its original rules. |

## Verification evidence

Use controlled offline cases for calculations, state transitions, scheduling and
failure paths. Qualify each notebook and strategy version before activation.
Compare inherited numerical behaviour against the selected lab implementation
on identical inputs, including ties, missing operands, prior observations and
warm-up. Check that the requested bar count supports the selected calculations
and rules. Ordinary scheduled runs use the qualified strategy.

Complete an observed OANDA practice-account run for the actual integration.
Distinguish this evidence from offline simulation. Record the strategy identity,
configuration/code version, run identity, relevant broker records, notebook
reconciliation and any failures. Keep credentials out of evidence.

Record each scenario's outcome and supporting evidence when executed, and link
the results from [project status](STATUS.md). Mark acceptance complete when the
required scenarios have been exercised and their results recorded.

Trading profitability is measured by the experiment; it is not a software
acceptance requirement.

# Implementation plan

Approved by the owner on 16 November 2026 after three review fixes. The
[brief](../PROJECT_BRIEF.md) owns behaviour, [design](DETAILED_DESIGN.md) owns
contracts and [acceptance](ACCEPTANCE.md) owns scenarios and test variations.
[Status](STATUS.md) owns current operation; this plan retains delivery history and
guidance for bounded feature/fix requests.

## Delivery history

Architecture → detailed design → planning reviews are complete. M01–M09 retain
these dependencies and offline receipts, not a review queue. The
[README map](../README.md#code-and-test-map) locates components/tests;
[verification](VERIFICATION.md) indexes host/account observations. Existing approvals
do not establish account support.

| Delivery / date — original dependency | Recorded result and source |
| --- | --- |
| M01, 16 Nov — Approved plan | 16 offline checks; original digest/results in Git; [fixtures](../tests/support.py). |
| M02, 17 Nov — M01 | 37 combined checks; [suite](../tests/test_m02.py). |
| M03 plumbing, 17 Nov — M01–M02; manual selection | 48 checks + 8 original-lab probes; source `cd64da9`; [reference probes](../tests/check_m03_lab_reference.py). |
| M04 preflight — M02/account; M03 for candles | [Intended-account and scheduled-candle evidence](VERIFICATION.md#python-01-account-and-host-evidence). |
| M05, 18 Nov — M01–M03 | 102 suite/40 management checks; [evidence/traces](../var/verification/m05/evidence.json), [log](../var/verification/m05/discovery.log). |
| M06, 18 Nov — M01–M03; account findings | 171 suite/69 entry checks; [evidence](../var/verification/m06/evidence.json), [log](../var/verification/m06/discovery.log). |
| M07, 18 Nov — M01–M06 | 264 suite checks; [evidence/row exports](../var/verification/m07/evidence.json), [package](../var/verification/m07/package-check.json). |
| M08, 19 Nov — M01–M02 records; M07 outcomes | 294 suite/30 dashboard checks; [manifest/pages](../var/m08/verification.json), [visual review](../var/m08/visual-checks.json). |
| M09, 19 Nov — M07; M08 for dashboard | 319 offline tests; [manifest](../var/verification/m09/verification.json). User-manager controller passed; dashboard failed 218/CAPABILITIES: [report](../var/verification/m09/nnfx-m09-probe-2194936/host-results.json). Later system checks preserved security restrictions. |
| M10 integration, 19–20 Nov | Prerequisite/service/initialization/arming fixtures: 327/347/383/392/406 checks; [integration record](../var/verification/m10-integration/verification-final.json), [arming suite](../var/verification/m10-arming/final-suite.log). Simulated fills cannot qualify execution. |
| Automatic qualification, 20 Nov | 427 baseline/460 isolated tests, 43-file wheel; [frozen verification](../var/prepared/m10-automatic/var/verification/m10-automatic/verification.json). Owner required isolation from concurrent dashboard work. |

Counts apply to recorded revisions. M01–M08 were reported ready for review, without
claiming a fresh full suite or acceptance of every scenario. [Acceptance](ACCEPTANCE.md#controlled-verification)
links controlled cases; implementation/deployment alone does not establish acceptance.

New experiments may proceed offline while account checks are pending. Each needs
its own selection, calculation and [account qualification](ACCEPTANCE.md#account-and-execution-evidence);
Python 01–03 already have strategy/count bindings. Automatic selection, repair
services and signal forcing remain excluded. A one-unit-increment Trade 2 reduction
is only a review option if observed account restrictions require it, never a fallback.

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

Use [acceptance scenarios](ACCEPTANCE.md) to verify changes and investigate issues.
Account incompatibilities, unsupported monetary shapes and unresolved outcomes
return to review. Reuse evidence only while its code, configuration, strategy and
account conditions apply; recheck affected behaviour after changes.

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

Follow [working guidance](../AGENTS.md#authority-and-proportionate-work) for routine
work. A requested milestone handover names work, prerequisites, checks and stopping
point, carrying unfinished work and authority forward to its agreed review.
Stop for that review before starting another explicitly requested milestone.

Keep one current status handoff. Retained evidence records scenario/variation,
class, date, code/configuration/strategy identities, input location, run/set IDs,
expected/actual result and pass/fail/blocked reason. Preserve non-secret broker IDs
and failures. [Acceptance](ACCEPTANCE.md#account-and-execution-evidence) determines
when a scenario is verified; unknown remains pending.

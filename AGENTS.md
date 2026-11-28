# Working guidance

## Development worktrees

Create all new development worktrees under
`/mnt/nnfx-usb/development/worktrees/<repository>/<task>`.
Keep each worktree's development databases, artifacts and working data separate
on the USB drive.

Before creating a worktree or its development data, verify that `/mnt/nnfx-usb`
is mounted. Stop if the drive is unavailable; do not fall back to internal storage.
Reuse a suitable existing checkout and preserve existing work and data.

## Purpose and boundaries

Build the practice trading application in [PROJECT_BRIEF.md](PROJECT_BRIEF.md).
Prefer the smallest solution meeting an accepted requirement: simple architecture,
reusable independent account/controller/notebook bindings, correct trading and
understandable records. Do not add automatic strategy selection or reproduce the
indicator lab's research framework. Simplicity must not hide uncertainty,
duplicate trades or missing protection.

Practice accounts are the scope. The dashboard is observational: it cannot place
orders, modify strategies or start trading runs. Keep credentials in private
configuration, outside version control, logs and notebooks; examples contain no
real credentials. Match broker checks to the intended account.

## Read for the task

Start with the short [status](docs/STATUS.md), then only the relevant route below.
The [README component map](README.md#code-and-test-map) links requirements, code
and tests; its [development guidance](README.md#development-and-verification)
provides commands. Follow cross-boundary links only as needed.

| Task | Read |
| --- | --- |
| Trading behaviour or scope | [Brief](PROJECT_BRIEF.md#trading-sequence), then the affected [design contract](docs/DETAILED_DESIGN.md) |
| Persistence or reconciliation | [Design state and import rules](docs/DETAILED_DESIGN.md#state-rules) |
| Dashboard | [Presentation contract](docs/ARCHITECTURE.md#notebook-dashboard) |
| Deployment, scheduling or maintenance | [Operations](docs/OPERATIONS.md) |
| Strategy integration | [Calculation contract](docs/ARCHITECTURE.md#candle-and-signal-inputs), selected manifest and experiment setup |
| Acceptance or retained evidence | Relevant [acceptance scenario](docs/ACCEPTANCE.md); [verification references](docs/VERIFICATION.md) only when needed |
| Delivery dependencies or feature planning | [Implementation plan](docs/IMPLEMENTATION_PLAN.md) |

## Document ownership

| Document | Authoritative purpose |
| --- | --- |
| `PROJECT_BRIEF.md` | Accepted scope, trading and operating rules |
| `AGENTS.md` | Durable working instructions and reading routes |
| `README.md` | Orientation, component/test map and development commands |
| `docs/STATUS.md` | Current delivery state, blockers and one current handoff |
| `docs/ARCHITECTURE.md` | Runtime/workflow, candle/signal contracts and dashboard presentation |
| `docs/DETAILED_DESIGN.md` | Persistence, sizing, broker, reconciliation and accounting contracts |
| `docs/IMPLEMENTATION_PLAN.md` | Delivery dependencies/offline receipts, lifecycle, operating checklist and feature template |
| `docs/ACCEPTANCE.md` | A01–A16 scenarios, controlled variations and required evidence |
| `docs/OPERATIONS.md` | Host procedures, deployment authority and practice upgrades |
| `docs/VERIFICATION.md` | Evidence index, dated host/account findings and their limits |
| `docs/PYTHON_02.md`, `docs/PYTHON_03.md` | Experiment selection, comparison evidence, immutable bindings and integration constraints |

When behaviour changes, update its authoritative document and replace the
superseded statement. Link to that home instead of repeating its rules.

## Authority and proportionate work

Follow the accepted [delivery decision](PROJECT_BRIEF.md#delivery-sequence) and
[operating checklist](docs/IMPLEMENTATION_PLAN.md#operating-checklist).
Use existing approvals and authority without requesting them again. Routine work
uses bounded feature/fix requests; milestone-per-chat reviews apply only to new
milestones explicitly requested by the owner.
User instructions take precedence over project guidance.
For routine fixes use brief planning and focused checks; deepen review when
trading behaviour, persistence, broker interactions or component contracts change.
Clarify material unresolved behaviour before implementing it. Code alone does
not change an accepted requirement or establish deployment or acceptance.

Use the selected lab implementations and exact signal/ATR semantics. Inspect
original rules and code when integration needs them; do not substitute a library
ATR or treat persistent state as a fresh signal. The brief owns its differences
from the lab: partial candle, balance, entry direction, margin and risk rules. The sibling
`nnfx-indicator-lab` is a reference; changing it requires separate task scope.
Runtime reuse is through the packaged strategy, never its checkout or database.

Use actual OANDA fills, status and transactions for notebook facts. Requested
closes or stop changes are not confirmation. Retain broker IDs, signal operands,
sizing and failed/uncertain outcomes for reconciliation and operator investigation.
Offline simulations cannot establish broker support. Preserve required
account-specific checks and distinguish offline, host, read-only account and
actual execution evidence.

## Documentation maintenance

Project-specific budgets (physical lines / UTF-8 bytes, including blank lines):
AGENTS 300 / 16 KiB, README 200 / 16 KiB, STATUS 150 / 16 KiB, other maintained
prose 250 / 16 KiB each; 1 KiB = 1,024 bytes. Prefer shorter guidance. Remove
superseded duplication before considering a new document; report essential
exceptions explicitly. Raw evidence, third-party and legal files are separate.

Keep the README map to 10 rows/400 words and its command guide to 8 entries/400
words of explanation. Update affected mappings when ownership or paths change.
Keep one STATUS handoff and the plan's feature template to 15 lines/200 words each.
Record only findings that affect future work; replace state instead of appending
progress narratives. Check links, anchors, sizes, consistency and approval status
for prose changes. Do not run application tests solely for prose. Runtime changes
need meaningful focused verification, with evidence and limits linked from status.

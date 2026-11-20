# Working guidance

## Purpose

Build the NNFX practice trading application defined in [PROJECT_BRIEF.md](PROJECT_BRIEF.md).
Keep this file at or below 300 lines. Put detailed requirements in their owning
documents and link to them here.

## Principles

1. Extreme simplicity across architecture, code, configuration and operation.
2. Reusable account/controller/notebook configuration for independent experiments.
3. Correct trading behaviour, broker reconciliation and understandable records.

Prefer the smallest solution that meets an accepted requirement. Do not reproduce
the indicator lab's whole research framework, add speculative infrastructure or
introduce automatic strategy selection. Simplicity must not conceal uncertain
order outcomes, duplicate trades or missing protection.

## Read for the task

Start with [project status](docs/STATUS.md) and the relevant document below.
Read only the material needed for the task; follow references across boundaries.

| Task | Read |
| --- | --- |
| Understand scope or change trading behaviour | [Project brief](PROJECT_BRIEF.md) |
| Understand project contents and delivery sequence | [README](README.md) |
| Work through architecture or OANDA integration | [Architecture](docs/ARCHITECTURE.md) |
| Review component, record and reconciliation contracts | [Detailed design](docs/DETAILED_DESIGN.md) |
| Define or verify acceptance | [Acceptance checklist](docs/ACCEPTANCE.md) |
| Determine current delivery state and next work | [Status](docs/STATUS.md) |
| Plan implementation milestones and dependencies | [Implementation plan](docs/IMPLEMENTATION_PLAN.md) |

## Document ownership

- `PROJECT_BRIEF.md` owns accepted scope, trading rules and operating rules.
- `AGENTS.md` owns working guidance and task-based reading.
- `README.md` owns orientation and navigation; add real setup/run commands when available.
- `docs/STATUS.md` owns current delivery state, verification evidence and next work.
- `docs/ARCHITECTURE.md` owns architecture work and its unresolved decisions.
- `docs/DETAILED_DESIGN.md` owns detailed component and data contracts and their review status.
- `docs/ACCEPTANCE.md` owns verification scenarios derived from the brief.
- `docs/IMPLEMENTATION_PLAN.md` owns delivery milestones, dependencies, verification order and plan review status.

Keep one authoritative home per rule. Supporting summaries must agree with the
brief. Distinguish accepted requirements, proposals and observed verification.
Create detailed-design and implementation-plan documents when those stages begin;
do not fill them with speculative decisions in advance.

## Working sequence and authority

Follow the accepted delivery sequence: architecture and integration, detailed
design, implementation planning, then implementation. Use the user's existing
instructions and decisions; do not seek permission again for work already
authorised. Continue useful work within the current stage and agreed scope.

User instructions take precedence over project guidance. Update the owning
document when the user changes an accepted rule. Do not silently change strategy
behaviour while resolving an implementation detail. Clarify a material unresolved
behaviour before implementing it, and record the decision once.

## Preserve the agreed trading behaviour

The brief uses the still-forming daily candle at the 4:50 pm New York run.
The scheduler owns timing and each run uses its own candle.
Keep the agreed balance snapshot and use the fresh entry-stage C1 event to
select direction on eligible flat pairs. Check current margin for each new
trade set. The brief sets no combined account risk cap.

Use the selected indicator lab implementations and exact accepted signal/ATR
semantics. Inspect the original rules and code when integration requires them;
do not substitute a library's default ATR or reinterpret a persistent state as a
fresh signal. The practice brief governs its explicit differences from the lab.

Research simulation assumptions are not broker execution evidence. Use actual
OANDA status, fills and transactions for the notebook. A requested close or stop
change is not a confirmed one. Keep broker identifiers, signal results and
sizing decisions for reconciliation and operator investigation of failures.

The dashboard is observational. It must not place orders, modify strategies or
start trading runs. Practice accounts are the scope of this project.

## Changes and verification

Preserve existing work and data. Treat the sibling `nnfx-indicator-lab` project as
a reference; changes to that application require their own task scope. Choose a
simple documented reuse boundary instead of assuming a runtime dependency on its
checkout or operating database.

Keep credentials in private configuration, outside version control, logs and
notebooks. Never include real credentials in examples. Match broker checks to the
intended practice account and do not assume account capabilities from documentation
alone.

Use focused checks appropriate to a change. Verify trading logic with controlled
cases and compare inherited calculations against the selected lab implementation.
Distinguish offline checks from actual OANDA practice execution; never describe a
simulated result as broker verification.

For documentation changes, check links, consistency, approval status and this
file's line limit. Do not add tests that merely mirror prose. When runtime work
exists, record meaningful verification and outstanding limitations in `docs/STATUS.md`.

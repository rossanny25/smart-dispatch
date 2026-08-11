# Smart Dispatch IA v2.1 — Technical Addendum

This addendum preserves technical direction and brownfield evidence that should inform architecture and implementation without turning the PRD into a solution design.

## Brownfield Baseline

- Current runtime: one Python `http.server` process on port 8000.
- Current frontend: static HTML/CSS/vanilla JavaScript.
- Current operational data: module-level Python arrays.
- Current persistent memory: `data/learning_store.json`.
- Current orchestration: one synchronous handler that performs the conceptual agent stages.
- Current score: ad hoc base, proximity, workload, memory bonus, and GPS penalty.
- Current feasibility: certification before scoring; maximum-day validation after scoring; availability and shift are not enforced.
- Current runtime defect: the priority-5 overtime branch uses JavaScript-style `alerts.push(...)`; Python compilation succeeds, but that branch raises `AttributeError`.

Detailed evidence is indexed in `docs/index.md`.

## Technical Direction from Professor Feedback

### Deterministic Control

Use an explicit transition table for:

`CAPTURE -> ANALYZE -> PLAN -> EVALUATE -> WAIT_FOR_DECISION -> LEARN`

Recommended additional terminal/error states include `COMPLETED`, `FAILED`, and `NO_FEASIBLE_CANDIDATES`. Architecture should decide whether these are states or typed outcomes while preserving the PRD behavior.

### JSON Contracts

Each Agent Stage should have a versioned input/output schema. Schema validation occurs before a State Transition. Prompts may propose structured values, but the orchestrator and deterministic services remain authoritative.

### SQLite

SQLite should separate operational records, run audit data, Episodic Memory, and Semantic Patterns. Migration should import JSON seed records as seeded assumptions rather than fabricate historical evidence.

### Learning Policy

The policy requires:

- evidence count increments for new observations;
- confidence growth for consistent observations;
- confidence reduction for contradictions;
- age decay;
- promotion only after a minimum sample threshold;
- no effect on Hard Constraints.

Exact formulas and defaults remain configuration decisions listed in the PRD Open Questions.

### Academic Evidence

The deliverable should include:

- automated hard-rule tests;
- uncertainty scenarios;
- Memory enabled/disabled comparisons;
- KPI definitions and computed results;
- decision, limitation, and risk documentation;
- a reproducible configuration snapshot for each result.

## Reconciliation Notes

- Existing specifications describe Express/React, but the implemented brownfield system is Python/vanilla JavaScript. The PRD does not mandate a framework.
- Existing rules allowed a priority-5 overtime exception. The professor feedback defines maximum-day eligibility as a hard exclusion. The MVP follows the stricter feedback; an exception workflow is deferred.
- Existing UI/spec language exposes “thought traces.” The updated requirement preserves structured decision evidence without requiring private chain-of-thought.
- Existing roadmap proposes PostgreSQL/pgvector later. The MVP explicitly uses SQLite and statistical incremental learning.

# Current Architecture

## Executive Summary

Smart Dispatch IA is implemented as a multi-part monolith. A single Python process serves static browser assets and synchronous JSON endpoints. Domain data is held in module-level Python collections, while learned preferences and calibrations are stored in one JSON file.

## Runtime Flow

1. The browser loads technicians, orders, and memory through GET endpoints.
2. The dispatcher creates or selects an order.
3. `POST /api/dispatch/simulate` performs capture, analysis, planning, evaluation, and response assembly in one handler call.
4. The UI animates those already-computed stages.
5. `POST /api/dispatch/confirm` updates order/workload state and writes learning records.

## Components

### Backend

- `SmartDispatchHTTPHandler`: static file serving, API routing, response serialization.
- Module-level technician/order lists: volatile operational store.
- `ZONE_DISTANCES`: deterministic distance lookup.
- `learning_store.json`: persistent learned calibration/preferences.
- Inline dispatch logic: classification, ranking, validation, and response construction.

### Frontend

- Dashboard state in module-level JavaScript variables.
- Fetch-based API adapter embedded in `main.js`.
- DOM-rendered order, technician, memory, agent-cycle, recommendation, override, and completion views.
- Artificial delays animate the cycle after the backend returns.

## Current Constraints and Gaps

- There is no explicit state enum, transition table, run identifier, or durable execution log.
- Agent outputs are not independently schema-validated.
- Feasibility rules are incomplete and split across planning and evaluation.
- Ranking uses an unnormalized formula and caps totals, making explanations misleading.
- Confidence is reused only as a memory-record attribute, not computed for recommendations.
- JSON persistence has no atomic transaction across dispatch, decision, result, and learning.
- The code has no separation between HTTP, orchestration, domain rules, repositories, and presentation.

## Target Direction Required by the Feedback

The next architecture should preserve the educational scope while introducing these boundaries:

- HTTP/API adapter
- deterministic orchestrator with persisted states
- capture/analyze adapters returning validated JSON
- feasibility engine applying immutable hard rules
- scoring engine with configurable weights and normalized components
- evaluation/explanation service
- SQLite repositories for runs, episodes, decisions, outcomes, semantic patterns, and KPI events
- learning service that aggregates evidence and promotes patterns only after thresholds

The target sequence is:

`CAPTURE -> ANALYZE -> PLAN -> EVALUATE -> WAIT_FOR_DECISION -> LEARN`

Every transition must record timestamps, input/output summaries, status, and errors. `NO_FEASIBLE_CANDIDATES` and invalid-agent-output are explicit terminal/error paths.

## Security and Operational Posture

Current CORS allows any origin, no endpoint is authenticated, payload size is unbounded, and exceptions are inconsistently handled. These are acceptable only for a local classroom prototype and must be stated as limitations.

## Testing Strategy Needed

- Unit tests for each hard constraint and score component.
- State-transition tests, including invalid transitions and retry/error paths.
- Contract tests for every endpoint and agent JSON payload.
- SQLite migration and learning-promotion tests.
- Scenario tests for stale GPS, weather, traffic, no feasible candidates, close scores, and contradictory feedback.
- KPI calculation tests and memory-on/off comparisons.


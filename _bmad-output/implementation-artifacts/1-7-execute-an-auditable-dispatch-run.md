---
baseline_commit: NO_VCS
---

# Story 1.7: Execute an Auditable Dispatch Run

Status: in-progress

## Story

As a dispatcher,
I want the complete recommendation process controlled and recorded as one Dispatch Run,
so that I can trust its state and inspect the evidence behind its result.

## Requirements Traceability

- **Functional:** FR1, FR2, FR3, FR20.
- **Non-functional:** NFR1, NFR2, NFR3, NFR7.
- **Journey:** UJ-1 through recommendation/no-feasible outcome; decision/outcome remain Epic 2.
- **Architecture:** AD-1–AD-5, AD-7, AD-8, AD-10–AD-13, AD-15, AD-16, AD-18–AD-20, AD-24, AD-26, AD-27.
- **Success:** SM-3 plus retained evidence for SM-1, SM-2, SM-4, SM-6, SM-9.
- **Dependencies:** authoritative integration of completed Stories 1.1–1.6. Story 1.8 owns crash resume, competing writers, completed-run replay, redacted snapshot queries, and performance benchmark. Story 1.9 owns browser presentation.

## Acceptance Criteria

1. **Strict start request and one immutable run snapshot**
   - `POST /api/v1/dispatch-runs` requires `Idempotency-Key` and a strict `DispatchRunStartV1` body containing an existing Work Order UUID, one UTC `captured_at`, complete Technician roster, quality/GPS evidence keyed exactly to that roster, traffic/weather freshness, active supporting-episode count, and `memory_experiment_mode`.
   - The v1 mode accepted here is `disabled`; Story 3.2 introduces active Semantic Pattern reads.
   - Before any stage executes, the command loads and validates the canonical Work Order, copies it with roster/environment/freshness/configuration into one canonical `run_snapshots` input row, and records its SHA-256.
   - Every later calculation is reconstructed from this immutable snapshot; no stage queries mutable Work Order, Technician, environment, or clock state.

2. **Only `DispatchOrchestrator` advances state**
   - The `dispatch-v1` transition registry permits exactly `START → CAPTURE → ANALYZE → PLAN → EVALUATE`, followed by `WAIT_FOR_DECISION`, `NO_FEASIBLE_CANDIDATES`, or typed `FAILED` from an active stage.
   - Stages/policies/adapters return evidence only and cannot persist a run state or transition.
   - Every transition has a consecutive sequence, previous/current state, outcome code, UTC occurrence time, run revision, and configuration version.

3. **CAPTURE is validated and committed**
   - Run creation and the immutable input snapshot are one atomic transaction with initial `CAPTURE` state and revision 0.
   - CAPTURE validates the copied Work Order/roster/environment contract, writes canonical input/output snapshot references and a completed StageExecution, then atomically records `CAPTURE → ANALYZE` and increments revision once.
   - Invalid request data is rejected before run creation; invalid retained Work Order data produces a sanitized failure without copying unsafe evidence.

4. **ANALYZE uses the deterministic stage contract**
   - ANALYZE builds `AnalyzeInputV1` only from the run snapshot and invokes `DeterministicAnalyzeStage` through the existing stage boundary.
   - Returned data is validated as `AnalyzeOutputV1` with unknown fields forbidden before persistence.
   - A valid output and StageExecution commit atomically with `ANALYZE → PLAN`; no stage output can choose the next state.

5. **PLAN applies feasibility before scoring**
   - PLAN reconstructs `EligibilityInputV1` from snapshot plus analyzed requirements, invokes `EligibilityPolicy`, and validates the complete output.
   - Only eligible candidates are converted to `ScoringInputV1`; `ScoringPolicy` preserves the exact Story 1.5 formulas/order, while ineligible candidates retain all Story 1.4 discard evidence and no score.
   - PLAN persists one structured output containing validated eligibility and scoring evidence, then atomically records `PLAN → EVALUATE`.
   - No pre-run diagnostic evaluation row is treated as authority; pure policies and contracts are reused from the run snapshot.

6. **EVALUATE adds confidence without changing PLAN**
   - EVALUATE derives `ConfidenceInputV1` from the immutable snapshot and exact PLAN scoring output, invokes `ConfidencePolicy`, and fully validates `ConfidenceOutputV1`.
   - Candidate identity, eligibility, scores, components, penalties, warnings, and rank remain byte-equivalent to PLAN.
   - With eligible candidates, the rank-1 Technician becomes the recommendation and the run atomically enters `WAIT_FOR_DECISION`.
   - With no eligible candidates, confidence/recommendation are absent and the run atomically enters `NO_FEASIBLE_CANDIDATES`.

7. **StageExecution evidence is complete**
   - Every CAPTURE, ANALYZE, PLAN, and EVALUATE attempt records UUID, state, attempt number, status, schema/configuration version, start/end UTC timestamps, exact integer duration milliseconds, input/output snapshot references, and typed error fields.
   - Successful records have output references and no error; failed records have no partial output reference and include stable error code/type/safe message.
   - Stage records and transitions are returned in chronological sequence with deterministic tie ordering.

8. **Typed failures preserve prior committed evidence**
   - Invalid stage output, policy failure, or persistence failure during an active stage never commits partial stage output or the success transition.
   - When failure recording succeeds, a separate atomic command records a failed StageExecution and the permitted `<active-state> → FAILED` transition while preserving all prior stage evidence.
   - If failure recording itself cannot commit, the original stage remains the durable state and a sanitized application error is returned; no false FAILED state is claimed.
   - API errors never expose exception text, addresses, incident narratives, exact GPS, or stack traces.

9. **No-feasible result is exact**
   - `NO_FEASIBLE_CANDIDATES` returns every Technician with all Hard Constraint checks/rejection reasons.
   - It contains no recommended Technician, eligible alternative, Objective Score for an ineligible Technician, Recommendation Confidence, or fabricated fallback choice.
   - This is a successful terminal recommendation outcome, not a generic server error.

10. **Canonical run resource and presentation**
    - `DispatchRunSuccessEnvelopeV1` returns run ID/state/revision/configuration/memory mode, input snapshot reference/hash, recommendation when present, eligible alternatives, separate ineligible results, score breakdown, confidence/factors/warnings/explanation, ordered stage executions, and transitions.
    - Stored evidence retains canonical unrounded Decimal strings; any display-specific Decimal included by the HTTP response uses two-place `ROUND_HALF_UP` without altering stored evidence.
    - The response contains structured evidence only and no private chain-of-thought/provider reasoning.

11. **Local API behavior is versioned and idempotent**
    - Route is local `/api/v1/dispatch-runs`, uses the shared success/error envelopes, executes blocking orchestration in the thread pool, and is wired only in `app/main.py`.
    - A completed identical route/key/request retry returns the retained canonical response and creates no duplicate run/snapshot/stage/transition.
    - Same route/key with a different request hash returns `409 CONFLICT`.
    - Required transport failures remain `413`, `415`, and `422`; stable orchestration errors map to typed safe responses.

12. **Immutable `dispatch-v1` configuration**
    - One deeply immutable registry and persisted SHA-256 covers state/transition table, stage order/semantics, schema versions, configuration bundle, evidence/status/error rules, ordering, bounds, serialization, duration calculation, terminal consistency, and presentation rounding.
    - The run snapshot records exact `dispatch-v1`, `analysis-v1`, `eligibility-v1`, `scoring-v1`, and `confidence-v1` versions/digests.
    - Environment variables cannot change transitions, policies, or formulas.

13. **Minimal authoritative persistence**
    - Migration `20260728_0007` adds `dispatch_runs`, `run_snapshots`, `stage_executions`, and `state_transitions` with explicit UUID/FK/check/unique constraints.
    - Repositories validate canonical JSON/hash, snapshot ownership, configuration digest, state/revision/terminal summaries, stage timing/status/reference consistency, transition legality/sequence, and complete response reconstruction on every read.
    - Repositories use caller-owned transactions and never commit.

14. **Scope boundary with Story 1.8**
    - This story implements synchronous start-to-recommendation and revision increments required for correct authority.
    - Story 1.8 adds public resume/replay operations, competing-writer conflict tests, crash-boundary recovery, snapshot redaction query, and the 100-run p95 benchmark.
    - No decision, outcome, learning, browser rewrite, fixture reset, KPI, report, active Memory read, or legacy route cutover is added here.

15. **Boundary-aligned verification**
    - Unit tests cover the full transition table, invalid transitions, snapshot-only stage inputs, no/one/many candidates, failure translation, exact duration, stage order, and immutability.
    - Contract tests reject unknown fields, roster/source mismatches, altered PLAN evidence during EVALUATE, illegal terminal summaries, ineligible score leakage, confidence in no-feasible output, malformed timing/error evidence, and unsafe explanation/provider fields.
    - Real-SQLite tests cover fresh and `0006 → 0007` migration, exact schema/FKs/checks/uniqueness, four stage commits, final reconstruction, idempotent completed retry/conflict, no-feasible outcome, each stage failure, rollback, corruption, and preservation of Stories 1.1–1.6 evidence.
    - API/OpenAPI tests cover `201`, `409`, `413`, `415`, `422`, safe typed failures, success/no-feasible response validation, and no external network use.
    - Full regression, compile, offline lock, process launch, import safety, and learning-store integrity remain green.

## Tasks / Subtasks

- [ ] 1. Add failing run-domain, contract, orchestrator, persistence, API, and migration tests first (AC: 1–15).
- [ ] 2. Define frozen Dispatch Run/state/snapshot/stage/transition domain models and immutable `dispatch-v1` registry (AC: 1–2, 7, 9, 12).
- [ ] 3. Add strict start/snapshot/stage/PLAN/EVALUATE/run-resource contracts and presentation helpers (AC: 1, 3–10).
- [ ] 4. Add migration `0007`, repositories, ports, and Unit of Work integration (AC: 2, 7–8, 11–13).
- [ ] 5. Implement snapshot-only CAPTURE/ANALYZE/PLAN/EVALUATE execution and `DispatchOrchestrator` transactions (AC: 1–9, 12–14).
- [ ] 6. Add `/api/v1/dispatch-runs`, composition wiring, envelopes, logging, and idempotent completed-response behavior (AC: 10–11).
- [ ] 7. Complete documentation, focused/full verification, adversarial review fixes, and tracking evidence (AC: 13–15).

## Dev Notes

### Binding Capability Boundary

- `DispatchOrchestrator` is the only state owner. Stage helpers are pure/application services that accept validated snapshot data and return contracts.
- This is the first authoritative run path. Existing Story 1.3–1.6 application commands remain useful diagnostic seams but are not chained as run authority because they read/persist pre-run evidence independently.
- Reuse the same deterministic Analyze adapter, Eligibility/Scoring/Confidence policies, strict contracts, registries, canonical JSON/Decimal utilities, warning/explanation structures, and validation logic.
- `POST /dispatch-runs` consumes an existing canonical Work Order. Story 1.9 composes Work Order creation followed by run start in the browser.

### Run Snapshot Contract

Snapshot input contains:

- `schema_version`, `dispatch_configuration_version`, `captured_at`, copied Work Order ID/body/context;
- complete sorted Technician roster with all Story 1.4 fields;
- complete quality and GPS evidence keyed exactly one-to-one to roster;
- traffic/weather observed timestamps, configured defaults, active supporting episode count;
- `memory_experiment_mode: "disabled"`;
- exact configuration-version/digest bundle for analysis, eligibility, scoring, confidence, and dispatch.

Exact GPS coordinates are not accepted or stored. Only freshness timestamp and optional last-known zone enter the snapshot.

### State and Commit Semantics

| Durable state | Stage executed next | Success state |
| --- | --- | --- |
| `CAPTURE` | CAPTURE | `ANALYZE` |
| `ANALYZE` | ANALYZE | `PLAN` |
| `PLAN` | PLAN | `EVALUATE` |
| `EVALUATE` | EVALUATE | `WAIT_FOR_DECISION` or `NO_FEASIBLE_CANDIDATES` |

- Creation transaction records `START → CAPTURE` at revision 0.
- Each successful stage transaction writes input/output snapshots, StageExecution, legal transition, and increments revision exactly once.
- A failure transaction writes only failed execution/error evidence plus `<stage> → FAILED`, incrementing once.
- Use one attempt in this story. Story 1.8 owns retry/resume attempts and competing CAS behavior.

### Expected File Impact

**New:**

- `app/domain/dispatch/{__init__,models,rules}.py`
- `app/contracts/dispatch.py`
- `app/application/orchestration/dispatch_orchestrator.py`
- `app/adapters/persistence/dispatch.py`
- `app/api/v1/dispatch_runs.py`
- `app/migrations/versions/20260728_0007_dispatch_runs.py`
- `tests/unit/test_{dispatch_rules,dispatch_contracts,dispatch_orchestrator}.py`
- `tests/integration/test_dispatch_persistence.py`
- `tests/contract/test_dispatch_runs_api.py`

**Updated:**

- persistence ports/schema/Unit of Work, API router/errors, composition root, migration tests/fixture heads, development guide, sprint/story tracking.

Do not modify frontend, legacy compatibility/server, existing policy formulas/registries, learning store, or Stories 1.1–1.6 evidence tables.

### Testing and Safety Guardrails

- Use deterministic UUID/time sequences in orchestration tests; never read clocks inside domain policies.
- Validate complete nested evidence at each stage boundary, not only summaries/hashes.
- Failed-stage recording must itself be tested under persistence failure; never claim a FAILED transition that did not commit.
- Verify output snapshot hashes and all cross-table ownership references on read.
- Preserve the existing 266-test baseline and learning-store SHA-256 `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.
- No new dependency is required.

### Latest Technical Information

- Keep the pinned FastAPI/Pydantic/SQLAlchemy/Alembic versions from project context; do not upgrade opportunistically.
- SQLAlchemy Core connection transactions remain the Unit of Work mechanism; named foreign keys/checks/unique constraints must be reflected in migration tests.
- Pydantic v2 strict frozen models and model-level validators remain the boundary pattern.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 1.7]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — FR1–FR3, FR20, NFR1–NFR3, NFR7]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-1–AD-12, AD-16, AD-18, AD-20, AD-27]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — §§5–8, 12–14]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad-output/implementation-artifacts/1-6-explain-recommendation-confidence-and-data-quality.md`]
- [Source: `docs/index.md` and linked brownfield documentation]

## Definition of Done

- [ ] All tasks/ACs are implemented with tests passing.
- [ ] Only the orchestrator advances legal transitions from one immutable run snapshot.
- [ ] Stage/transition/snapshot evidence is canonical, complete, chronological, transactional, and corruption-detecting.
- [ ] Recommendation and no-feasible terminal results preserve all Story 1.4–1.6 invariants.
- [ ] Canonical API/OpenAPI/idempotency and typed failure behavior pass.
- [ ] No Story 1.8/1.9/Epic 2+ scope leaked.
- [ ] Full regression and repository integrity checks pass.
- [ ] Code review findings are resolved and exact verification/file records are complete.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Test-first immutable Dispatch Run evidence and state machine.
- Snapshot-only deterministic orchestration across completed policies.
- Transactional persistence, canonical API integration, and adversarial verification.

### Debug Log References

- Pending implementation.

### Completion Notes List

- Pending implementation.

### File List

- `_bmad-output/implementation-artifacts/1-7-execute-an-auditable-dispatch-run.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-07-28: Created implementation-ready Story 1.7 from final planning artifacts, completed Story 1.6, and current codebase.

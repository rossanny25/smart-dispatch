---
baseline_commit: NO_VCS
---

# Story 1.5: Score and Rank Eligible Technicians Deterministically

Status: done

## Story

As a dispatcher,
I want eligible Technicians ranked by a transparent and reproducible objective function,
so that I can compare qualified alternatives using consistent operational criteria.

## Requirements Traceability

- **Functional:** FR10, FR11, FR12.
- **Non-functional:** NFR2, NFR4, NFR7.
- **Journey:** UJ-1, limited to deterministic scoring after feasibility.
- **Architecture:** AD-1, AD-3-AD-7, AD-10, AD-11, AD-13, AD-15, AD-16, AD-18, AD-23, AD-24, AD-26, AD-27.
- **Success/counter-metrics:** SM-2, SM-4, SM-9, SM-C2.
- **Dependencies:** consumes the validated Story 1.4 eligibility evaluation and immutable scoring snapshots. Story 1.6 owns confidence and explanation. Story 1.7 owns authoritative PLAN execution, Dispatch Runs, run snapshots, recommendation, and State Transitions.

## Acceptance Criteria

1. **Only eligible Technicians are scored**
   - **Given** a validated `EligibilityOutputV1`
   - **When** `ScoreEligibleTechnicians` invokes `ScoringPolicy` with `scoring-v1`
   - **Then** every identifier in `eligible_technician_ids` receives exactly one score result
   - **And** no identifier in `ineligible_technician_ids` receives an Objective Score, component, penalty, or rank
   - **And** ineligible candidates are retained only with their complete Story 1.4 constraint evidence
   - **And** scoring cannot reinterpret or override eligibility.

2. **Strict, self-contained scoring input**
   - **Given** scoring input crosses the boundary
   - **When** `ScoringInputV1` validates it
   - **Then** it requires the exact eligibility-evaluation identifier and one immutable scoring snapshot for every eligibility candidate
   - **And** the command derives SLA from the validated Story 1.3 Analyze result and derives ETA, distance, and projected work from retained Story 1.4 evidence
   - **And** caller-supplied scoring data is limited to an optional quality rating bound one-to-one to each Technician UUID
   - **And** the scoring roster exactly matches the eligibility roster with no duplicate, missing, or extra Technician
   - **And** distance exactly matches retained eligibility evidence
   - **And** strict types, canonical ordering, bounded values, and forbidden unknown fields are enforced
   - **And** the pure policy receives no repository, clock, UUID factory, network client, mutable operational row, or Memory adapter.

3. **Every eligible result exposes complete component evidence**
   - **Given** an eligible Technician is scored
   - **When** the result is assembled
   - **Then** it contains exactly `sla`, `proximity`, `workload_balance`, `quality`, and `memory` in registry order
   - **And** every component exposes its safe raw inputs, unrounded normalized Decimal value, configured Decimal weight, and unrounded weighted contribution
   - **And** penalties are exposed separately with name, version, raw inputs, unrounded amount, and impact
   - **And** output contains no Recommendation Confidence, recommendation decision, State Transition, free-form explanation, or provider reasoning.

4. **Normative component formulas**
   - **Given** calculation registry `scoring-v1`
   - **When** component values are normalized
   - **Then** `sla = clamp(100 × (1 − eta_minutes / sla_minutes))`
   - **And** `proximity = clamp(100 − 2 × distance_km)`
   - **And** `workload_balance = clamp(100 × (1 − projected_work_hours / max_workday_hours))`
   - **And** `quality = clamp(20 × rating_0_to_5)` when a usable rating exists
   - **And** `memory = clamp(50 + Σ(confidence × signed_effect_points))`
   - **And** `distance_km = distance_meters / 1000`, `projected_work_hours = projected_work_minutes / 60`, `max_workday_hours = 8`, and `clamp(x) = min(100, max(0, x))`
   - **And** zero or negative `sla_minutes` fails validation before division.

5. **Neutral quality fallback is explicit**
   - **Given** quality rating is absent
   - **When** quality is calculated
   - **Then** its normalized value is Decimal `50`
   - **And** one stable `SCORING_QUALITY_FALLBACK` warning identifies source, quality, freshness, fallback, impact, Technician, and configuration version
   - **And** warning content and ordering come from the immutable registry rather than caller-supplied text.

6. **Memory is neutral and cannot affect eligibility**
   - **Given** no active applicable Semantic Pattern effect exists
   - **When** Memory is calculated
   - **Then** it is Decimal `50`
   - **And** `scoring-v1` accepts no caller or legacy Memory effects, so the sum is empty and deterministic
   - **And** inactive hypotheses and legacy `memory_bonus` never enter canonical scoring
   - **And** Story 3.2 owns a future explicitly versioned integration of active applicable Semantic Pattern effects
   - **And** Memory evidence cannot add a candidate, restore an ineligible candidate, or alter any Hard Constraint.

7. **Distance is a versioned soft penalty**
   - **Given** an eligible Technician has `distance_km > 50`
   - **When** penalties are calculated
   - **Then** `distance_penalty = min(20, max(0, distance_km − 50))`
   - **And** it is zero at and below 50 km, grows without intermediate rounding, and caps at 20
   - **And** every other registered penalty is explicitly named/versioned and Decimal zero by default
   - **And** distance never changes eligibility.

8. **Objective Score uses exact Decimal arithmetic**
   - **Given** all component contributions and penalties
   - **When** the Objective Score is calculated
   - **Then** `raw_score = 0.35×sla + 0.25×proximity + 0.20×workload_balance + 0.10×quality + 0.10×memory − Σ(penalties)`
   - **And** `objective_score = clamp(raw_score)`
   - **And** internal/domain/persistence arithmetic uses `Decimal` without binary floating point or intermediate presentation rounding
   - **And** weights sum exactly to Decimal `1.00`
   - **And** `ROUND_HALF_UP` to two decimal places is reserved for the later API presentation boundary.

9. **Ranking and every tie-break are deterministic**
   - **Given** all eligible candidates have scores
   - **When** ranking is assigned
   - **Then** candidates sort by unrounded Objective Score descending
   - **And** exact ties sort by unrounded SLA descending, then unrounded quality descending, then ETA minutes ascending, then lexicographically ascending canonical Technician UUID
   - **And** ranks are consecutive positive integers in final order
   - **And** input order cannot change output order.

10. **Complete immutable `scoring-v1` registry**
    - **Given** identical scoring inputs and configuration
    - **When** scoring repeats
    - **Then** domain output, canonical JSON bytes, and ranked order are identical
    - **And** the registry includes formula operands/operators, weights, component/penalty order, clamp behavior, fallbacks, warning templates, Memory applicability, tie-break order, serialization rules, and bounds
    - **And** the deeply immutable registry is covered by one persisted SHA-256 digest
    - **And** environment variables or mutable globals cannot alter `scoring-v1`.

11. **Atomic validated scoring evidence and replay**
    - **Given** `ScoreEligibleTechnicians` receives an eligibility-evaluation identifier and complete scoring snapshots
    - **When** it executes
    - **Then** it loads and validates the retained Story 1.4 input/output/configuration and their relationship before scoring
    - **And** validates the scoring output against both scoring input and eligibility evidence before persistence
    - **And** persists one canonical `scoring_evaluation_sets` row linked to the eligibility evaluation and `scoring-v1`
    - **And** identical `(eligibility_evaluation_set_id, configuration_version, input_hash)` retries return the retained validated result
    - **And** changed input or configuration appends distinct immutable evidence
    - **And** configuration, hash, canonical JSON, relationship, candidate count, partition, rank, or summary corruption fails safely
    - **And** any failure rolls back new writes and leaves eligibility and earlier evidence unchanged.

12. **Pre-run evidence does not become Dispatch Run authority**
    - **Given** a scoring evaluation exists before Story 1.7 creates a Dispatch Run
    - **When** it is retained or replayed
    - **Then** it is diagnostic scoring evidence only
    - **And** it creates no Dispatch Run, run snapshot, StageExecution, recommendation, confidence, or State Transition
    - **And** Story 1.7 may reuse it only when exact snapshot/configuration hashes match, otherwise it invokes the same pure policy from the authoritative run snapshot.

13. **Boundary-aligned verification**
    - **Given** unit, contract, real-SQLite, migration, and regression tests execute
    - **When** formula boundaries, Decimal fractions, missing quality, Memory status/applicability, distance thresholds/cap, score clamps, every tie-break, empty/no-feasible/one/many candidate sets, replay, corruption, and rollback are exercised
    - **Then** arithmetic and evidence match `scoring-v1` exactly
    - **And** no ineligible candidate is scored
    - **And** the completed Story 1.4 behavior and 172-test regression remain green
    - **And** process launch, legacy routes, lock, database safety, and `data/learning_store.json` remain unchanged.

## Tasks / Subtasks

- [x] 1. Establish failing scoring tests first (AC: 1-10, 13)
  - [x] Add pure tests for every formula, zero/clamp boundaries, fractional Decimal inputs, missing quality, neutral Memory, rejection of caller/legacy Memory influence, distance 50/over/cap, penalty subtraction, and every tie-break.
  - [x] Add strict contract tests for exact roster binding, sorted/unique snapshots and effects, Decimal-string safety, output component order, rank/partition invariants, stable warnings, and forbidden confidence/recommendation/state fields.
  - [x] Add tests proving ineligible candidates never acquire any scoring field.

- [x] 2. Define pure scoring types and immutable `scoring-v1` registry (AC: 3-10)
  - [x] Add frozen scoring input, component, penalty, warning, ranked-candidate, and output value objects under `app/domain/scoring`.
  - [x] Encode all formulas, weights, fallbacks, component/penalty order, tie-breaks, Decimal serialization, bounds, and warning templates in a deeply immutable registry.
  - [x] Derive canonical registry JSON and SHA-256 from that same complete rule representation.

- [x] 3. Add strict self-contained scoring contracts (AC: 1-10)
  - [x] Add `ScoringInputV1`, Technician scoring snapshot, component/penalty/warning evidence, eligible ranked result, retained ineligible result, and `ScoringOutputV1`.
  - [x] Represent all domain Decimal values as strict canonical decimal strings at JSON boundaries so validation/persistence cannot pass through binary floats.
  - [x] Bind exact eligibility roster, distances, partition, complete component set, score equation, unrounded rank order, and warnings before persistence.

- [x] 4. Implement pure `ScoringPolicy` (AC: 1, 3-10)
  - [x] Score only eligible candidates, calculate all five components and versioned penalties from passed immutable values, and carry ineligible evidence unchanged.
  - [x] Use only `Decimal`, no intermediate quantization, and canonical deterministic accumulation/order.
  - [x] Rank by the full unrounded tie-break chain and return complete safe evidence without I/O.

- [x] 5. Add minimal scoring persistence (AC: 10-13)
  - [x] Add one linear Alembic revision after `20260728_0004` for only `scoring_evaluation_sets`; reuse `configuration_versions`.
  - [x] Store UUID, eligibility/configuration foreign keys, contract version, canonical input/output JSON, input hash, candidate/eligible/ineligible counts, top Technician/score summary, and UTC creation time.
  - [x] Add exact schema/value/JSON/hash/count/partition/top-summary checks and uniqueness on `(eligibility_evaluation_set_id, configuration_version, input_hash)`.
  - [x] Rebase both review migration fixtures and prove fresh plus real `0004 -> 0005` migration.

- [x] 6. Implement `ScoreEligibleTechnicians` through the existing Unit of Work (AC: 1, 2, 10-12)
  - [x] Load and fully validate Story 1.4 retained evidence/configuration; reject relationship or canonical-integrity corruption.
  - [x] Build and validate self-contained scoring input, invoke the pure policy, validate cross-input/output invariants, and persist atomically.
  - [x] Insert/validate immutable `scoring-v1` configuration, replay identical retained evidence, and append changed input.
  - [x] Translate missing/corrupt eligibility, invalid policy output, policy/dependency failure, and persistence failure to sanitized typed application errors.

- [x] 7. Complete integration, documentation, and regression evidence (AC: 11-13)
  - [x] Prove real-SQLite foreign keys, uniqueness/replay, changed-input append, canonical round-trip, configuration digest, corruption rejection, rollback, and source-evidence immutability.
  - [x] Update the development guide with the internal scoring capability and Story 1.6/1.7 seams.
  - [x] Run focused/full tests, compile, offline lock check, process launchers, migration backup/fail-closed checks, import safety, and learning-evidence checksum.

### Review Findings

- [x] [Review][Patch] Use the same task-local Decimal context for policy and every contract recomputation so valid non-terminating fractions are deterministic [app/contracts/scoring.py:165]
- [x] [Review][Patch] Expand the immutable registry to cover all executable formulas, operands, clamp semantics, bounds, evidence schemas, penalty text, and serialization rules, and drive policy/validation from it [app/domain/scoring/rules.py:100]
- [x] [Review][Patch] Complete the claimed boundary, application-command, corruption, rollback, foreign-key, and source-immutability verification matrix [tests/unit/test_scoring_policy.py:33]
- [x] [Review][Patch] Reject floats, booleans, and invalid runtime types at the pure policy seam and honor or validate the registry-declared Decimal rounding mode [app/domain/scoring/policy.py:48]
- [x] [Review][Patch] Snapshot quality supplements through a strict frozen boundary, reject malformed members, and bound Decimal text before parsing [app/application/commands/score_eligible_technicians.py:188]
- [x] [Review][Patch] Validate clock result type before dereferencing it and sanitize every invalid dependency result [app/application/commands/score_eligible_technicians.py:315]
- [x] [Review][Patch] Translate every malformed injected policy result into `InvalidScoringOutput` without leaking ordinary implementation exceptions [app/application/commands/score_eligible_technicians.py:301]
- [x] [Review][Patch] Validate component raw evidence values and formulas rather than only their key sets, and retain one input-bound semantic validation path [app/contracts/scoring.py:150]
- [x] [Review][Patch] Add the missing `test_score_eligible_technicians.py` suite for typed failures, replay, dependency errors, and transaction behavior [tests/unit/test_score_eligible_technicians.py:1]
- [x] [Review][Patch] Reconcile the story Definition of Done and completion record only after every new regression passes [_bmad-output/implementation-artifacts/1-5-score-and-rank-eligible-technicians-deterministically.md:328]

## Dev Notes

### Binding Contract Decisions

#### Capability boundary

- `ScoringPolicy` is a pure internal policy, not an Agent Stage. `ScoreEligibleTechnicians` is an internal application command; this story adds no public endpoint or UI.
- `scoring_evaluation_sets` is reusable pre-run diagnostic evidence, not a Dispatch Run or PLAN authority.
- Story 1.6 calculates confidence and explanation without changing eligibility, score, or rank.
- Story 1.7 owns run snapshots, PLAN StageExecution, recommendation selection, no-feasible terminal behavior, State Transitions, and API integration.

#### Scoring input contract

`ScoringInputV1` contains:

- `schema_version: "v1"`
- `configuration_version: "scoring-v1"`
- `eligibility_evaluation_set_id`
- `sla_minutes`: strict positive integer derived from retained Story 1.3 `sla_target_minutes`
- `technicians`: zero to 100 snapshots, sorted by canonical Technician UUID

Each scoring snapshot contains:

| Field | Contract |
| --- | --- |
| `technician_id` | opaque UUID; exact member of eligibility roster |
| `eta_minutes` | exact retained Story 1.4 `estimated_travel_minutes` |
| `distance_meters` | exact retained Story 1.4 distance evidence |
| `projected_work_minutes` | exact retained `assigned_work_minutes + estimated_travel_minutes + service_minutes` |
| `quality_rating_0_to_5` | canonical Decimal string in `[0,5]` or null |

The application command accepts only `(technician_id, quality_rating_0_to_5)` scoring supplements. It reconstructs every other scoring field from the validated Analyze and eligibility evidence. `scoring-v1` has no Memory-effect input; its empty Memory contribution is neutral 50. Story 3.2 owns a future explicitly versioned active Semantic Pattern integration.

#### Normative `scoring-v1` registry

| Item | Value |
| --- | --- |
| component order | SLA, proximity, workload balance, quality, Memory |
| weights | 0.35, 0.25, 0.20, 0.10, 0.10 |
| maximum workday | 8 hours |
| missing quality | neutral 50 plus warning |
| no active applicable Memory | neutral 50 |
| distance penalty threshold | 50 km |
| distance penalty cap | 20 points |
| other penalties | named/versioned; zero |
| internal arithmetic | Decimal, no intermediate quantization |
| final range | clamp to 0-100 |
| tie-breaks | score desc, SLA desc, quality desc, ETA asc, Technician UUID asc |

The registry stores exact formula tokens/operands/comparisons rather than only labels and scalar settings. Environment variables cannot change it.

#### Decimal and serialization rules

- Construct Decimal constants from strings only.
- Convert integer units exactly: `distance_meters / Decimal("1000")` and `projected_work_minutes / Decimal("60")`.
- Never use Python `float`, JSON floating-point input, or intermediate `quantize`.
- Execute calculations inside a task-local Decimal context with precision 34, `ROUND_HALF_EVEN`, and trapped invalid/division-by-zero/overflow operations. This is deterministic computational precision for non-terminating division, not two-place presentation rounding; never rely on or mutate the process-global context.
- Canonical JSON stores domain Decimal values as normalized non-exponent decimal strings with `-0` normalized to `0`.
- Ranking uses unrounded Decimal values. Two-decimal `ROUND_HALF_UP` numeric rendering belongs to later API presentation code and must not be added here.

#### Output and warning rules

- Eligible candidates have rank, Objective Score, exactly five components, explicit penalties, and structured warnings.
- Ineligible candidates retain their exact six Story 1.4 checks/warnings and have no optional/null score placeholders.
- Missing quality warning template:
  - `code: "SCORING_QUALITY_FALLBACK"`
  - `severity: "warning"`
  - `source: "technician.quality_rating_0_to_5"`
  - `quality: "unavailable"`
  - `freshness: "not_applicable"`
  - `fallback: "50"`
  - stable impact text and `configuration_version: "scoring-v1"`
- Output validation recomputes components, contributions, penalties, score, and order from validated input plus retained eligibility. It does not trust internally consistent but unrelated output.

#### Persistence and replay

- Add one batch-level `scoring_evaluation_sets` table; do not add candidate-score, recommendation, Dispatch Run, Memory, or fixture tables.
- Unique replay scope is `(eligibility_evaluation_set_id, configuration_version, input_hash)`.
- Before treating an input as new, detect canonically matching retained input with a corrupt hash and fail safely.
- On read, verify exact configuration bytes/digest, canonical input/output bytes, input hash, foreign-key identity, counts, partition, top summary, and recomputed output.
- Repositories use the caller-owned connection and never commit.

### Architecture and Reuse Guardrails

- Reuse Story 1.4 strict contracts, canonical JSON, immutable registry/digest, replay-corruption defenses, Unit of Work, configuration repository, UUID/UTC validation, and composite relational integrity patterns.
- Add `get_by_id` to eligibility persistence so the command consumes one validated retained set; do not query mutable Work Order or Technician operational rows from the pure policy.
- Keep domain modules free of Pydantic, SQLAlchemy, FastAPI, SQLite, I/O, clocks, UUID generation, network clients, mutable globals, and Memory repositories.
- Do not add confidence, explanation prose, recommendation selection, public API, SPA changes, Dispatch Run, run snapshot, StageExecution, State Transition, fixture import, KPI, learning, or legacy scoring migration.
- Do not round for display or change Story 1.4 eligibility evidence.

### Expected File Impact

**New:**

- `app/domain/scoring/{__init__,models,rules,policy}.py`
- `app/contracts/scoring.py`
- `app/application/commands/score_eligible_technicians.py`
- `app/adapters/persistence/scoring.py`
- `app/migrations/versions/20260728_0005_scoring_evaluation_sets.py`
- `tests/unit/test_{scoring_contracts,scoring_policy,score_eligible_technicians}.py`
- `tests/integration/test_scoring_persistence.py`
- `tests/contract/test_scoring_policy_contract.py`

**Updated:**

- `app/application/ports/persistence.py`
- `app/adapters/persistence/eligibility.py`
- `app/adapters/persistence/schema.py`
- `app/adapters/persistence/unit_of_work.py`
- `tests/integration/test_migrations.py`
- both migration fixture heads
- `docs/development-guide.md`
- sprint/story tracking artifacts

Do not update `app/api/v1/*`, `app/main.py`, `frontend/*`, `server.py`, `app/adapters/legacy/compatibility.py`, or `data/learning_store.json`.

### Testing Requirements

- Follow red-green-refactor.
- Pure policy: each formula, exact zero/100 clamps, fractional results under the bound local Decimal context, weight sum, missing rating, rating 0/5, neutral Memory and rejection of caller/legacy influence, 50 km/over/cap, total subtraction, final clamps, empty/one/many candidates, every tie-break, input-order independence.
- Contracts: strict no-float Decimals, positive SLA, roster/distance binding, duplicate/unsorted snapshots/effects, exact components/penalties, malformed formulas/contributions/scores/ranks, warning mismatch, ineligible scoring leakage, forbidden confidence/recommendation/state fields.
- Application: missing/corrupt eligibility/configuration, invalid policy output, policy/clock/UUID failures, identical replay, changed input, sanitized persistence failure.
- Integration: real SQLite, incremental `0004 -> 0005`, exact schema/check/index/FK allowlists, canonical round-trip, configuration digest, uniqueness, changed-input append, corruption, rollback, source evidence unchanged.
- No browser, provider, confidence, orchestrator, Memory database, performance benchmark, or public API test belongs to this story.

### Latest Technical Information

- Keep pinned dependencies; do not upgrade opportunistically.
- Python `decimal` provides exact base-10 arithmetic and explicit rounding modes. Construct values from strings and retain the existing task-local Decimal context behavior. [Python Decimal documentation](https://docs.python.org/3/library/decimal.html).
- Pydantic v2 supports strict Decimal boundary validation and cross-field model validators; the project boundary intentionally serializes domain Decimals as canonical strings to prevent JSON float contamination. [Pydantic Decimal types](https://docs.pydantic.dev/latest/api/standard_library_types/#decimals) and [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/).
- SQLAlchemy Core supports the required check, composite foreign-key, and unique constraints while transaction ownership remains with the Unit of Work. [SQLAlchemy constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html) and [Core transactions](https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html).

### Project Structure Notes

- No Git metadata is available; preserve `baseline_commit: NO_VCS`.
- Story 1.4 is done after all 14 review patches and 172 passing tests.
- Architecture and PRD formulas are normative; do not invent alternate scoring, distance, Memory, or tie-break rules.
- No UX work is required in this internal story. The first integrated visible workflow is owned by Story 1.7 and exposed through Story 1.9.
- `data/learning_store.json` must retain SHA-256 `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.5]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — UJ-1, FR10-FR12, NFR2, NFR4, NFR7, SM-2, SM-4, SM-9]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-16, AD-18, AD-23, AD-24, AD-27]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — §§5-8, 10, 13-14, 17-18]
- [Source: `_bmad-output/project-context.md` — Decimal, determinism, policy, and testing rules]
- [Source: `_bmad-output/implementation-artifacts/1-4-determine-technician-eligibility-before-scoring.md` — completed eligibility capability and review learnings]
- [Source: `app/domain/eligibility/*`, `app/contracts/eligibility.py`, `app/application/commands/determine_technician_eligibility.py`, `app/adapters/persistence/*` — current implementation seams]

## Definition of Done

- [x] All tasks/subtasks and acceptance criteria are complete with tests passing.
- [x] Only eligible Technicians receive exactly five components, penalties, Objective Score, and rank.
- [x] All formulas, weights, fallbacks, Memory rules, penalties, and tie-breaks match `scoring-v1`.
- [x] Decimal arithmetic remains exact and unrounded until the future API presentation boundary.
- [x] Input/output/configuration and persisted evidence are strict, immutable, canonical, replay-safe, and reproducible.
- [x] Corruption or failure cannot leave partial evidence or mutate Story 1.4 evidence.
- [x] No confidence, recommendation, public API, browser, Dispatch Run, State Transition, Memory database, or legacy-migration scope leaked into the story.
- [x] Full regression, lock, compile, migration, import-safety, process-launch, and evidence-integrity checks pass.
- [x] Dev Agent Record lists exact commands/results and every changed file.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Test-first deterministic Decimal scoring domain and strict boundary contracts.
- Atomic append-only scoring evidence through the existing Unit of Work.
- Full formula, tie-break, corruption, migration, and regression verification.

### Debug Log References

- RED: scoring tests failed during collection because the scoring domain and contract modules did not exist.
- GREEN: pure formula/contract tests passed after implementing the Decimal policy and strict semantic boundary.
- Full regression remained green after persistence, migration, application-command, and documentation integration.

### Completion Notes List

- Implemented exact `scoring-v1` SLA, proximity, workload, quality, neutral Memory, distance penalty, Objective Score, and five-level deterministic ranking.
- Added self-contained scoring evidence that embeds the validated eligibility output, binds travel/distance/workload to Story 1.4, and preserves complete ineligible constraint evidence without scoring fields.
- Added registry-backed quality fallback warnings, task-local Decimal precision, canonical decimal-string persistence, immutable configuration digest, corruption-safe replay, and atomic Unit of Work behavior.
- Added the linear `20260728_0005` migration and verified fresh plus `0004 -> 0005` upgrades, exact schema/constraints/FKs, replay, changed quality, corruption failure, and source evidence preservation.
- Verification: 225 tests pass (223 sandbox-safe plus 2 loopback process tests), compile passes, offline lock resolves 28 packages, and learning evidence SHA-256 remains `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.
- Resolved all 10 code-review patches: shared task-local Decimal arithmetic, complete executable registry evidence, strict pure-policy/request boundaries, sanitized failures, formula-bound raw evidence, and expanded application/persistence/migration coverage.

### File List

- _bmad-output/implementation-artifacts/1-5-score-and-rank-eligible-technicians-deterministically.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- app/adapters/persistence/eligibility.py
- app/adapters/persistence/schema.py
- app/adapters/persistence/scoring.py
- app/adapters/persistence/unit_of_work.py
- app/application/commands/score_eligible_technicians.py
- app/application/ports/persistence.py
- app/contracts/scoring.py
- app/domain/scoring/__init__.py
- app/domain/scoring/arithmetic.py
- app/domain/scoring/models.py
- app/domain/scoring/policy.py
- app/domain/scoring/rules.py
- app/migrations/versions/20260728_0005_scoring_evaluation_sets.py
- docs/development-guide.md
- tests/contract/test_scoring_policy_contract.py
- tests/fixtures/migrations/failure/20260728_0002_review_failure.py
- tests/fixtures/migrations/success/20260728_0002_review_success.py
- tests/integration/test_migrations.py
- tests/integration/test_scoring_persistence.py
- tests/unit/test_scoring_contracts.py
- tests/unit/test_scoring_policy.py
- tests/unit/test_score_eligible_technicians.py

### Change Log

- 2026-07-28: Created implementation-ready Story 1.5 context from the final PRD, Architecture Spine, completed Story 1.4, and current codebase.
- 2026-07-28: Implemented deterministic Decimal scoring, immutable replay-safe evidence, migration, and full regression coverage; moved Story 1.5 to review.
- 2026-07-28: Addressed all 10 code-review findings, raised verification to 225 passing tests, and completed Story 1.5.

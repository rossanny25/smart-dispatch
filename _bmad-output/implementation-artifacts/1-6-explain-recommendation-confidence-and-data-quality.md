---
baseline_commit: NO_VCS
---

# Story 1.6: Explain Recommendation Confidence and Data Quality

Status: done

## Story

As a dispatcher,
I want to see how trustworthy the recommendation is and which data limitations affect it,
so that I can make an informed decision without confusing a high score with high certainty.

## Requirements Traceability

- **Functional:** FR12, FR13, FR14.
- **Non-functional:** NFR2, NFR4, NFR7.
- **Architecture:** AD-1, AD-3-AD-7, AD-10, AD-11, AD-13, AD-15, AD-16, AD-18, AD-24, AD-26, AD-27.
- **Success metrics:** SM-6 and deterministic/auditable evidence required by SM-2 and SM-9.
- **Dependencies:** consumes the validated Story 1.5 scoring evaluation and its retained Story 1.4 eligibility evidence. Story 1.7 owns Dispatch Run authority, recommendation state, StageExecution, transitions, and public run API.

## Acceptance Criteria

1. **Confidence remains independent from Objective Score**
   - Given at least one eligible ranked candidate, `ConfidencePolicy` calculates confidence without modifying candidate scores, components, penalties, ranks, warnings, or eligibility evidence.
   - The output exposes every factor, weight, weighted contribution, final value, label, and configuration version.
   - With no eligible candidate, Recommendation Confidence and recommended Technician are unavailable while complete ineligible evidence remains available.

2. **Normative confidence formula**
   - `confidence = clamp(0.35 × data_quality + 0.25 × historical_evidence + 0.25 × score_margin + 0.15 × condition_certainty)`.
   - Internal calculations use the shared task-local Decimal rules with no binary float or intermediate presentation rounding.
   - Labels are `low` for 0–49, `medium` for 50–74, and `high` for 75–100.

3. **Data quality is derived from applicable sources**
   - Current, stale, and unavailable sources contribute Decimal 100, 75, and 50.
   - `data_quality` is the arithmetic mean of all applicable source-quality values.
   - The v1 applicable source set is GPS for every ranked Technician plus traffic, weather, and historical evidence for the evaluation.
   - Missing source timestamps are unavailable. Negative ages or non-UTC evaluation/source timestamps fail validation.

4. **Freshness classification and fallbacks are exact**
   - GPS age at most 5 minutes is current, over 5 through 30 is stale, and over 30 is unavailable.
   - Traffic and weather age at most 15 minutes is current, over 15 through 60 is stale, and over 60 is unavailable.
   - Unavailable GPS uses a last-known zone only when supplied and marks it estimated; otherwise its fallback is unavailable.
   - Unavailable traffic/weather uses the documented seeded/default scenario value.
   - Historical evidence with at least one active supporting episode is current; zero episodes is unavailable and uses no-history fallback.

5. **Historical evidence factor is bounded and scoped**
   - `historical_evidence = min(100, 10 × active_supporting_episode_count)`.
   - The count is a strict integer from 0 through 10,000.
   - Only active, applicable supporting episodes may be counted; inactive hypotheses and unrelated episodes are outside the input contract.

6. **Score margin is deterministic**
   - With two or more eligible candidates, `score_margin = min(100, 10 × (first_score − second_score))`.
   - With exactly one eligible candidate it is 50.
   - With no eligible candidate it is unavailable together with Recommendation Confidence.
   - The policy consumes Story 1.5 order and validates that the margin is non-negative; it never re-ranks.

7. **Condition certainty is explainable**
   - `condition_certainty = clamp(100 − 25 × uncertain_condition_count)`.
   - Every counted condition is a unique, sorted, structured identifier from the bounded v1 vocabulary: `gps_estimated`, `traffic_defaulted`, `weather_defaulted`, `historical_evidence_missing`.
   - The policy derives this set from source classifications/fallbacks; callers cannot inject a conflicting count.

8. **Warnings are structured, stable, and reproducible**
   - Every missing, stale, estimated, or unavailable source creates a warning with stable code, severity, source, affected field, observed quality, freshness/age, fallback, impact, optional Technician identifier, and configuration version.
   - Warning text comes from the immutable registry, not callers or generated reasoning.
   - Warnings are unique and canonically ordered by source, Technician identifier, affected field, and code.

9. **Alternatives and explanation remain evidence-based**
   - Eligible alternatives retain Story 1.5 ranking, Objective Score, full score breakdown, confidence context, and applicable warnings.
   - Ineligible Technicians remain separate with all Story 1.4 discard reasons and no score or confidence.
   - The explanation is a concise structured template containing the leading Technician, its score, separate confidence value/label, score-margin evidence, limiting confidence factors, and warning codes.
   - No private chain-of-thought, provider reasoning, or caller-supplied prose is stored.

10. **Complete immutable `confidence-v1` registry**
    - The registry contains factor order, formulas, weights, thresholds, source-quality values, applicable-source rules, fallback/warning templates, uncertain-condition derivation, label boundaries, Decimal behavior, ordering, bounds, and serialization rules.
    - One canonical registry JSON and SHA-256 digest cover the executable rules.
    - Environment variables and mutable globals cannot alter the registry.

11. **Atomic validated evidence and replay**
    - `EvaluateRecommendationConfidence` loads and fully validates retained Story 1.5 input/output/configuration before calculation.
    - It persists one canonical `confidence_evaluation_sets` row linked to the scoring evaluation and `confidence-v1`.
    - Identical `(scoring_evaluation_set_id, configuration_version, input_hash)` retries return the retained validated result; changed evidence appends a new immutable row.
    - Configuration, digest, canonical JSON, relationship, counts, recommendation summary, confidence summary, warning count, or source evidence corruption fails safely.
    - Any failure rolls back new writes and leaves Stories 1.1–1.5 evidence unchanged.

12. **Pre-run evidence is not Dispatch Run authority**
    - The evaluation is diagnostic EVALUATE evidence only.
    - It creates no Dispatch Run, StageExecution, state transition, assignment, outcome, learning episode, semantic pattern, API route, or UI.
    - Story 1.7 may reuse it only when exact immutable snapshot/configuration hashes match.

13. **Boundary-aligned verification**
    - Unit tests cover formulas, Decimal fractions, every freshness boundary, no/one/many candidates, label boundaries, warning/fallback combinations, uncertainty derivation, input-order independence, high-score/low-confidence separation, and pure-policy invalid types.
    - Contract tests cover strict timestamps/Decimal strings, source roster binding, warning/factor order, output recomputation, no-feasible behavior, explanation safety, and forbidden unknown fields.
    - Real-SQLite tests cover fresh and incremental migration, schema/FKs/checks, replay, changed input, corruption, rollback, and preservation of source evidence.
    - Full regression, compile, offline lock, process launch, import safety, and learning-store integrity remain green.

## Tasks / Subtasks

- [x] 1. Add failing Story 1.6 unit and contract tests first (AC: 1-10, 13).
- [x] 2. Define frozen confidence domain models and complete immutable `confidence-v1` registry (AC: 2-10).
- [x] 3. Implement pure `ConfidencePolicy` with exact Decimal arithmetic and structured warnings/explanation (AC: 1-9).
- [x] 4. Add strict self-contained `ConfidenceInputV1` and `ConfidenceOutputV1` contracts with semantic recomputation (AC: 1-10).
- [x] 5. Add linear migration `0006`, persistence model/repository, Unit of Work port, and corruption-safe replay (AC: 10-13).
- [x] 6. Implement `EvaluateRecommendationConfidence` and typed sanitized failures (AC: 1, 3-12).
- [x] 7. Complete focused/full validation, documentation, review corrections, and tracking evidence (AC: 11-13).

### Review Findings

- [x] [Review][Patch] Remove binary floating point from freshness arithmetic and honor the configured trapped Decimal context [app/domain/confidence/policy.py:246]
- [x] [Review][Patch] Bind and validate the complete canonical Story 1.5 scoring output on every command/replay path [app/contracts/confidence.py:343]
- [x] [Review][Patch] Make all executable warning, fallback, bound, and explanation rules deeply immutable and digest-covered [app/domain/confidence/rules.py:91]
- [x] [Review][Patch] Expose estimated/unavailable/defaulted fallback quality explicitly, including unavailable GPS without a zone [app/domain/confidence/policy.py:263]
- [x] [Review][Patch] Produce a complete structured explanation with typed registry-owned parameters [app/contracts/confidence.py:201]
- [x] [Review][Patch] Constrain environment fallback evidence to the exact registry defaults [app/contracts/confidence.py:76]
- [x] [Review][Patch] Enforce exact UUID, rank, object, and tuple types at the pure policy seam [app/domain/confidence/policy.py:198]
- [x] [Review][Patch] Add the missing application, contract, boundary, corruption, rollback, and schema verification matrix [tests/unit/test_confidence_policy.py:52]

## Dev Notes

### Binding Contract

- The application request contains the scoring evaluation identifier, UTC `evaluated_at`, GPS observations keyed exactly to eligible Technician UUIDs, traffic/weather observations, and `active_supporting_episode_count`.
- Each observation contains a UTC `observed_at` or null. GPS additionally contains optional `last_known_zone`; traffic/weather contain the stable configured default fallback.
- Data-quality inputs are evidence only. They do not alter ETA, distance, score, rank, or eligibility.
- Historical evidence participates both as a data-quality source and as the separately weighted historical-evidence factor. This is deliberate in PRD v1.
- All output Decimals cross JSON boundaries as canonical non-exponent strings; two-place `ROUND_HALF_UP` belongs to the future API presentation layer.

### Expected File Impact

**New:**

- `app/domain/confidence/{__init__,models,rules,policy}.py`
- `app/contracts/confidence.py`
- `app/application/commands/evaluate_recommendation_confidence.py`
- `app/adapters/persistence/confidence.py`
- `app/migrations/versions/20260728_0006_confidence_evaluation_sets.py`
- `tests/unit/test_{confidence_policy,confidence_contracts,evaluate_recommendation_confidence}.py`
- `tests/integration/test_confidence_persistence.py`
- `tests/contract/test_confidence_policy_contract.py`

**Updated:**

- persistence ports, schema, Unit of Work, migration tests/fixtures, development guide, sprint/story tracking.

Do not update public API/UI, legacy compatibility, Dispatch Run tables, scoring rules/results, eligibility evidence, or `data/learning_store.json`.

### Reuse and Safety

- Reuse scoring canonical JSON/Decimal helpers, scoring output semantic validation, immutable configuration persistence, UUID/UTC validation, Unit of Work ownership, and append-only replay patterns.
- Domain code remains free of Pydantic, SQLAlchemy, FastAPI, SQLite, I/O, clocks, UUID generation, environment reads, mutable globals, and provider/model calls.
- Never expose chain-of-thought. Explanation is reconstructed exclusively from structured retained fields and registry templates.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 1.6]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — FR12-FR14]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-16, AD-18, AD-24, AD-27]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — §§5-8, 10, 13-14]
- [Source: `_bmad-output/project-context.md`]
- [Source: `_bmad-output/implementation-artifacts/1-5-score-and-rank-eligible-technicians-deterministically.md`]

## Definition of Done

- [x] All acceptance criteria and tasks are implemented and tested.
- [x] Confidence, score, rank, and eligibility remain demonstrably separate.
- [x] Every formula, freshness threshold, fallback, warning, label, and ordering rule matches `confidence-v1`.
- [x] Evidence is strict, canonical, immutable, replay-safe, corruption-detecting, and atomic.
- [x] Full regression and repository integrity checks pass.
- [x] Code review findings are resolved and the exact verification record/file list is complete.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Test-first pure confidence policy and strict contracts.
- Atomic append-only confidence evidence over validated Story 1.5 results.
- Full formula, boundary, replay, corruption, migration, and regression validation.

### Debug Log References

- RED: Story 1.6 tests initially failed because confidence domain and contract modules did not exist.
- GREEN: focused domain/contract tests passed after implementing the pure Decimal policy and strict boundary.
- Integration exposed strict nested tuple serialization and migration-test placement defects; both received failing regressions and were corrected.

### Completion Notes List

- Implemented independent `confidence-v1` factors, freshness classification, source-quality evidence, deterministic warnings, uncertainty evidence, labels, and registry-owned explanation templates.
- Added strict frozen input/output contracts that bind rank/score evidence to Story 1.5 and fully recompute confidence output before persistence.
- Added append-only, replay-safe confidence evidence, linear migration `0006`, Unit of Work integration, and corruption-safe repository reads.
- Verification after review: 266 tests pass (264 sandbox-safe plus 2 local launch tests), compile passes, offline lock resolves 28 packages, and the learning-store SHA-256 remains `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.
- Resolved all eight review patch groups: exact integer-backed freshness arithmetic, trapped configured Decimal behavior, complete scoring-output digest binding, deeply immutable rule evidence, explicit fallback quality, structured explanation parameters, strict pure-policy boundaries, and expanded failure/corruption/migration coverage.

### File List

- `_bmad-output/implementation-artifacts/1-6-explain-recommendation-confidence-and-data-quality.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `app/adapters/persistence/confidence.py`
- `app/adapters/persistence/schema.py`
- `app/adapters/persistence/scoring.py`
- `app/adapters/persistence/unit_of_work.py`
- `app/application/commands/evaluate_recommendation_confidence.py`
- `app/application/ports/persistence.py`
- `app/contracts/confidence.py`
- `app/domain/confidence/__init__.py`
- `app/domain/confidence/models.py`
- `app/domain/confidence/policy.py`
- `app/domain/confidence/rules.py`
- `app/migrations/versions/20260728_0006_confidence_evaluation_sets.py`
- `docs/development-guide.md`
- `tests/contract/test_confidence_policy_contract.py`
- `tests/fixtures/migrations/failure/20260728_0002_review_failure.py`
- `tests/fixtures/migrations/success/20260728_0002_review_success.py`
- `tests/integration/test_confidence_persistence.py`
- `tests/integration/test_migrations.py`
- `tests/unit/test_confidence_contracts.py`
- `tests/unit/test_confidence_policy.py`
- `tests/unit/test_evaluate_recommendation_confidence.py`

### Change Log

- 2026-07-28: Created implementation-ready Story 1.6 from the final PRD, Architecture Spine, completed Story 1.5, and current codebase.
- 2026-07-28: Implemented and validated deterministic confidence/data-quality evidence; moved Story 1.6 to review.
- 2026-07-28: Addressed all eight code-review patch groups, raised verification to 266 passing tests, and completed Story 1.6.

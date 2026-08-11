---
baseline_commit: NO_VCS
---

# Story 1.4: Determine Technician Eligibility Before Scoring

Status: done

## Story

As a dispatcher,
I want every Technician evaluated against all safety and operational constraints,
so that no ineligible Technician can enter the recommendation ranking.

## Requirements Traceability

- **Functional:** FR6, FR7, FR8, FR9.
- **Non-functional:** NFR2, NFR7.
- **Journey:** UJ-1, limited to feasibility before ranking.
- **Architecture:** AD-1, AD-3, AD-4, AD-5, AD-6, AD-7, AD-10, AD-11, AD-13, AD-15, AD-16, AD-18, AD-23, AD-26, and AD-27.
- **Epic requirements registry:** AR1, AR3-AR7, AR10, AR11, AR13, AR15, AR16, AR21, AR24, AR25, AR27-AR29.
- **Success/counter-metrics:** SM-1 and SM-C2.
- **Dependencies:** consumes Story 1.3 Analyze evidence and canonical certification codes. Story 1.5 scores only the eligible output. Story 1.7 owns Dispatch Runs, run snapshots, PLAN execution, State Transitions, and the terminal `NO_FEASIBLE_CANDIDATES` outcome.

## Acceptance Criteria

1. **All Hard Constraints execute before scoring**
   - **Given** a validated Story 1.3 analysis and an immutable Technician roster
   - **When** `DetermineTechnicianEligibility` invokes `EligibilityPolicy` with `eligibility-v1`
   - **Then** every Technician receives exactly six checks in fixed order: `availability`, `certifications`, `shift`, `maximum_workday`, `driving_limit`, and `required_epp`
   - **And** every check produces `pass` or `fail` plus a stable reason and structured evidence
   - **And** all checks run even after an earlier failure
   - **And** a Technician is eligible only when all six checks pass
   - **And** the output contains no Objective Score, scoring component, confidence, rank, recommendation, or Memory evidence.

2. **Strict, self-contained eligibility contracts**
   - **Given** input or output crosses the eligibility boundary
   - **When** Pydantic validates `EligibilityInputV1` or `EligibilityOutputV1`
   - **Then** strict types and timezone-aware UTC timestamps are required and unknown fields are forbidden
   - **And** the input contains analyzed requirements, captured UTC time, zero to 100 complete Technician snapshots, resolved shift boundaries, travel values, and configuration version
   - **And** the policy receives no repository handle, Work Order ID lookup, mutable operational row, clock service, network client, or Memory adapter
   - **And** invalid or semantically inconsistent output fails before persistence.

3. **Availability is a hard gate**
   - **Given** a Technician availability is `busy`, `absent`, or `off_duty`
   - **When** eligibility is evaluated
   - **Then** `availability` fails with `TECHNICIAN_UNAVAILABLE`
   - **And** only the exact state `available` passes
   - **And** all remaining checks still execute.

4. **Every required certification is mandatory**
   - **Given** analyzed requirements contain one or more canonical certification codes
   - **When** a Technician possesses only a subset
   - **Then** `certifications` fails with `CERTIFICATIONS_MISSING`
   - **And** evidence contains sorted canonical `required`, `possessed`, and `missing` code lists
   - **And** display labels, priority, and Memory cannot alter the result
   - **And** an empty required list passes with `NO_CERTIFICATIONS_REQUIRED`.

5. **Shift and maximum workday are independent hard gates**
   - **Given** `captured_at`, `shift_start`, `shift_end`, estimated travel, and estimated service duration
   - **When** shift eligibility is calculated
   - **Then** assignment starts only when `shift_start <= captured_at < shift_end`
   - **And** `projected_finish = captured_at + travel_minutes + service_minutes`
   - **And** shift passes only when `projected_finish <= shift_end`.
   - **Given** current assigned work and the configured maximum workday
   - **When** maximum-day eligibility is calculated
   - **Then** `projected_workday_minutes = assigned_work_minutes + travel_minutes + service_minutes`
   - **And** the check passes at exactly 480 minutes and fails above 480
   - **And** priority 5 never bypasses either check.

6. **Four-hour driving limit fails closed**
   - **Given** the `driving_limit` check is enabled
   - **When** accumulated driving plus estimated outbound travel is evaluated
   - **Then** it passes at exactly 240 minutes and fails above 240 with `DRIVING_LIMIT_EXCEEDED`
   - **And** a missing accumulated-driving value fails with `SOURCE_DATA_UNAVAILABLE`
   - **And** a disabled driving check in any explicitly versioned future policy configuration fails with `CHECK_DISABLED`
   - **And** either missing or disabled evidence emits one structured safety warning rather than an implicit pass.

7. **EPP is mandatory for priority 4-5**
   - **Given** analyzed priority is 4 or 5
   - **When** the `required_epp` check is enabled
   - **Then** `has_required_epp: true` passes and `false` fails with `REQUIRED_EPP_MISSING`
   - **And** a missing EPP value fails with `SOURCE_DATA_UNAVAILABLE`
   - **And** a disabled required EPP check in any explicitly versioned future policy configuration fails with `CHECK_DISABLED`
   - **And** missing or disabled evidence emits one structured safety warning.
   - **Given** priority is 1-3
   - **When** EPP is evaluated
   - **Then** it passes with `EPP_NOT_REQUIRED_FOR_PRIORITY` without needing EPP source data.

8. **Distance never changes eligibility**
   - **Given** a Technician is more than 50,000 meters from the Work Order
   - **When** eligibility is evaluated
   - **Then** distance is retained as downstream evidence but no distance Hard Constraint exists
   - **And** the Technician remains eligible if every configured Hard Constraint passes
   - **And** Story 1.5 may later apply the versioned soft distance penalty.

9. **Complete candidate evidence and no feasible set**
   - **Given** a Technician fails several checks
   - **When** output is assembled
   - **Then** all failures are present and no check short-circuits
   - **And** candidates are sorted by ascending opaque Technician UUID
   - **And** `eligible_technician_ids` and `ineligible_technician_ids` are sorted and exactly partition the candidate set.
   - **Given** the roster is empty or no Technician passes every check
   - **When** eligibility completes
   - **Then** `eligible_technician_ids` is empty and `no_feasible_candidates` is true
   - **And** no recommendation, score, confidence, or State Transition is fabricated.

10. **Deterministic configuration and canonical bytes**
    - **Given** identical analyzed requirements, Technician roster, travel data, captured clock, and `eligibility-v1`
    - **When** the policy runs repeatedly
    - **Then** the structured domain output and canonical JSON bytes are identical
    - **And** candidate, certification, check, and warning ordering is deterministic
    - **And** the output contains no generated UUID, runtime clock read, mutable global value, network result, or Memory data
    - **And** the deeply immutable `eligibility-v1` registry and every rule/default are covered by its persisted SHA-256 digest.

11. **Atomic validated evidence and replay**
    - **Given** `DetermineTechnicianEligibility` receives an analysis identifier, self-contained roster/travel snapshots, captured time, and configuration version
    - **When** it executes
    - **Then** it loads and validates the retained Story 1.3 analysis and `analysis-v1` configuration before calculation
    - **And** validates `EligibilityOutputV1` before inserting evidence
    - **And** persists one canonical `eligibility_evaluation_sets` row linked to Work Order, analysis, and `eligibility-v1`
    - **And** identical `(analysis_id, configuration_version, input_hash)` retries return the retained validated result
    - **And** a changed roster, travel value, clock, or configuration produces a distinct immutable evaluation set
    - **And** configuration, input hash, output JSON, and queryable summary corruption fail safely
    - **And** any command failure rolls back all new writes and leaves Work Order/analysis evidence unchanged.

12. **Historical priority-5 defect is corrected without broad migration**
    - **Given** the preserved legacy simulation reaches a priority-5 candidate whose projected workday exceeds eight hours
    - **When** its compatibility evaluation branch executes
    - **Then** it returns a rejected candidate with an overtime alert
    - **And** does not raise the historical `alerts.push(...)` `AttributeError`
    - **And** does not preserve the superseded priority-5 overtime exception
    - **And** no broader legacy route delegation, canonical browser migration, or legacy scoring rewrite is introduced.

13. **Boundary-aligned verification**
    - **Given** unit, contract, real-SQLite, migration, legacy regression, and full regression tests run
    - **When** single and combined failures, exact boundaries, missing/disabled safety inputs, distant candidates, no-feasible candidates, replay, corruption, and rollback are exercised
    - **Then** 100% of ineligible Technicians are rejected before ranking
    - **And** every Technician retains all six check results
    - **And** the completed Story 1.3 behavior and 117-test regression remain green
    - **And** process launch, legacy routes, import safety, lock, database safety, and `data/learning_store.json` evidence remain unchanged except for the explicitly corrected priority-5 branch.

## Tasks / Subtasks

- [x] 1. Establish failing eligibility tests first (AC: 1-10, 12, 13)
  - [x] Add pure tests for each Hard Constraint, all exact boundaries, multiple simultaneous failures, disabled/missing safety data, priority 5, distance over 50 km, deterministic ordering, and no feasible candidates.
  - [x] Add strict contract tests for input/output, UTC times, UUIDs, empty and nonempty rosters, canonical codes/order, six-check completeness, partition invariants, warning consistency, and forbidden score/rank/recommendation fields.
  - [x] Add the failing legacy priority-5 overtime regression before changing the compatibility branch.

- [x] 2. Define pure eligibility types and immutable `eligibility-v1` registry (AC: 1, 3-10)
  - [x] Add frozen Technician, requirements, configuration, check-evidence, warning, candidate, and output value objects under `app/domain/eligibility`.
  - [x] Bind 480 maximum workday minutes, 240 driving minutes, EPP priority threshold 4, exact boundaries, check order, reason codes, and fail-closed missing/disabled semantics.
  - [x] Deep-freeze runtime structures and derive canonical registry JSON/digest from the same complete rule representation.

- [x] 3. Add strict self-contained eligibility contracts (AC: 1-10)
  - [x] Add `EligibilityInputV1`, Technician snapshot, six check-result contract variants, structured safety warning, candidate result, and `EligibilityOutputV1`.
  - [x] Enforce aware UTC timestamps, nonnegative minute/meter bounds, unique/sorted certification codes, unique Technician IDs, fixed candidate/check order, exact eligible/ineligible partition, and no unknown fields.
  - [x] Keep score, rank, confidence, recommendation, Memory, and state fields absent and forbidden.

- [x] 4. Implement pure `EligibilityPolicy` (AC: 1, 3-10)
  - [x] Evaluate all six checks without short-circuiting and use only passed immutable input/configuration.
  - [x] Apply inclusive limit semantics, fail-closed safety rules, priority-independent overtime rejection, and EPP threshold exactly.
  - [x] Return canonically ordered output with complete safe evidence and no I/O.

- [x] 5. Add minimal eligibility persistence (AC: 10, 11, 13)
  - [x] Add one linear Alembic revision after `20260728_0003` for only `eligibility_evaluation_sets`; reuse `configuration_versions`.
  - [x] Store UUID, Work Order/analysis/configuration foreign keys, contract version, canonical input/output JSON, input hash, candidate/eligible/ineligible counts, no-feasible flag, and UTC creation time.
  - [x] Add exact schema/value/JSON/hash/count checks and uniqueness on `(work_order_analysis_id, configuration_version, input_hash)`.
  - [x] Rebase both review migration fixtures and prove fresh plus real Story 1.3 incremental migration.

- [x] 6. Implement `DetermineTechnicianEligibility` through the existing Unit of Work (AC: 2, 10, 11)
  - [x] Load and validate Story 1.3 analysis/configuration, build the self-contained input, invoke the pure policy, and validate output before persistence.
  - [x] Insert/validate immutable `eligibility-v1` configuration without import-time I/O.
  - [x] Replay identical retained results; validate configuration, input hash, canonical JSON, summary columns, and foreign-key identity before return.
  - [x] Translate missing/corrupt analysis, invalid policy output, policy failure, and persistence failure to sanitized typed application errors.

- [x] 7. Correct only the owned legacy defect (AC: 12, 13)
  - [x] Replace the broken priority-5 `push` branch with deterministic rejection and `append`, preserving the legacy response shape.
  - [x] Prove projected overtime is rejected for priority 5 and lower priorities without changing unrelated legacy routes, candidate scoring, global data, or SPA behavior.

- [x] 8. Complete integration, documentation, and regression evidence (AC: 11-13)
  - [x] Prove real-SQLite foreign keys, uniqueness/replay, changed-input append, canonical round-trip, configuration digest, corruption translation, rollback, and source evidence immutability.
  - [x] Update the development guide with the internal eligibility capability and Story 1.5/1.7 seams.
  - [x] Run focused/full tests, compile, offline lock check, process launchers, migration backup/fail-closed checks, import safety, and learning-evidence checksum.

### Review Findings

- [x] [Review][Patch] Bind every validated output to the exact input roster, identifiers, distances, count, and canonical ordering on both new execution and replay [app/application/commands/determine_technician_eligibility.py:192]
- [x] [Review][Patch] Replace generic check evidence with six strict discriminated evidence contracts and semantic calculations [app/contracts/eligibility.py:236]
- [x] [Review][Patch] Recompute and compare retained canonical output from retained input so unrelated but individually valid evidence cannot replay [app/adapters/persistence/eligibility.py:49]
- [x] [Review][Patch] Expand the immutable registry to cover formula operands, comparisons, missing-data behavior, reason selection, warning templates, evidence schemas, and partition rules; execute configured check order [app/domain/eligibility/rules.py:131]
- [x] [Review][Patch] Detect a retained row whose canonical input matches but whose stored input hash was corrupted instead of silently inserting a replacement [app/adapters/persistence/eligibility.py:31]
- [x] [Review][Patch] Rebuild Story 1.3 Analyze input from the retained Work Order and verify its SHA-256 before consuming analysis evidence [app/application/commands/determine_technician_eligibility.py:97]
- [x] [Review][Patch] Bind warning code, quality, source, impact, and affected check to immutable registry templates [app/contracts/eligibility.py:257]
- [x] [Review][Patch] Reject naive or noncanonical retained UTC timestamps [app/adapters/persistence/eligibility.py:23]
- [x] [Review][Patch] Sanitize clock/UUID dependency failures and reject non-UUID factory values [app/application/commands/determine_technician_eligibility.py:205]
- [x] [Review][Patch] Fail closed on projected-finish datetime overflow while retaining complete candidate evidence [app/domain/eligibility/policy.py:145]
- [x] [Review][Patch] Enforce the Work Order-to-analysis relationship in SQLite with a composite foreign key [app/adapters/persistence/schema.py:124]
- [x] [Review][Patch] Complete the explicit policy/contract/application/legacy boundary matrix claimed by AC13 [tests/unit/test_eligibility_policy.py:46]
- [x] [Review][Patch] Verify every eligibility migration constraint, index, and foreign key rather than columns alone [tests/integration/test_migrations.py:207]
- [x] [Review][Patch] Include story and sprint tracking artifacts in the Dev Agent Record File List [_bmad-output/implementation-artifacts/1-4-determine-technician-eligibility-before-scoring.md:402]

## Dev Notes

### Binding Contract Decisions

#### Capability boundary

- `EligibilityPolicy` is a pure internal policy, not an Agent Stage, and `DetermineTechnicianEligibility` is an internal application command. Story 1.4 adds no HTTP endpoint.
- The policy accepts a complete value snapshot. It never loads Technicians, analysis, time, traffic, configuration, or Memory itself.
- `eligibility_evaluation_sets` is reusable pre-run diagnostic evidence, not a Dispatch Run, run snapshot, PLAN `StageExecution`, candidate score, recommendation, or run authority.
- Story 1.7 owns authoritative run evidence. It may reuse a retained set only after the run-snapshot eligibility input hash and configuration digest match exactly; it then copies the validated canonical input/output into PLAN evidence and links the source set. Otherwise it invokes the same pure policy from the immutable `run_snapshot`. The PLAN `StageExecution`, never the pre-run set, is authoritative for that run.
- Story 1.5 receives the same immutable Technician snapshots plus the validated eligibility partition/result. It may use rating and other explicitly captured scoring inputs from those snapshots, but may not reload mutable Technician rows, reinterpret checks, score ineligible candidates, or override eligibility.

#### Eligibility input contract

`EligibilityInputV1` contains:

- `schema_version: "v1"`
- `configuration_version: "eligibility-v1"`
- `requirements`: `priority`, sorted canonical `required_certifications`, and `estimated_service_duration_minutes` from a validated Story 1.3 output
- `captured_at`: aware UTC datetime
- `technicians`: 0-100 snapshots sorted by ascending UUID

Each Technician snapshot contains:

| Field | Contract |
| --- | --- |
| `technician_id` | opaque UUID |
| `availability` | `available`, `busy`, `absent`, or `off_duty` |
| `certifications` | unique sorted Story 1.3 certification codes |
| `shift_start`, `shift_end` | aware UTC timestamps; start strictly before end |
| `assigned_work_minutes` | strict integer 0-1440 |
| `accumulated_driving_minutes` | strict integer 0-1440 or null |
| `has_required_epp` | strict boolean or null |
| `estimated_travel_minutes` | strict integer 0-1440 |
| `distance_meters` | strict integer 0-1,000,000 |

Exact GPS, address, names, ratings, Memory, free text, and display labels are not eligibility inputs.

#### Normative `eligibility-v1` registry

| Setting | Value |
| --- | --- |
| check order | availability, certifications, shift, maximum_workday, driving_limit, required_epp |
| maximum workday | 480 minutes; MVP assumption based on the eight-hour brownfield limit |
| accumulated driving maximum | 240 minutes |
| EPP priority threshold | priority 4 |
| availability enabled | true |
| certifications enabled | true |
| shift enabled | true |
| maximum workday enabled | true |
| driving limit enabled | true |
| required EPP enabled | true |
| limit comparison | equality passes; only greater-than fails |
| disabled/missing safety data | fail closed plus structured warning; `eligibility-v1` enables every check, while the pure policy retains and unit-tests this rule for future explicitly versioned configurations |

Environment variables cannot change this registry. A future configuration version may change it without rewriting old evidence.

#### Check results and stable reasons

Checks appear exactly once in registry order. Status is `pass` or `fail`.

| Check | Pass reasons | Fail reasons |
| --- | --- | --- |
| `availability` | `TECHNICIAN_AVAILABLE` | `TECHNICIAN_UNAVAILABLE`, `CHECK_DISABLED` |
| `certifications` | `ALL_CERTIFICATIONS_PRESENT`, `NO_CERTIFICATIONS_REQUIRED` | `CERTIFICATIONS_MISSING`, `CHECK_DISABLED` |
| `shift` | `WITHIN_SHIFT` | `OUTSIDE_SHIFT`, `SHIFT_END_EXCEEDED`, `CHECK_DISABLED` |
| `maximum_workday` | `WITHIN_MAXIMUM_WORKDAY` | `MAXIMUM_WORKDAY_EXCEEDED`, `CHECK_DISABLED` |
| `driving_limit` | `WITHIN_DRIVING_LIMIT` | `DRIVING_LIMIT_EXCEEDED`, `SOURCE_DATA_UNAVAILABLE`, `CHECK_DISABLED` |
| `required_epp` | `EPP_PRESENT`, `EPP_NOT_REQUIRED_FOR_PRIORITY` | `REQUIRED_EPP_MISSING`, `SOURCE_DATA_UNAVAILABLE`, `CHECK_DISABLED` |

`eligibility-v1` cannot be disabled at the persisted boundary. The pure policy accepts an explicit immutable configuration value so future versioned configurations cannot accidentally turn a disabled mandatory check into a pass; focused unit tests exercise that fail-closed branch. Missing data is accepted only for fields explicitly optional in the input contract and never becomes a pass when the check applies.

#### Structured check evidence

- Availability: observed canonical availability.
- Certifications: sorted `required`, `possessed`, and `missing`.
- Shift: `captured_at`, `shift_start`, `shift_end`, `travel_minutes`, `service_minutes`, and `projected_finish`.
- Maximum workday: `assigned_work_minutes`, `travel_minutes`, `service_minutes`, `projected_workday_minutes`, and `maximum_workday_minutes`.
- Driving: `enabled`, accumulated/travel/projected minutes, and maximum.
- EPP: `enabled`, `required_for_priority`, observed value, and threshold.
- No check evidence contains raw text, address, name, exact GPS, provider reasoning, or display labels.

#### Safety warnings

Only missing or disabled safety checks produce candidate warnings in this story:

- `ELIGIBILITY_SOURCE_DATA_UNAVAILABLE`
- `ELIGIBILITY_CHECK_DISABLED`

Each warning contains `code`, `severity: "warning"`, `technician_id`, `affected_check`, `source`, `quality`, `freshness: "not_applicable"`, `fallback: null`, `impact`, and `configuration_version`. Warning templates are immutable registry content. Warnings sort by `(technician_id, affected_check, code)`.

#### Persistence and replay

- One `eligibility_evaluation_sets` row stores the complete validated batch. Do not add durable Technician, candidate-score, Dispatch Run, transition, or fixture tables.
- Unique replay scope is `(work_order_analysis_id, configuration_version, input_hash)`.
- The output candidates and identifier partitions are canonical. Summary columns must equal validated JSON on read.
- A changed input hash creates a new immutable evaluation set; old sets are not overwritten.
- Configuration and analysis integrity are validated before replay or new calculation.
- Repositories use the caller-owned connection and never commit.

#### Legacy compatibility correction

In `evaluate_candidates()`, projected work above eight hours always sets `validation_status` to `rechazado` and appends the existing overtime alert shape. Priority 5 receives no exception. Do not route the legacy simulator through the new command yet; Story 1.10 owns that cutover.

### Architecture and Reuse Guardrails

- Reuse Story 1.3 canonical certification codes, strict contract patterns, canonical JSON, immutable/digested registry pattern, validated retained-result pattern, Unit of Work, configuration repository, and corruption defenses.
- Do not reuse legacy Spanish certification labels as canonical values.
- Keep domain modules free of Pydantic, SQLAlchemy, FastAPI, SQLite, mutable globals, I/O, clock reads, and network/Memory access.
- Do not implement distance penalty, score, ranking, confidence, recommendation, UI, public API, Dispatch Run, run snapshot, State Transition, stage timing, replay API, or fixture import.
- Do not modify Story 1.3 Analyze values or provenance.

### Expected File Impact

**New:**

- `app/domain/eligibility/{__init__,models,rules,policy}.py`
- `app/contracts/eligibility.py`
- `app/application/commands/determine_technician_eligibility.py`
- `app/adapters/persistence/eligibility.py`
- `app/migrations/versions/20260728_0004_eligibility_evaluation_sets.py`
- `tests/unit/test_{eligibility_contracts,eligibility_policy,determine_technician_eligibility}.py`
- `tests/integration/test_eligibility_persistence.py`
- `tests/contract/test_eligibility_policy_contract.py`

**Updated:**

- `app/application/ports/persistence.py`
- `app/adapters/persistence/schema.py`
- `app/adapters/persistence/unit_of_work.py`
- `app/adapters/legacy/compatibility.py`
- `tests/integration/test_legacy_compatibility.py`
- `tests/integration/test_migrations.py`
- both migration fixture heads
- `docs/development-guide.md`

Do not update `app/api/v1/*`, `app/main.py`, `frontend/*`, `server.py`, `data/learning_store.json`, or existing Story 1.3 contracts.

### Testing Requirements

- Follow red-green-refactor for every behavior and defect.
- Pure unit tests: each pass/fail reason; equality and one-minute-over limits; priority 5; full/subset/empty certifications; unavailable states; shift start/end; combined failures; missing/disabled safety data; >50 km; stable ordering; no feasible candidates; byte determinism.
- Contract tests: strict types, aware UTC, UUIDs, duplicate/unsorted roster/certifications, malformed check order, incomplete evidence, partition mismatch, warning mismatch, forbidden extra score/rank/recommendation/Memory/state fields.
- Application tests: missing/corrupt analysis/configuration, invalid policy output, policy exception, identical replay, changed input, sanitized persistence failure.
- Integration: real temporary SQLite, incremental `0003 -> 0004`, exact schema allowlist/columns/checks/FKs, canonical round-trip, configuration digest, uniqueness, changed-input append, corruption, rollback, source evidence unchanged.
- Legacy regression: direct priority-5 overtime branch and `/api/dispatch/simulate` preservation.
- No browser, external network, provider, scoring, confidence, orchestrator, or performance benchmark tests belong to this story.

### Latest Technical Information

- Keep the pinned project versions; do not upgrade opportunistically.
- Pydantic v2 strict models, discriminated unions, and model validators support exact boundary and cross-field invariants. [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [Pydantic unions](https://docs.pydantic.dev/latest/concepts/unions/), and [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/).
- SQLAlchemy Core exposes explicit `CheckConstraint`, `ForeignKeyConstraint`, and `UniqueConstraint` primitives; continue using caller-owned transaction boundaries. [SQLAlchemy constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html) and [Core transactions](https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html).
- SQLite foreign keys and JSON validity checks remain the storage guardrails, while Pydantic/repository validation owns cross-JSON invariants. [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html) and [SQLite JSON functions](https://www.sqlite.org/json1.html).

### Project Structure Notes

- No Git metadata is available; preserve `baseline_commit: NO_VCS`.
- Story 1.3 is done after nine review patches and 117 passing tests.
- The Architecture Spine and completed Story 1.3 supersede older descriptions that validate after scoring, use Spanish labels as canonical skills, or permit priority-5 overtime.
- No UX work is required because eligibility remains an internal capability.
- `data/learning_store.json` must retain SHA-256 `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.4]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — UJ-1, FR6-FR9, NFR2, NFR7, SM-1, SM-C2]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/addendum.md` — Brownfield Baseline and stricter overtime rule]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-1, AD-3-AD-7, AD-10, AD-11, AD-13, AD-15, AD-16, AD-18, AD-23, AD-26, AD-27]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — §§5-8, 10, 13-14, 17-18]
- [Source: `_bmad-output/project-context.md` — project-wide implementation and testing rules]
- [Source: `_bmad-output/implementation-artifacts/1-3-derive-dispatch-requirements-with-provenance.md` — completed capability, review learnings, persistence seams]
- [Source: `spec/02_business_rules.md` — original business rules and limits]
- [Source: `app/adapters/legacy/compatibility.py` — Technician evidence and owned priority-5 defect]
- [Source: `app/domain/analysis/*`, `app/contracts/stages/analyze.py`, `app/application/commands/analyze_work_order.py`, `app/adapters/persistence/*` — current implementation seams]

## Definition of Done

- [ ] All tasks/subtasks and acceptance criteria are complete with tests passing.
- [ ] Every Technician has all six Hard Constraint results; only all-pass candidates are eligible.
- [ ] Missing or disabled safety evidence fails closed and remains visible.
- [ ] Distance, priority, and Memory cannot weaken eligibility.
- [ ] Eligibility input/output/configuration and persisted evidence are strict, immutable, canonical, and reproducible.
- [ ] Invalid output, corruption, or persistence failure cannot leave partial evidence or mutate source Work Order/analysis.
- [ ] The priority-5 legacy branch rejects overtime without raising.
- [ ] No scoring, confidence, recommendation, public API, browser, Dispatch Run, State Transition, or LLM scope leaked into the story.
- [ ] Full regression, lock, compile, migration, import-safety, and evidence-integrity checks pass.
- [ ] Dev Agent Record lists exact commands/results and every changed file.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Implementation Plan

- Test-first pure eligibility domain and strict boundary contracts.
- Atomic, append-only SQLite evidence through the existing Unit of Work.
- Isolated brownfield priority-5 regression correction.
- Full regression, migration, launch, lock, compile, and evidence-integrity verification.

### Debug Log References

- RED: eligibility tests initially failed at collection because the new domain and contract modules did not exist.
- RED: persistence tests initially failed because the application command did not exist.
- Full-suite sandbox run exposed only the expected local socket restriction; both process tests passed with local-loopback permission.

### Completion Notes List

- Implemented all six pre-scoring Hard Constraints with complete evidence and no short-circuiting.
- Added strict canonical eligibility input/output validation, empty-roster behavior, deterministic ordering, and fail-closed warnings.
- Added immutable `eligibility-v1` registry/digest and append-only replay-safe SQLite evidence.
- Corrected the legacy priority-5 overtime branch without changing its response shape.
- Verification: 172 tests pass (170 sandbox-safe plus 2 loopback process tests), compile passes, offline lock check resolves 28 packages, and learning evidence SHA-256 remains `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.
- Resolved all 14 code-review patches: semantic evidence, exact input/output binding, replay corruption defenses, complete registry semantics, source hash verification, canonical warning/UTC handling, safe dependencies/overflow, composite relational integrity, and expanded boundary/migration tests.

### File List

- app/adapters/legacy/compatibility.py
- app/adapters/persistence/analyses.py
- app/adapters/persistence/eligibility.py
- app/adapters/persistence/schema.py
- app/adapters/persistence/unit_of_work.py
- app/application/commands/determine_technician_eligibility.py
- app/application/ports/persistence.py
- app/contracts/eligibility.py
- app/domain/eligibility/__init__.py
- app/domain/eligibility/models.py
- app/domain/eligibility/policy.py
- app/domain/eligibility/rules.py
- app/migrations/versions/20260728_0004_eligibility_evaluation_sets.py
- docs/development-guide.md
- tests/contract/test_eligibility_policy_contract.py
- tests/fixtures/migrations/failure/20260728_0002_review_failure.py
- tests/fixtures/migrations/success/20260728_0002_review_success.py
- tests/integration/test_eligibility_persistence.py
- tests/integration/test_legacy_eligibility_regression.py
- tests/integration/test_migrations.py
- tests/unit/test_determine_technician_eligibility.py
- tests/unit/test_eligibility_contracts.py
- tests/unit/test_eligibility_policy.py
- _bmad-output/implementation-artifacts/1-4-determine-technician-eligibility-before-scoring.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

### Change Log

- 2026-07-28: Created and validated the implementation-ready Story 1.4 context.
- 2026-07-28: Implemented deterministic pre-scoring eligibility, immutable evidence, and the priority-5 compatibility correction; moved story to review.
- 2026-07-28: Addressed all 14 code-review findings, raised verification to 172 passing tests, and completed Story 1.4.

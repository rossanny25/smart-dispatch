---
baseline_commit: NO_VCS
---

# Story 1.3: Derive Dispatch Requirements with Provenance

Status: done

## Story

As a dispatcher,
I want the incident to be converted into explicit dispatch requirements,
so that I can understand which operational facts will govern the recommendation.

## Requirements Traceability

- **Functional:** FR5.
- **Non-functional:** NFR2, NFR4, NFR7.
- **Journey:** UJ-1, limited to deterministic analysis of a captured Work Order.
- **Architecture:** AD-1, AD-5, AD-7, AD-10, AD-11, AD-12, AD-13, AD-15, AD-16, AD-18, AD-26, and AD-27.
- **Epic requirements registry:** AR7, AR11, AR12, and AR16.
- **Downstream:** Story 1.4 consumes the analyzed requirements; Story 1.7 owns Dispatch Runs, snapshots, stage execution records, and State Transitions.

## Acceptance Criteria

1. **Deterministic Analyze result**
   - **Given** a valid Work Order persisted by Story 1.2
   - **When** `AnalyzeWorkOrder` invokes the local deterministic Analyze stage with analysis configuration `analysis-v1`
   - **Then** it produces `category`, `priority`, `sla_target_minutes`, `required_certifications`, and `estimated_service_duration_minutes`
   - **And** the complete output validates against `AnalyzeOutputV1` before any analysis row is persisted
   - **And** the Work Order row remains byte-for-byte unchanged.

2. **Strict, self-contained versioned stage contracts**
   - **Given** Analyze input or output crosses the stage boundary
   - **When** Pydantic validates `AnalyzeInputV1` or `AnalyzeOutputV1`
   - **Then** strict types are enforced and unknown fields are forbidden
   - **And** the input contains the complete immutable semantic Work Order data required by the stage rather than a repository handle
   - **And** output contract version and analysis configuration version are independently recorded
   - **And** a proposed output with any missing field, invalid enum/range, malformed provenance, inconsistent warning, duplicate certification, or unknown field is rejected as `InvalidAnalyzeOutput`
   - **And** no invalid output is persisted.

3. **Explicit supplied values and precedence**
   - **Given** `context.dispatch_requirements` contains a valid explicit value for one or more supported fields
   - **When** analysis applies precedence
   - **Then** valid supplied values take precedence over inference and defaults
   - **And** each such field records provenance kind `supplied`
   - **And** `source_field` is the JSON Pointer `/context/dispatch_requirements/<field>`
   - **And** evidence never copies the supplied value, incident narrative, address, or other sensitive raw text.

4. **Configured deterministic inference**
   - **Given** a field is not explicitly supplied and one unambiguous `analysis-v1` rule applies
   - **When** analysis derives the field
   - **Then** provenance kind is `inferred`
   - **And** evidence contains the stable `rule_id` and `configuration_version: "analysis-v1"`
   - **And** matching uses Unicode NFKD normalization, combining-mark removal, and `casefold()` only for comparison without altering stored raw input.

5. **Defaults and structured warnings**
   - **Given** a required field is neither supplied nor unambiguously inferred
   - **When** the configured fallback is safe to apply
   - **Then** provenance kind is `defaulted`
   - **And** the result includes one stable Data Quality Warning for that field
   - **And** the warning records `code`, `severity`, `affected_field`, `source`, `quality`, `freshness`, `fallback`, and `impact`
   - **And** `fallback` is a non-sensitive canonical value, `freshness` is `not_applicable`, and `quality` is `defaulted`.

6. **Ambiguous, unsupported, and contradictory input**
   - **Given** incident rules match more than one category with equal precedence
   - **When** no valid supplied category resolves the conflict
   - **Then** category uses the configured default with `ANALYZE_AMBIGUOUS_CATEGORY`
   - **And** dependent certifications and duration also use their configured defaults rather than mixing incompatible rule outputs.
   - **Given** no category rule matches
   - **When** the incident is unsupported
   - **Then** category uses the configured default with `ANALYZE_UNSUPPORTED_INCIDENT`.
   - **Given** a supplied value contradicts inferred incident evidence but is contract-valid
   - **When** supplied precedence is applied
   - **Then** the supplied value remains authoritative for Analyze
   - **And** `ANALYZE_SUPPLIED_CONFLICT` identifies only the affected field, source pointer, and applicable rule identifiers.
   - **Given** a supplied value is contract-invalid
   - **When** Analyze input validation runs
   - **Then** analysis fails with `InvalidAnalyzeInput` rather than silently ignoring or replacing the value.

7. **Normative `analysis-v1` registry**
   - **Given** the MVP deterministic adapter is used
   - **When** it classifies an incident
   - **Then** it uses only the immutable registry in the Binding Contract Decisions section
   - **And** category codes, certification codes, rule precedence, SLA values, duration values, defaults, and warning codes are not changeable through environment variables or mutable globals
   - **And** the registry is serialized canonically and persisted as an immutable configuration row with its SHA-256 digest.

8. **Deterministic ordering and byte equivalence**
   - **Given** identical semantic Work Order data and `analysis-v1`
   - **When** Analyze runs repeatedly
   - **Then** its domain output contains no generated UUID, clock value, database value, network result, or mutable global state
   - **And** certifications are deduplicated and sorted by canonical code, provenance entries follow the five required field order, and warnings sort by `(affected_field, code, source)`
   - **And** UTF-8 canonical JSON with sorted object keys, compact separators, explicit nulls, and no non-finite numbers is byte-equivalent across executions.

9. **Atomic persistence, replay, and corruption safety**
   - **Given** a Work Order and configuration have already been analyzed successfully
   - **When** the same command is retried
   - **Then** the retained validated result is returned without inserting a duplicate
   - **And** the database enforces one result per `(work_order_id, configuration_version)`.
   - **Given** Work Order retrieval, configuration retrieval, output validation, analysis insertion, or commit fails
   - **When** the Unit of Work exits
   - **Then** all writes from the command roll back
   - **And** no partial analysis is available
   - **And** the Work Order remains unchanged
   - **And** corruption or adapter failures become sanitized typed application errors.

10. **Minimal Story 1.3 persistence**
    - **Given** the production migration reaches head
    - **When** schema objects are inspected
    - **Then** this story adds only `configuration_versions` and `work_order_analyses`
    - **And** `configuration_versions` stores immutable version, contract version, canonical registry JSON, digest, and UTC creation time
    - **And** `work_order_analyses` stores UUID identity, Work Order foreign key, contract/configuration versions, input hash, canonical validated output JSON, queryable required fields, and UTC creation time
    - **And** foreign keys, non-null checks, value checks, unique replay key, and configuration linkage are enforced
    - **And** no Technician, candidate, score, confidence, Dispatch Run, snapshot, transition, stage execution, Decision, outcome, Memory, KPI, replay, reset, or fixture table is introduced.

11. **Optional future LLM boundary without an LLM dependency**
    - **Given** a future LLM Analyze adapter is introduced
    - **When** it proposes an output
    - **Then** it implements the same `AnalyzeStage` port and passes `AnalyzeOutputV1` before persistence
    - **And** `adapter_metadata` records adapter kind, provider, and model when applicable
    - **And** validation and `analysis-v1` safety semantics remain authoritative
    - **And** this story adds no provider SDK, prompt, credential, network call, or external-service test.

12. **Boundary-aligned evidence and regression safety**
    - **Given** unit, contract, integration, migration, and regression tests run
    - **When** supplied, inferred, defaulted, ambiguous, unsupported, conflicting, invalid-input, invalid-output, replay, corruption, and rollback cases are exercised
    - **Then** every required field has valid provenance or the command fails before persistence
    - **And** the domain result is canonically byte-equivalent on repeat
    - **And** the 74 tests completed after Story 1.2 remain green
    - **And** the legacy API, SPA, import safety, launch contract, database PRAGMAs, backup/fail-closed migrations, and `data/learning_store.json` checksum remain unchanged.

## Tasks / Subtasks

- [x] 1. Establish red tests for the Analyze kernel and its boundaries (AC: 1-8, 11, 12)
  - [x] Add pure tests for every supplied field, each inference rule, every default, Unicode/case normalization, conflicts, ambiguity, unsupported incidents, stable ordering, and canonical byte equivalence.
  - [x] Add strict Pydantic contract tests for input/output, provenance variants, warnings, ranges, duplicates, and forbidden extras.
  - [x] Add application tests for missing Work Order, invalid stage output, existing-result replay, and sanitized persistence failure.

- [x] 2. Define pure analysis domain types and the immutable registry (AC: 1-8)
  - [x] Add frozen domain value objects/enums for category, certification, requirements, provenance, warning, adapter metadata, and result.
  - [x] Add `analysis-v1` as immutable data in code, including its canonical serialization and digest.
  - [x] Keep the domain free of FastAPI, Pydantic, SQLAlchemy, SQLite, clocks, UUID generation, and network access.

- [x] 3. Implement strict Analyze contracts and adapter port (AC: 1-6, 8, 11)
  - [x] Add `AnalyzeInputV1` and `AnalyzeOutputV1` with `extra="forbid"` and strict validation.
  - [x] Use discriminated provenance models so supplied, inferred, and defaulted evidence cannot be malformed.
  - [x] Define `AnalyzeStage` as a self-contained application port and an output-validation seam usable by both the local adapter and a future optional LLM adapter.

- [x] 4. Implement the deterministic local Analyze adapter (AC: 1, 3-8)
  - [x] Apply supplied → inferred → defaulted precedence independently, with category ambiguity controlling dependent category outputs.
  - [x] Generate structured warnings and evidence references only; never generate reasoning prose or chain-of-thought.
  - [x] Canonicalize collections and prove the adapter performs no I/O.

- [x] 5. Add minimal configuration and analysis persistence (AC: 7-10)
  - [x] Add one linear Alembic revision after `20260728_0002` for exactly the two Story 1.3 tables.
  - [x] Seed immutable `analysis-v1` configuration deterministically during migration or command initialization without import-time database I/O.
  - [x] Add SQLAlchemy Core table metadata and caller-owned-connection repositories with typed reconstruction/corruption failures.
  - [x] Rebase both migration review fixtures to the new production head and test a real incremental upgrade from Story 1.2.

- [x] 6. Implement `AnalyzeWorkOrder` through the existing Unit of Work (AC: 1, 2, 7-10)
  - [x] Load the Work Order and configuration, build a self-contained input, invoke the stage, validate its output, and insert only after validation.
  - [x] Return a retained validated result for `(work_order_id, configuration_version)` retries.
  - [x] Preserve one transaction, repository non-commit behavior, Work Order immutability, and sanitized typed failures.

- [x] 7. Complete real-SQLite and contract evidence (AC: 2, 7-10, 12)
  - [x] Prove foreign keys, uniqueness, canonical round-trip, config digest, retrieval validation, corruption translation, rollback, and unchanged Work Order.
  - [x] Prove the migration against fresh and Story 1.2 databases, exact schema allowlist, one fixture head, and startup backup/fail-closed behavior.
  - [x] Keep Analyze internal: no standalone HTTP endpoint, OpenAPI operation, idempotency row, browser change, or orchestrator stub.

- [x] 8. Preserve brownfield behavior and document the capability (AC: 11, 12)
  - [x] Update the development guide with the internal Analyze contract, registry, provenance, warnings, and later Story 1.7 integration seam.
  - [x] Run compile, lock, complete regression, legacy/process, checksum, and import-safety checks.

### Review Findings

- [x] [Review][Patch] Deep-freeze the normative registry and include every priority and conditional-certification rule in its canonical digest [app/domain/analysis/rules.py:9]
- [x] [Review][Patch] Reject explicitly null supplied fields instead of treating them as omitted [app/contracts/stages/analyze.py:34]
- [x] [Review][Patch] Let a valid supplied category resolve matching-category ambiguity and retain unambiguous critical-priority inference [app/adapters/stages/deterministic_analyze.py:117]
- [x] [Review][Patch] Remove supplied values from conflict warnings and record canonical applicable rule identifiers [app/adapters/stages/deterministic_analyze.py:174]
- [x] [Review][Patch] Reject invented provenance, inconsistent or sensitive warning metadata, and duplicate warnings at the output contract [app/contracts/stages/analyze.py:104]
- [x] [Review][Patch] Validate configuration integrity and recompute the current input hash before returning a retained analysis [app/application/commands/analyze_work_order.py:82]
- [x] [Review][Patch] Reconcile retained canonical output with every queryable analysis column before replay [app/adapters/persistence/analyses.py:84]
- [x] [Review][Patch] Translate non-validation stage exceptions into a sanitized typed Analyze failure [app/application/commands/analyze_work_order.py:136]
- [x] [Review][Patch] Add SQLite checks for contract/config versions, category vocabulary, hash shape, and JSON validity [app/adapters/persistence/schema.py:61]

## Dev Notes

### Binding Contract Decisions

#### Capability boundary

- `AnalyzeWorkOrder` is an internal application command; Story 1.3 adds no public Analyze endpoint.
- `AnalyzeStage` accepts a self-contained immutable input and returns a semantic output. It never queries repositories or advances state.
- `work_order_analyses` is reusable derived evidence, not a `StageExecution`. Story 1.7 will invoke the same capability from an immutable run snapshot and owns `CAPTURE -> ANALYZE`, retries, timestamps, stage attempts, and snapshot references.
- Same Work Order/configuration retries return the existing valid analysis. A new registry requires a new configuration version; existing evidence is never overwritten.

#### Recognized supplied context

Only these keys under `context.dispatch_requirements` are authoritative supplied values:

| JSON key | Type and validation |
| --- | --- |
| `category` | one canonical category code |
| `priority` | strict integer 1-5; booleans rejected |
| `sla_target_minutes` | strict integer 1-10080 |
| `required_certifications` | list of unique canonical certification codes; maximum 16; empty allowed |
| `estimated_service_duration_minutes` | strict integer 15-1440 |

Unknown keys inside `dispatch_requirements` are forbidden. Other `context` keys remain preserved but uninterpreted. A missing `context`, missing `dispatch_requirements`, or missing individual key is not an error.

#### Canonical vocabularies

Category codes are:

`gas`, `electricity`, `telecommunications`, `plumbing`, `hvac`, `maintenance`.

Certification codes and Spanish display labels are:

| Code | Display label |
| --- | --- |
| `gas_registered` | `Gasista Matriculado` |
| `electrician_category_a` | `Técnico Electricista Categoría A` |
| `wan_networks` | `Redes WAN` |
| `fiber_optics` | `Fibra Óptica` |
| `working_at_height` | `Seguridad en Alturas` |
| `licensed_plumber` | `Plomero Matriculado` |
| `high_pressure_refrigerants` | `Refrigerantes de Alta Presión` |

Codes, not display labels, are authoritative for future eligibility. This resolves the brownfield mismatch between `Técnico Electricista A` and `Técnico Electricista Categoría A`.

#### Priority and SLA registry

Priority is an integer where 1 is scheduled maintenance and 5 is critical emergency. `sla_target_minutes` is the positive response-duration budget consumed later by scoring:

| Priority | SLA minutes | Meaning |
| --- | ---: | --- |
| 5 | 60 | critical/emergency |
| 4 | 240 | high |
| 3 | 720 | medium |
| 2 | 2880 | low/planned installation |
| 1 | 10080 | scheduled maintenance; MVP assumption of seven days |

If priority is supplied but SLA is not, SLA is inferred by `priority_sla_v1`. If both are supplied, both remain supplied even when nonstandard; `ANALYZE_SUPPLIED_CONFLICT` reports the mismatch without rewriting either value.

#### Category rule registry

Matching is token/phrase based after comparison-only normalization. A category matches when any of its configured phrases occurs. Category precedence is not used to conceal cross-category conflicts: two or more matched categories are ambiguous unless supplied category resolves the field.

| Rule ID | Category | Match phrases | Inferred priority | Certifications | Duration minutes |
| --- | --- | --- | ---: | --- | ---: |
| `category_gas_v1` | `gas` | `gas`, `fuga`, `caldera` | 5 for `fuga`; otherwise 4 | `gas_registered` | 90 |
| `category_electricity_v1` | `electricity` | `luz`, `electricidad`, `electrico`, `termica`, `tension`, `cortocircuito` | 5 for `fuego` or `cortocircuito`; 4 for `corte` or `urgente`; otherwise 3 | `electrician_category_a` | 120 |
| `category_telecommunications_v1` | `telecommunications` | `internet`, `enlace`, `fibra`, `red`, `servidor` | 5 for `servidor critico`; 4 for `urgente`, `sin servicio`, or `no conecta`; otherwise 3 | `wan_networks`; plus `fiber_optics` and `working_at_height` when `fibra` or `altura` occurs | 60 |
| `category_plumbing_v1` | `plumbing` | `agua`, `cano`, `inundacion`, `bano`, `plomeria` | 5 for `inundacion` with `riesgo`; otherwise 4 | `licensed_plumber` | 90 |
| `category_hvac_v1` | `hvac` | `aire acondicionado`, `frio`, `hvac`, `climatizacion` | 3 | `high_pressure_refrigerants` | 120 |
| `category_maintenance_v1` | `maintenance` | `mantenimiento`, `inspeccion`, `preventivo`, `rutina` | 1 | none | 60 |

Keyword matching must respect normalized word/phrase boundaries so `red` does not match unrelated substrings. Multiple phrases in the same category are not ambiguous.

#### Defaults and dependent inference

| Field | Default | Warning impact |
| --- | --- | --- |
| `category` | `maintenance` | May under-specify the service specialty; dispatcher review required |
| `priority` | 3 | Medium urgency assumed; dispatcher must verify operational impact |
| `sla_target_minutes` | 720 | Twelve-hour response budget assumed |
| `required_certifications` | empty list | No specialty certification inferred; eligibility may be broader than intended |
| `estimated_service_duration_minutes` | 60 | One-hour service duration assumed; schedule feasibility may change after review |

- A single unambiguous category rule supplies the category-dependent priority, certifications, and duration when those fields are absent.
- SLA is inferred from the final priority, regardless of whether priority was supplied or inferred.
- An ambiguous or unsupported category defaults category, certifications, and duration independently and generates field-specific warnings. Priority may still be inferred only from unambiguous critical phrases; otherwise it defaults. SLA follows the resulting priority.
- Safety-critical supplied values are accepted only when contract-valid and receive conflict warnings where applicable. Invalid supplied values fail closed; they are never replaced silently.

#### Provenance and warning shapes

- `supplied`: `{kind, source_field}`.
- `inferred`: `{kind, rule_id, configuration_version}`.
- `defaulted`: `{kind, rule_id: "default_<field>_v1", configuration_version}`.
- One provenance record exists for each of the five output fields.
- Warning severity is `warning`; future levels may be versioned but are not accepted by v1.
- Stable codes: `ANALYZE_DEFAULT_APPLIED`, `ANALYZE_AMBIGUOUS_CATEGORY`, `ANALYZE_UNSUPPORTED_INCIDENT`, and `ANALYZE_SUPPLIED_CONFLICT`.
- `source` contains a JSON Pointer or rule ID, never a raw value.
- `fallback` is a canonical scalar/list or null; `impact` is a fixed registry template, never generated reasoning.

### Architecture and Reuse Guardrails

- Reuse `WorkOrderRepository.get()`, the caller-owned connection, `SqliteUnitOfWork`, strict common contracts, injected factories, and canonical JSON behavior from Story 1.2.
- Extract canonical JSON/hash behavior to a neutral pure helper only with regression tests; do not duplicate incompatible serializers.
- Domain modules import no framework or adapter package.
- Repositories never commit. The command owns atomic coordination through one Unit of Work.
- Do not call or modify legacy `classify_order()`. It is characterization evidence, not the canonical registry.
- Do not create or modify Dispatch Run, State Machine, StageExecution, snapshot, Technician, eligibility, scoring, confidence, recommendation, Human Decision, outcome, Memory, KPI, replay, reset, or browser behavior.
- Do not add an LLM SDK or dependency.
- No raw incident, address, arbitrary context values, exact coordinates, or private reasoning may appear in warnings or logs.

### Expected File Impact

**New:**

- `app/domain/analysis/{__init__,models,rules}.py`
- `app/contracts/stages/{__init__,analyze}.py`
- `app/application/ports/stages.py`
- `app/adapters/stages/{__init__,deterministic_analyze}.py`
- `app/application/commands/analyze_work_order.py`
- `app/adapters/persistence/analyses.py`
- `app/migrations/versions/20260728_0003_work_order_analysis.py`
- `tests/unit/test_{analyze_contracts,deterministic_analyze,analyze_work_order}.py`
- `tests/integration/test_analysis_persistence.py`
- `tests/contract/test_analyze_stage_contract.py`

**Updated:**

- `app/adapters/persistence/schema.py`
- `app/adapters/persistence/unit_of_work.py`
- `app/application/ports/persistence.py`
- `tests/integration/test_migrations.py`
- both migration fixture heads
- `docs/development-guide.md`

Do not update `app/api/v1/*`, `app/main.py`, `frontend/*`, the legacy adapter, `server.py`, or seeded learning evidence for this internal capability.

### Testing Requirements

- Follow red-green-refactor.
- Unit: all registry branches and fields; valid/invalid supplied values; precedence; conflicts; ambiguity; unsupported; NFKD/casefold; word boundaries; duplicate/sorted certifications; deterministic warning order; no I/O; canonical byte equality.
- Contract: strict input/output; forbidden fields; ranges; discriminated provenance; complete warning fields; invalid adapter outputs.
- Application: missing Work Order; invalid output before write; replay; command errors; no generated metadata inside semantic output.
- Integration: real temporary SQLite; configuration seeding/digest; foreign keys; exact round-trip; corruption translation; unique replay; rollback; unchanged Work Order.
- Migration: fresh database and real incremental `0002 -> 0003`; exact object allowlist; fixture single-head; backup-before-change and fail-closed behavior.
- Regression: complete prior suite, legacy routes, real launch where sandbox permits, import safety, PRAGMAs, lock, compile, and evidence checksum.
- No browser, orchestrator, external-network, or provider tests belong to this story.

### Latest Technical Information

- Keep all versions pinned in `uv.lock`; do not upgrade opportunistically.
- Pydantic v2 supports strict models, forbidden extras, discriminated unions, and model-level validators for cross-field invariants. [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) and [Pydantic unions](https://docs.pydantic.dev/latest/concepts/unions/).
- SQLAlchemy Core transaction contexts commit only on success and roll back on exceptions; all repositories in one command must share the caller-owned connection. [SQLAlchemy Core transactions](https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html).
- SQLite foreign keys must remain enabled per connection, as already enforced by the project runtime. [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html).

### Project Structure Notes

- No Git metadata is available; use `baseline_commit: NO_VCS`.
- Story 1.2 completed with 74 passing tests. Two real-process tests may require an environment that permits loopback binding; distinguish sandbox denial from product failure.
- No separate UX specification exists, and none is required because Story 1.3 has no browser surface.
- `data/learning_store.json` must retain SHA-256 `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.3]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — UJ-1, FR5, NFR2, NFR4, NFR7]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/addendum.md` — JSON Contracts, SQLite, deterministic baseline]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-1, AD-5, AD-7, AD-10–AD-13, AD-15, AD-16, AD-18, AD-26, AD-27]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — §§5, 6, 8, 10, 13, 14, 18]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/reconcile-prd.md` — G-3]
- [Source: `_bmad-output/project-context.md` — project-wide implementation rules]
- [Source: `_bmad-output/implementation-artifacts/1-2-capture-and-validate-a-work-order.md` — completion notes, review findings, reusable seams]
- [Source: `spec/02_business_rules.md`, `spec/04_agents.md`, `spec/07_data_model.md` — brownfield terminology and candidate rules]
- [Source: `app/application/commands/create_work_order.py`, `app/application/ports/persistence.py`, `app/adapters/persistence/*` — current implementation seams]

## Definition of Done

- [x] All tasks and subtasks are complete with tests passing.
- [x] Every analyzed field has valid supplied, inferred, or defaulted provenance.
- [x] The `analysis-v1` registry, contracts, warnings, and persistence are deterministic and reproducible.
- [x] Invalid output and persistence failures cannot leave partial analysis or mutate the Work Order.
- [x] No public API, orchestrator, Dispatch Run, eligibility, score, confidence, browser, or LLM scope has leaked into this story.
- [x] Full regression, lock, compile, migration, import-safety, and evidence-integrity checks pass.
- [x] Dev Agent Record lists exact commands/results and every created or modified file.

## Dev Agent Record

### Agent Model Used

GPT-5.6

### Implementation Plan

- Establish failing Analyze tests first, then implement the pure registry and strict stage contracts.
- Add the deterministic adapter and internal application command without introducing an HTTP or orchestration surface.
- Extend the existing Unit of Work with the minimal two-table SQLite evidence model.
- Finish with contract, real-SQLite, migration, process, compile, lock, and checksum verification.

### Debug Log References

- Initial focused pytest red phase — four collection errors confirmed the Analyze modules did not exist.
- Focused green phase — 34 Analyze/contract/application/SQLite/migration tests passed.
- Initial full regression outside the loopback-restricted sandbox — 103 tests passed, including both real-process launchers.
- Post-review full regression — 117 tests passed after all nine adversarial review patches.
- `.venv/bin/python -m compileall -q app tests` — passed.
- `uv lock --check --offline` with isolated cache — 28 packages resolved; lock is current.
- `data/learning_store.json` retained SHA-256 `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.

### Completion Notes List

- Implemented the immutable `analysis-v1` registry, canonical category/certification codes, priority/SLA mapping, deterministic rule matching, defaults, conflicts, ambiguity, and structured warnings.
- Added strict self-contained Analyze input/output contracts with discriminated provenance and cross-field evidence validation.
- Added the reusable local Analyze adapter and internal `AnalyzeWorkOrder` command; no network, LLM, public endpoint, Dispatch Run, or State Transition was introduced.
- Added immutable configuration and validated analysis persistence through the existing caller-owned Unit of Work, including replay, digest checks, foreign keys, rollback, and corruption translation.
- Preserved the captured Work Order, legacy API/SPA, process launch, migrations, import safety, database behavior, and historical learning evidence.
- Resolved all nine review findings: deep registry immutability and complete digest coverage, explicit-null rejection, ambiguity/critical-priority handling, privacy-safe conflict evidence, semantic output validation, replay integrity, cross-column corruption detection, typed stage failures, and stronger SQLite checks.

### File List

- `_bmad-output/implementation-artifacts/1-3-derive-dispatch-requirements-with-provenance.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `app/adapters/persistence/analyses.py`
- `app/adapters/persistence/schema.py`
- `app/adapters/persistence/unit_of_work.py`
- `app/adapters/stages/__init__.py`
- `app/adapters/stages/deterministic_analyze.py`
- `app/application/commands/analyze_work_order.py`
- `app/application/ports/persistence.py`
- `app/application/ports/stages.py`
- `app/contracts/stages/__init__.py`
- `app/contracts/stages/analyze.py`
- `app/domain/analysis/__init__.py`
- `app/domain/analysis/models.py`
- `app/domain/analysis/rules.py`
- `app/migrations/versions/20260728_0003_work_order_analysis.py`
- `docs/development-guide.md`
- `tests/fixtures/migrations/failure/20260728_0002_review_failure.py`
- `tests/fixtures/migrations/success/20260728_0002_review_success.py`
- `tests/integration/test_analysis_persistence.py`
- `tests/integration/test_migrations.py`
- `tests/unit/test_analyze_contracts.py`
- `tests/unit/test_analyze_work_order.py`
- `tests/unit/test_deterministic_analyze.py`

### Change Log

- 2026-07-28: Created and validated the implementation-ready Story 1.3 context.
- 2026-07-28: Implemented and verified the complete deterministic Analyze slice; moved Story 1.3 to review.
- 2026-07-28: Applied all nine adversarial code-review patches, expanded the regression suite to 117 passing tests, and marked Story 1.3 done.

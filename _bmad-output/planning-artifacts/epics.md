---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md
  - _bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/addendum.md
  - _bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md
---

# Smart Dispatch IA v2.1 - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Smart Dispatch IA v2.1, decomposing the requirements from the final PRD, its technical addendum, and the Architecture Spine into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Execute every Dispatch Run through the explicit, persisted State Machine, accepting only configured transitions, validating versioned stage contracts before transition, and starting learning only after the Human Decision and required outcome data exist.

FR2: Record every Agent Stage's start, end, duration, status, schema version, input/output snapshot references, and typed error as a chronological, retrievable evidence log without exposing private chain-of-thought.

FR3: Represent invalid input, invalid stage output, stage failure, and no feasible candidates as explicit typed outcomes, preserving completed evidence and never fabricating a recommendation.

FR4: Allow the dispatcher to create and validate a Work Order from incident text, address, zone, and available context while preserving raw input, structured-output schema version, and field-level validation errors.

FR5: Derive category, priority, SLA target, required certifications, and estimated service duration, recording whether each value was supplied, inferred, or defaulted and warning on ambiguity.

FR6: Reject unavailable Technicians before scoring and record the failed availability check.

FR7: Require every certification requested by the Work Order before a Technician can be scored; neither Memory nor priority may restore eligibility.

FR8: Reject Technicians outside their shift or whose travel plus service would exceed the configured maximum workday, using the immutable run time snapshot and without an implicit emergency exception.

FR9: Apply configured driving-hour and required-equipment safety checks, recording a result for each enabled rule and a visible warning when a check is disabled or unavailable.

FR10: Calculate SLA, proximity, workload balance, quality, and Memory scoring components on a 0–100 scale for eligible candidates only, exposing raw input, normalized value, weight, and contribution deterministically.

FR11: Apply the versioned default objective function `0.35 × SLA + 0.25 × proximity + 0.20 × workload_balance + 0.10 × quality + 0.10 × memory − penalties`, with weights totaling 1.00 and the final score clamped to 0–100.

FR12: Return every evaluated Technician with eligibility, score where applicable, component breakdown, warnings, and discard reasons; rank eligible candidates deterministically using score, SLA, quality, travel time, and Technician identifier as successive tie-breaks.

FR13: Calculate Recommendation Confidence independently of Objective Score from data quality, historical evidence, score margin, and condition certainty, exposing factor contributions and the configured low/medium/high label.

FR14: Produce structured Data Quality Warnings for missing, stale, estimated, or unavailable GPS, traffic, weather, and historical evidence, including freshness, fallback, and recommendation impact.

FR15: Allow the dispatcher to accept the recommendation, override it with another eligible Technician while supplying a reason, or decline assignment, preserving the alternatives and evidence visible at decision time.

FR16: Append immutable Episodic Memory for the selected Technician, prediction, actual duration, completion status, optional First-Time Fix result, feedback, decision, alternatives, and decision-time evidence.

FR17: Aggregate consistent episodes, penalize contradictions, apply age decay, and activate Semantic Patterns only after the configured evidence and confidence thresholds, while never affecting Hard Constraints.

FR18: Reproducibly compute time to assignment, SLA compliance, manual reassignment rate, estimated-time MAE, workload balance, recommendation acceptance, total/stage latency, and First-Time Fix Rate, including each KPI's numerator, denominator, exclusions, window, unit, and unavailable state.

FR19: Run or replay identical Scenario Fixtures with Memory enabled and disabled, differing only in Semantic Pattern reads, and show changes in ranks, contributions, recommendation, confidence, and KPI inputs while preserving identical Hard Constraint results and Episodic Memory writes.

FR20: Expose a versioned local simulation and replay API that returns the Dispatch Run, eligibility results, scoring breakdown, confidence, warnings, alternatives, and State Transition log and can reproduce a run from its stored snapshot and configuration.

FR21: Produce a reproducible academic evidence report linking configuration, scenario inputs, run identifiers, results, Memory comparison, KPI values, structured evidence, limitations, rejected alternatives, known risks, and the statistical nature of learning.

### NonFunctional Requirements

NFR1: Complete the deterministic synchronous recommendation path within three seconds at p95 across 100 warm runs on the seeded classroom dataset of up to 100 Technicians and 100 open Work Orders, excluding UI animation and optional external LLM latency and recording hardware/runtime versions.

NFR2: Produce identical feasibility, scoring, confidence, and KPI outputs from identical persisted inputs and configuration.

NFR3: Make State Transition, Human Decision, outcome, and learning writes transactional so failure never leaves a partially advanced Dispatch Run.

NFR4: Derive every user-facing explanation from stored structured evidence and never display or claim access to private model chain-of-thought.

NFR5: Use HTTPS outside local development and retain only zone-level—not exact historical—location in long-term Semantic Patterns.

NFR6: Support keyboard-only operation, visible focus, semantic labels, and text alternatives for status conveyed by color or icons across order creation, dispatch review, Human Decision, outcome capture, and KPI comparison, targeting applicable WCAG 2.2 AA criteria for those MVP flows.

NFR7: Retain every Dispatch Run's input snapshot, configuration version, state history, candidate evidence, Human Decision, and linked outcomes required to reproduce the result.

### Additional Requirements

- AR1: Implement the target as a hexagonal modular monolith: adapters call typed application commands/queries, application services depend on domain policies and ports, and domain code has no framework, database, browser, or provider dependencies.
- AR2: Make `DispatchOrchestrator` the only owner of the versioned transition table and support `WAIT_FOR_OUTCOME`, `COMPLETED`, `FAILED`, `NO_FEASIBLE_CANDIDATES`, and retryable `LEARN_FAILED` semantics in addition to the core PRD stages.
- AR3: Apply all Hard Constraints and persist every check before invoking scoring; the PLAN stage performs eligibility and ranking, while EVALUATE validates evidence and adds confidence, warnings, and explanations without changing eligibility or rank.
- AR4: Implement scoring and confidence as pure decimal calculations over immutable snapshots; use decimal half-up rounding to two places only at the API presentation boundary.
- AR5: Implement each mutating application command with one Unit of Work; repositories cannot commit independently, and each state advancement uses its own transaction plus optimistic compare-and-swap on the run revision.
- AR6: Keep append-only Episodic Memory separate from Semantic Patterns; only the Learning Service may aggregate patterns, and eligibility must never read Memory.
- AR7: Define versioned Pydantic models with unknown fields forbidden for every API and Agent Stage boundary; persist schema failures as typed errors that block transition.
- AR8: Place the canonical local API under `/api/v1`, use a common success/error envelope and stable error codes, and require route-scoped `Idempotency-Key` handling for every external mutation, returning `409 CONFLICT` when a reused key has a different request hash.
- AR9: Keep the vanilla JavaScript browser as a replaceable adapter that only renders API resources and submits commands; business calculations and authoritative state remain on the server.
- AR10: Capture one immutable run snapshot containing UTC clock, Work Order, Technician roster, environment, freshness, and configuration version, and use copied snapshot data for every downstream calculation.
- AR11: Persist structured decision evidence—inputs, checks, contributions, warnings, outputs, and concise templates—rather than private or provider-specific reasoning.
- AR12: Use deterministic local Capture and Analyze adapters for the MVP; any optional LLM adapter must satisfy the same validated contract and record provider/model metadata.
- AR13: Run the MVP as one FastAPI process backed by `data/smart_dispatch.db`, with SQLite foreign keys, WAL mode, busy timeout, fail-closed Alembic migrations before serving, and backups made through SQLite's backup API.
- AR14: Model immutable Scenario Fixtures so Memory on/off comparison runs share Work Order, Technician, environment, clock, and non-memory configuration snapshots.
- AR15: Provide pure domain unit tests, real-SQLite repository integration tests, `/api/v1` contract tests, and browser smoke tests for UJ-1 through UJ-3; every defect correction begins with a failing regression test.
- AR16: Treat the PRD behavioral registry—including formulas, thresholds, evidence fields, KPI semantics, accessibility scope, and marked assumptions—as binding configuration/contract version `v1`.
- AR17: Implement Human Decision and Service Outcome as separate atomic commands: decision leaves an assignment in `WAIT_FOR_OUTCOME`; outcome later advances it to learning.
- AR18: Keep existing `/api/*` routes only as temporary adapters to the same application use cases and remove them together with `server.py` only after all journey and error smoke tests pass exclusively through `/api/v1`.
- AR19: Preserve identity and provenance during migration: retain legacy string IDs beside UUID keys, convert naive Buenos Aires timestamps to UTC with provenance, use deterministic fixture identifiers/timestamps, and import JSON learnings as inactive hypotheses unless they belong to a named synthetic fixture.
- AR20: Bind to `127.0.0.1` by default, serve vendored assets same-origin, insert untrusted browser values with `textContent`, back up before schema-changing migration/reset, and fail closed when migration fails.
- AR21: Enforce availability, all certifications, shift, maximum workday, four-hour driving limit, and required EPP as Hard Constraints; supersede the old priority-5 overtime exception; treat the 50 km radius only as a versioned soft penalty; reject ineligible overrides.
- AR22: Implement calculation registry `v1` exactly: SLA, proximity, workload, quality, Memory, distance penalty, confidence factors, final score, and tie-break formulas from AD-24, using decimal arithmetic and `clamp(x)=min(100,max(0,x))`.
- AR23: Resume runs from their last committed state and guarantee exactly-once learning with uniqueness on `(run_id,state,attempt)` and `(outcome_id,learning_policy_version)`; never recompute a committed stage; atomically append the episode, update the pattern ledger, and transition learning.
- AR24: Pin and reproduce the runtime with Python 3.12.10, uv 0.11.16, FastAPI 0.138.2, Pydantic 2.13.4, SQLAlchemy Core 2.0.51, Alembic 1.18.5, Uvicorn 0.46.0, pytest 9.1.1, coverage.py 7.13.5, Playwright 1.60.0, and the exact `uv.lock`; run one Uvicorn worker on `127.0.0.1:8000`.
- AR25: Organize implementation into `app/api/v1`, `app/application`, bounded `app/domain` packages, `app/contracts`, stage and persistence adapters, migrations, the existing frontend, versioned fixtures, and unit/integration/contract/browser test suites.
- AR26: Generate OpenAPI from the canonical contracts, persist KPI events with configuration versions, create replay runs linked by `source_run_id` with isolated Memory read snapshots, and implement reset as a guarded, backed-up, transactional fixture reload that never deletes exported reports.
- AR27: Standardize API and persistence conventions: snake_case JSON/database names, opaque UUID identifiers, ISO 8601 UTC timestamps ending in `Z`, explicit foreign keys, structured JSON logs without raw address or exact GPS, 1 MiB JSON request limit, and stable `413`, `415`, and `422` responses.
- AR28: Migrate incrementally from the brownfield Python `http.server`, module-level arrays, static frontend, synchronous handler, and `data/learning_store.json`, correcting the known priority-5 `alerts.push(...)` runtime defect through regression coverage.
- AR29: Keep seeded/simulated data and local educational operation as the MVP boundary; defer production authentication/authorization, non-local security, multi-process deployment, real external integrations, vector search, frontend framework migration, and public API compatibility.
- AR30: Provide safe export/backup and academically reproducible fixtures, benchmark metadata, configuration snapshots, evidence links, documented synthetic-data limitations, and Memory-enabled/disabled scenario results.

### UX Design Requirements

No separate UX design contract was included. The actionable user-interface and accessibility obligations contained in the PRD and Architecture Spine are preserved in NFR6 and AR9, AR15, AR18, AR20, AR25, and AR27.

### FR Coverage Map

FR1: Epic 1 - Execute and persist the controlled Dispatch Run State Machine.
FR2: Epic 1 - Record retrievable Agent Stage execution evidence.
FR3: Epic 1 - Handle validation, execution, and no-candidate outcomes explicitly.
FR4: Epic 1 - Capture and validate the dispatcher's Work Order.
FR5: Epic 1 - Derive traceable dispatch requirements.
FR6: Epic 1 - Exclude unavailable Technicians before ranking.
FR7: Epic 1 - Enforce all required certifications.
FR8: Epic 1 - Enforce shift and maximum-workday limits.
FR9: Epic 1 - Enforce driving-hour and equipment safety checks.
FR10: Epic 1 - Normalize and expose deterministic scoring components.
FR11: Epic 1 - Apply the versioned objective function.
FR12: Epic 1 - Rank and explain eligible alternatives.
FR13: Epic 1 - Calculate independent Recommendation Confidence.
FR14: Epic 1 - Surface structured Data Quality Warnings.
FR15: Epic 2 - Record acceptance, eligible override, or declined assignment.
FR16: Epic 2 - Record immutable service outcomes and decision-time evidence.
FR17: Epic 3 - Promote, contradict, decay, and activate Semantic Patterns conservatively.
FR18: Epic 4 - Compute reproducible prototype KPIs.
FR19: Epic 3 - Compare identical scenarios with Memory enabled and disabled.
FR20: Epic 4 - Expose versioned local simulation and replay operations.
FR21: Epic 4 - Produce the reproducible academic evidence package.

## Epic List

### Epic 1: Safe and Explainable Dispatch Recommendation

The dispatcher can create a Work Order and receive a deterministic, auditable recommendation with eligibility checks, scoring, confidence, warnings, alternatives, and explicit failure outcomes.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14

**Implementation notes:** Establish the reproducible runtime, hexagonal application spine, immutable run snapshots, versioned contracts, SQLite persistence, canonical `/api/v1` surface, incremental brownfield adapter, accessible recommendation flow, and automated tests required to deliver the first complete user outcome.

### Epic 2: Human Decision and Service Outcome

The dispatcher can accept, override, or decline a recommendation and later record the real service outcome without losing the alternatives and evidence visible when the decision was made.

**FRs covered:** FR15, FR16

**Implementation notes:** Add separate idempotent and transactional Decision and Outcome commands, eligibility enforcement for overrides, `WAIT_FOR_OUTCOME` behavior, immutable Episodic Memory, concurrency protection, and accessible decision/outcome interfaces.

### Epic 3: Controlled Learning and Memory Experimentation

The system can learn conservatively from accumulated outcomes and demonstrate how Memory changes recommendations without ever altering Hard Constraint results.

**FRs covered:** FR17, FR19

**Implementation notes:** Implement exactly-once learning, Semantic Pattern promotion/contradiction/decay, isolated Memory snapshots, comparable Scenario Fixtures, deterministic Memory scoring, and paired Memory-enabled/disabled results.

### Epic 4: Operational and Academic Evidence

Rossy can measure the prototype, replay scenarios through the local API, and produce a reproducible evidence package suitable for the course submission.

**FRs covered:** FR18, FR20, FR21

**Implementation notes:** Complete replay operations, KPI event contracts, benchmark metadata, evidence exports, report generation, reset/backup safety, and the automated academic scenario suite covering UJ-1 through UJ-3.

## Epic 1: Safe and Explainable Dispatch Recommendation

The dispatcher can create a Work Order and receive a deterministic, auditable recommendation with eligibility checks, scoring, confidence, warnings, alternatives, and explicit failure outcomes.

### Story 1.1: Launch the Local Simulator Safely and Reproducibly

**Requirements:** FR20 (runtime foundation), NFR3, NFR5; AR13, AR22, AR24, AR26

As Rossy or a course evaluator,
I want to launch the local simulator from a reproducible environment,
So that the academic demonstration starts consistently without risking existing evidence.

**Acceptance Criteria:**

**Given** a clean project checkout with the pinned Python version available
**When** the documented frozen dependency installation and launch commands are executed
**Then** the application starts through FastAPI and Uvicorn on `127.0.0.1:8000` with one worker
**And** `.python-version`, `pyproject.toml`, and `uv.lock` define the approved runtime and exact dependency graph.

**Given** the application is starting with a valid SQLite database
**When** persistence is initialized
**Then** SQLite foreign keys, WAL mode, and the configured busy timeout are enabled
**And** the runtime database is stored at `data/smart_dispatch.db` without being committed to source control.

**Given** pending database migrations exist
**When** the launcher starts
**Then** Alembic migrations run before the HTTP server begins accepting requests
**And** a schema-changing migration creates a recoverable SQLite backup when an existing database is present.

**Given** a migration fails
**When** the launcher handles the failure
**Then** the HTTP server does not start
**And** the error identifies the failed migration without modifying unrelated user data.

**Given** the legacy `server.py` entry point is used during the migration period
**When** it launches the application
**Then** it delegates to the same canonical composition root
**And** it does not contain an independent implementation of dispatch business rules.

**Given** the initial runtime foundation is created
**When** its database schema is inspected
**Then** it contains only the migration and runtime structures required by this story
**And** domain tables needed by later capabilities are not created prematurely.

**Given** the launch and migration test suite is executed
**When** the success, existing-database, and migration-failure cases run
**Then** all cases pass reproducibly
**And** the tests verify loopback-only binding, single-worker execution, backup creation, and fail-closed startup.

### Story 1.2: Capture and Validate a Work Order

**Requirements:** FR4; NFR3, NFR5, NFR7

As a dispatcher,
I want to submit the incident and its available operational context,
So that the system can create a trustworthy Work Order for dispatch analysis.

**Acceptance Criteria:**

**Given** valid incident text, address, zone, and optional context
**When** the dispatcher submits the Work Order through the versioned local API
**Then** the system persists the Work Order in one transaction
**And** returns it through the standard success envelope with its opaque identifier, schema version, raw input, and creation timestamp in UTC.

**Given** a valid Work Order request
**When** its structured representation is stored
**Then** the original incident text is preserved without being replaced by later derived values
**And** only the Work Order and idempotency structures required by this capability are added to persistence.

**Given** a request is missing a required field or contains a blank required value
**When** contract validation runs
**Then** the API returns a stable `422` error with field-level details
**And** no Work Order or partial persistence record is created.

**Given** the request contains an unknown field
**When** the versioned Pydantic contract validates it
**Then** the request is rejected through the standard error envelope
**And** the response identifies the unsupported field.

**Given** a mutating request includes an `Idempotency-Key`
**When** the same key and identical request body are submitted again to the same route
**Then** the original successful response is returned without creating a duplicate Work Order
**And** using the same key with a different request body returns `409 CONFLICT`.

**Given** a request is not JSON or exceeds the 1 MiB body limit
**When** it reaches the API adapter
**Then** the system returns the configured stable `415` or `413` error
**And** no application command is executed.

**Given** Work Order creation fails during persistence
**When** the Unit of Work rolls back
**Then** no partial Work Order or idempotency result remains
**And** the error is mapped once by the HTTP adapter without exposing an internal stack trace.

**Given** the Work Order includes an address or other sensitive operational text
**When** structured logs are emitted
**Then** logs include the request identifier and operation status
**And** do not include the raw address, exact coordinates, or complete incident narrative.

**Given** the Work Order contract and endpoint tests execute
**When** valid, invalid, duplicate, oversized, unsupported-media, and persistence-failure cases are evaluated
**Then** all response bodies validate against the generated `/api/v1` OpenAPI contract
**And** the tests prove that invalid requests cannot mutate persistence.

### Story 1.3: Derive Dispatch Requirements with Provenance

**Requirements:** FR5; NFR2, NFR4, NFR7

As a dispatcher,
I want the incident to be converted into explicit dispatch requirements,
So that I can understand which operational facts will govern the recommendation.

**Acceptance Criteria:**

**Given** a valid stored Work Order
**When** the deterministic Analyze capability processes it
**Then** it derives category, priority, SLA target, required certifications, and estimated service duration
**And** the output validates against the versioned Analyze contract before it is persisted.

**Given** a derived field was present explicitly in the submitted context
**When** analysis produces its result
**Then** the field provenance is recorded as `supplied`
**And** the stored evidence identifies the corresponding source field without duplicating sensitive raw text.

**Given** a field can be determined from the incident through a configured deterministic rule
**When** analysis produces its result
**Then** the field provenance is recorded as `inferred`
**And** the evidence identifies the rule and configuration version used.

**Given** a required dispatch field cannot be supplied or inferred
**When** the configured default is applied
**Then** the field provenance is recorded as `defaulted`
**And** a structured Data Quality Warning identifies the affected field, fallback value, and expected impact.

**Given** the incident is unsupported or ambiguous
**When** the deterministic classifier cannot produce a reliable value
**Then** the result contains a typed warning rather than inventing unsupported certainty
**And** every required downstream field still has explicit provenance or a typed validation failure.

**Given** identical Work Order data and analysis configuration
**When** analysis is executed repeatedly
**Then** the structured output is identical
**And** no external LLM or network service is required.

**Given** an optional LLM Analyze adapter is configured in the future
**When** it proposes a structured result
**Then** it must satisfy the same versioned contract before the result can be accepted
**And** provider and model metadata are recorded without making the adapter authoritative over validation.

**Given** Analyze persistence fails
**When** the application command rolls back
**Then** the previously stored Work Order remains unchanged
**And** no partial analysis result is available to later capabilities.

**Given** Analyze unit, integration, and contract tests run
**When** supplied, inferred, defaulted, ambiguous, invalid-output, and rollback cases are evaluated
**Then** all cases produce the expected provenance and warnings
**And** repeated deterministic executions produce byte-equivalent structured domain results before API presentation formatting.

### Story 1.4: Determine Technician Eligibility Before Scoring

**Requirements:** FR6, FR7, FR8, FR9; NFR2, NFR7

As a dispatcher,
I want every Technician evaluated against all safety and operational constraints,
So that no ineligible Technician can enter the recommendation ranking.

**Acceptance Criteria:**

**Given** analyzed Work Order requirements and a Technician roster
**When** the Eligibility Policy evaluates candidates
**Then** it checks every Technician against availability, all required certifications, shift, maximum workday, four-hour driving limit, and required EPP
**And** persists a pass/fail result and structured reason for every enabled check.

**Given** a Technician is unavailable
**When** eligibility is evaluated
**Then** the Technician is marked ineligible
**And** the candidate result contains no Objective Score.

**Given** a Work Order requires multiple certifications
**When** a Technician possesses only a subset
**Then** the certification check fails
**And** priority or Memory cannot restore eligibility.

**Given** estimated travel plus service exceeds the configured maximum workday or falls outside the Technician's shift
**When** eligibility is evaluated
**Then** the Technician is rejected using the same captured clock and duration values
**And** emergency priority, including priority 5, does not silently bypass the rule.

**Given** a Technician would exceed the four-hour driving limit or lacks required EPP
**When** the corresponding safety rule is enabled
**Then** the Technician is rejected
**And** the failed rule is visible independently from all other constraint results.

**Given** an enabled driving-hour or equipment check lacks required source data
**When** the policy cannot evaluate it reliably
**Then** the system produces a visible configuration or Data Quality Warning
**And** it does not treat the missing check as an implicit pass.

**Given** an eligible Technician is more than 50 km away
**When** eligibility is evaluated
**Then** distance does not make that Technician ineligible
**And** the later scoring capability may apply the configured soft distance penalty.

**Given** multiple constraints fail for one Technician
**When** eligibility evidence is returned
**Then** every evaluated failure is included rather than stopping at the first failure
**And** the dispatcher can distinguish all discard reasons.

**Given** no Technician passes every Hard Constraint
**When** eligibility completes
**Then** the result contains an empty eligible set and all rejection evidence
**And** it does not fabricate a recommendation or score.

**Given** identical Work Order, Technician, environment, clock, and configuration snapshots
**When** the Eligibility Policy runs repeatedly
**Then** the results are identical
**And** the policy performs no network or Memory access.

**Given** the legacy priority-5 overtime scenario is executed
**When** the maximum-workday branch runs
**Then** it returns a typed eligibility result without the historical `alerts.push(...)` runtime failure
**And** a regression test proves the stricter no-overtime rule.

**Given** eligibility unit and real-SQLite integration tests execute
**When** individual constraints, combined failures, missing safety inputs, distant candidates, and no-feasible-candidate cases run
**Then** 100% of ineligible Technicians are rejected before ranking
**And** stored evidence remains linked to the evaluated Work Order and configuration version.

### Story 1.5: Score and Rank Eligible Technicians Deterministically

**Requirements:** FR10, FR11, FR12; NFR2, NFR4, NFR7

As a dispatcher,
I want eligible Technicians ranked by a transparent and reproducible objective function,
So that I can compare qualified alternatives using consistent operational criteria.

**Acceptance Criteria:**

**Given** a Technician passed every Hard Constraint
**When** the Scoring Policy evaluates the candidate
**Then** it calculates SLA, proximity, workload balance, quality, and Memory components on a 0–100 scale
**And** exposes each raw input, normalized value, configured weight, weighted contribution, and penalty.

**Given** the calculation registry version is `v1`
**When** components are normalized
**Then** the system applies `SLA = clamp(100 × (1 − eta_minutes / sla_minutes))`, `proximity = clamp(100 − 2 × distance_km)`, `workload_balance = clamp(100 × (1 − projected_work_hours / max_workday_hours))`, `quality = clamp(20 × rating_0_to_5)`, and `memory = clamp(50 + Σ(confidence × signed_effect_points))`
**And** `clamp(x)` is defined as `min(100, max(0, x))`.

**Given** no active Semantic Pattern applies to a candidate
**When** the Memory component is calculated
**Then** its value is the neutral score of 50
**And** imported inactive hypotheses do not influence ranking.

**Given** a Technician has no usable quality rating
**When** the quality component is calculated
**Then** it uses the neutral value of 50
**And** produces a structured warning identifying the fallback and its impact.

**Given** an eligible Technician is farther than 50 km
**When** penalties are calculated
**Then** the distance penalty is `min(20, max(0, distance_km − 50))`
**And** any other penalty is explicitly named, versioned, and zero by default.

**Given** all components and penalties are available
**When** the Objective Score is calculated
**Then** it applies `0.35 × SLA + 0.25 × proximity + 0.20 × workload_balance + 0.10 × quality + 0.10 × memory − penalties`
**And** stores the configuration version and clamps the final result to 0–100.

**Given** several eligible candidates have been scored
**When** they are ranked
**Then** they are ordered by Objective Score descending
**And** ties are resolved by higher SLA, higher quality, lower travel time, and lexicographically ascending Technician identifier, in that order.

**Given** a Technician failed at least one Hard Constraint
**When** candidate results are assembled
**Then** the Technician has no Objective Score or component contributions
**And** appears only in the ineligible collection with its constraint evidence.

**Given** score calculations are performed internally
**When** arithmetic and persistence occur
**Then** decimal arithmetic is used without intermediate presentation rounding
**And** decimal half-up rounding to two places occurs only at the API presentation boundary.

**Given** identical immutable inputs and configuration
**When** scoring and ranking run repeatedly
**Then** the stored domain results and candidate order are identical
**And** the Scoring Policy performs no hidden I/O or mutable global-state access.

**Given** scoring tests execute
**When** boundary values, missing quality, neutral Memory, distances over 50 km, penalties, score clamping, and every tie-break level are evaluated
**Then** all arithmetic matches the recorded configuration exactly
**And** no ineligible candidate is ever scored.

### Story 1.6: Explain Recommendation Confidence and Data Quality

**Requirements:** FR12, FR13, FR14; NFR2, NFR4, NFR7

As a dispatcher,
I want to see how trustworthy the recommendation is and which data limitations affect it,
So that I can make an informed decision without confusing a high score with high certainty.

**Acceptance Criteria:**

**Given** at least one eligible ranked candidate
**When** the Confidence Policy evaluates the recommendation
**Then** it calculates data quality, historical evidence, score margin, and condition certainty independently from Objective Score
**And** exposes every factor, weight, contribution, final value, and configuration version.

**Given** confidence registry `v1`
**When** Recommendation Confidence is calculated
**Then** it applies `0.35 × data_quality + 0.25 × historical_evidence + 0.25 × score_margin + 0.15 × condition_certainty`
**And** clamps the result to 0–100 without modifying candidate scores or order.

**Given** source freshness is evaluated
**When** data quality is calculated
**Then** current, stale, and unavailable sources contribute 100, 75, and 50 respectively
**And** `data_quality` is the arithmetic mean of all applicable source-quality values.

**Given** active historical evidence exists
**When** the historical-evidence factor is calculated
**Then** it uses `min(100, 10 × active_supporting_episode_count)`
**And** inactive hypotheses and unrelated episodes are excluded.

**Given** two or more eligible candidates exist
**When** score margin is calculated
**Then** it uses `min(100, 10 × (first_score − second_score))`
**And** one eligible candidate produces a margin factor of 50 while no eligible candidates produce no Recommendation Confidence.

**Given** uncertain operating conditions are present
**When** condition certainty is calculated
**Then** it uses `clamp(100 − 25 × uncertain_condition_count)`
**And** each counted condition is identified in structured evidence.

**Given** the final confidence value is available
**When** its label is assigned
**Then** values 0–49 are `low`, 50–74 are `medium`, and 75–100 are `high`
**And** the confidence label is displayed separately from the Objective Score.

**Given** GPS freshness is evaluated
**When** its age is at most 5 minutes, between 5 and 30 minutes, or greater than 30 minutes
**Then** it is classified as current, stale, or unavailable respectively
**And** unavailable GPS uses the last known zone only when present and marks the fallback as estimated.

**Given** traffic or weather freshness is evaluated
**When** its age is at most 15 minutes, between 15 and 60 minutes, or greater than 60 minutes
**Then** it is classified as current, stale, or unavailable respectively
**And** an unavailable source uses the documented seeded/default scenario value.

**Given** any source is missing, stale, estimated, or unavailable
**When** recommendation evidence is assembled
**Then** a warning identifies the source, affected field, observed freshness or quality, fallback, and recommendation impact
**And** warnings remain structured and reproducible rather than free-form reasoning traces.

**Given** candidate results are returned
**When** the dispatcher reviews them
**Then** eligible alternatives include their ranking, score breakdown, confidence context, and warnings
**And** ineligible Technicians are listed separately with all discard reasons and no score.

**Given** a seeded scenario has a high leading Objective Score but weak or stale evidence
**When** confidence is calculated
**Then** the result can correctly be labeled `low`
**And** an automated test proves score and confidence are not conflated.

### Story 1.7: Execute an Auditable Dispatch Run

**Requirements:** FR1, FR2, FR3, FR20; NFR1, NFR2, NFR3, NFR7

As a dispatcher,
I want the complete recommendation process controlled and recorded as one Dispatch Run,
So that I can trust its state and inspect the evidence behind its result.

**Acceptance Criteria:**

**Given** a valid Work Order, Technician roster, environment data, and configuration
**When** a Dispatch Run starts
**Then** it captures one immutable snapshot containing the UTC clock, Work Order, roster, environment, freshness data, and configuration version
**And** every later stage reads copied snapshot data rather than mutable operational rows.

**Given** a recommendation run is active
**When** the orchestrator advances it
**Then** only `DispatchOrchestrator` may apply the versioned transition table through `CAPTURE → ANALYZE → PLAN → EVALUATE`
**And** a successful recommendation stops at `WAIT_FOR_DECISION` without allowing an Agent Stage or adapter to invent a transition.

**Given** PLAN executes
**When** it processes the immutable snapshot
**Then** it applies every Hard Constraint before scoring eligible candidates
**And** EVALUATE may validate evidence, calculate confidence and warnings, and render explanations without changing eligibility or rank.

**Given** an Agent Stage returns output
**When** the orchestrator receives it
**Then** the output is validated against its versioned Pydantic contract with unknown fields forbidden
**And** only valid output can be persisted and followed by a State Transition.

**Given** a stage starts or completes
**When** its execution record is written
**Then** the record contains start, end, duration, status, schema version, input/output snapshot references, attempt number, and typed error when applicable
**And** stage and transition records are returned chronologically.

**Given** a stage contract is invalid or stage execution fails
**When** the orchestrator handles the failure
**Then** the run enters the configured typed `FAILED` outcome without losing prior committed evidence
**And** no partial stage output or unauthorized next transition is persisted.

**Given** no Technician passes all Hard Constraints
**When** EVALUATE completes
**Then** the run enters `NO_FEASIBLE_CANDIDATES`
**And** contains every rejection reason, no recommendation, no Objective Score for ineligible Technicians, and no Recommendation Confidence.

### Story 1.8: Recover, Protect, and Benchmark Dispatch Runs

**Requirements:** FR1, FR2, FR20; NFR1, NFR2, NFR3, NFR5, NFR7

As Rossy or a course evaluator,
I want Dispatch Runs protected against retries, concurrency, and process failure,
So that the simulator remains reproducible, recoverable, private, and fast enough for demonstration.

**Acceptance Criteria:**

**Given** a stage advancement is committed
**When** another command attempts to advance the same run revision
**Then** compare-and-swap protection permits only one write
**And** a stale writer receives `409 CONFLICT` without duplicating a transition.

**Given** the process crashes after one or more stages committed
**When** the run is resumed
**Then** it continues from the last durable state using uniqueness on `(run_id, state, attempt)`
**And** no previously committed stage is recomputed.

**Given** stored snapshot evidence is requested
**When** an authorized local query resolves its reference
**Then** it returns schema-versioned content retained for the prototype evidence window
**And** exact historical location and other configured sensitive fields are redacted.

**Given** a client starts the same run command again with the same route, body, and `Idempotency-Key`
**When** the retry is handled
**Then** the original Dispatch Run response is returned
**And** no duplicate run, snapshot, stage, or transition is created.

**Given** 100 warm seeded runs with up to 100 Technicians and 100 open Work Orders
**When** the deterministic synchronous recommendation path is benchmarked
**Then** p95 completion time is below three seconds, excluding UI animation and optional LLM latency
**And** the result records hardware, runtime, configuration, and fixture versions.

### Story 1.9: Review a Recommendation in the Accessible Browser Interface

**Requirements:** FR3, FR4, FR12, FR13, FR14, FR20; NFR4, NFR6

As a dispatcher,
I want to create and review a dispatch recommendation from the browser,
So that I can understand the result and its uncertainty without using technical tools.

**Acceptance Criteria:**

**Given** the local application is running
**When** the dispatcher opens it in the browser
**Then** the existing vanilla JavaScript interface is served from the same origin with vendored assets
**And** it communicates with the canonical `/api/v1` contracts.

**Given** the dispatcher completes the Work Order form
**When** the form is submitted
**Then** the interface starts the Dispatch Run and displays its progress through the persisted states
**And** DOM state or animation timing never becomes authoritative application state.

**Given** Work Order validation fails
**When** the API returns field-level errors
**Then** each error is associated with its corresponding form control and announced accessibly
**And** valid user-entered values remain available for correction.

**Given** a recommendation reaches `WAIT_FOR_DECISION`
**When** the review view renders
**Then** it shows the recommended Technician, Objective Score, separate Recommendation Confidence value and label, component breakdown, warnings, and configuration version
**And** every displayed explanation is derived from structured evidence rather than private reasoning text.

**Given** multiple evaluated candidates exist
**When** the dispatcher reviews them
**Then** eligible alternatives appear in deterministic ranking order with score evidence
**And** ineligible Technicians appear separately with all discard reasons and no score.

**Given** a run reaches `NO_FEASIBLE_CANDIDATES` or a typed failure
**When** the interface renders the result
**Then** it presents an accurate, recoverable no-candidate or error state
**And** it never fabricates a recommendation or infer that a failed request succeeded.

**Given** a keyboard-only user completes order creation and recommendation review
**When** the user navigates controls, errors, results, alternatives, and evidence
**Then** every action has logical focus order, visible focus, semantic labels, and text alternatives for visual status
**And** the named flow satisfies the applicable WCAG 2.2 AA assumption.

**Given** API-provided values are rendered
**When** they are inserted into the page
**Then** untrusted content uses `textContent` or equivalent safe DOM APIs
**And** browser smoke tests prove the success, validation, stale-data, and no-candidate paths without external network access.

### Story 1.10: Migrate the Brownfield Prototype Safely

**Requirements:** FR1–FR14 (brownfield compatibility); NFR3, NFR7

As Rossy,
I want the new recommendation flow introduced without breaking or misrepresenting the working classroom prototype,
So that legacy data and interfaces migrate safely into the approved architecture.

**Acceptance Criteria:**

**Given** an existing `/api/*` route is still used
**When** it receives a supported legacy request
**Then** it delegates to the same application use case as `/api/v1`
**And** only translates the request or response envelope without duplicating business rules.

**Given** legacy operational identifiers and JSON learning records exist
**When** the Epic 1 migration inventories them
**Then** operational string IDs are retained beside UUID primary keys and naive Buenos Aires timestamps are converted to UTC with provenance
**And** learning records remain preserved in a deterministic import manifest until Semantic Pattern persistence is introduced by a later approved learning story.

**Given** seeded classroom data is loaded
**When** fixtures are created from legacy arrays or files
**Then** fixture identifiers and timestamps are deterministic
**And** assumptions are labeled as synthetic rather than presented as observed historical evidence.

**Given** any migration or fixture load fails
**When** its transaction is rolled back
**Then** the prior database remains recoverable from backup
**And** the application fails closed instead of serving mixed old and new state.

### Story 1.11: Verify the First Safe Dispatch Increment

**Requirements:** FR1–FR14 (verification); NFR1–NFR7

As Rossy,
I want the first safe recommendation increment verified across every architecture boundary,
So that I can demonstrate it without losing the still-needed brownfield compatibility surface.

**Acceptance Criteria:**

**Given** the complete Epic 1 automated suite runs
**When** unit, real-SQLite integration, OpenAPI contract, regression, browser, determinism, and performance tests execute
**Then** FR1 through FR14 and the applicable NFRs have passing evidence
**And** the priority-5 defect, Hard Constraint invariance, score arithmetic, low-confidence/high-score, and no-candidate scenarios are explicitly covered.

**Given** later journeys have not yet migrated completely to `/api/v1`
**When** Epic 1 is delivered
**Then** `server.py` and required legacy adapters remain available as compatibility surfaces
**And** their eventual removal is gated by all UJ-1 through UJ-3 journey and error smoke tests passing through `/api/v1`.

## Epic 2: Human Decision and Service Outcome

The dispatcher can accept, override, or decline a recommendation and later record the real service outcome without losing the alternatives and evidence visible when the decision was made.

### Story 2.1: Record the Dispatcher's Assignment Decision

**Requirements:** FR15; NFR3, NFR6, NFR7

As a dispatcher,
I want to accept, override, or decline a recommendation,
So that the final assignment remains under human control and is auditable.

**Acceptance Criteria:**

**Given** a run is in `WAIT_FOR_DECISION`
**When** the dispatcher accepts its recommendation with an idempotent command
**Then** one Human Decision is persisted with the selected Technician and decision timestamp
**And** the run advances atomically to `WAIT_FOR_OUTCOME`.

**Given** the dispatcher selects a different eligible Technician
**When** an override with a nonblank reason is submitted
**Then** the override and reason are persisted
**And** the selected Technician, recommendation, alternatives, warnings, scores, confidence, and evidence visible at decision time are frozen with the decision.

**Given** an override targets an ineligible or unknown Technician, or omits its reason
**When** validation runs
**Then** the command returns a stable typed error
**And** no decision or State Transition is written.

**Given** the dispatcher declines assignment
**When** the decision is recorded
**Then** no Technician is selected and the run advances to `COMPLETED`
**And** the declined result remains distinguishable from a no-feasible-candidates outcome.

**Given** two clients submit decisions for the same run revision
**When** concurrency and uniqueness guards execute
**Then** only one Human Decision commits
**And** the stale command returns `409 CONFLICT`.

**Given** an identical route, body, and `Idempotency-Key` are retried
**When** the request is processed
**Then** the original response is returned without duplication
**And** transaction, contract, override, decline, and concurrency tests pass against real SQLite.

### Story 2.2: Record the Service Outcome for Episodic Learning

**Requirements:** FR16; NFR3, NFR7

As a dispatcher,
I want to record what happened after the service visit,
So that predictions and real results become immutable source evidence for later learning.

**Acceptance Criteria:**

**Given** an assigned run is in `WAIT_FOR_OUTCOME`
**When** a valid outcome command is submitted
**Then** it persists completion status, selected Technician, predicted duration, actual duration when supplied, First-Time Fix when supplied, and dispatcher feedback
**And** advances the run to `LEARN` in the same transaction.

**Given** an optional outcome value is absent
**When** the outcome is persisted
**Then** its value is explicitly represented as unknown rather than zero or false
**And** later KPI calculations can distinguish missing from negative evidence.

**Given** an outcome commits
**When** its immutable source evidence is assembled
**Then** it links the Work Order, Dispatch Run, Human Decision, outcome, recommendation, alternatives, and decision-time evidence
**And** the subsequent baseline `LEARN` command can append Episodic Memory without rewriting any source record.

**Given** the run is not in `WAIT_FOR_OUTCOME` or has no assignment decision
**When** an outcome is submitted
**Then** the command returns a typed state error
**And** creates neither an outcome nor an episode.

**Given** persistence fails at any point
**When** the Unit of Work rolls back
**Then** the outcome and transition are both absent
**And** the previously committed Human Decision remains intact.

**Given** the same outcome is retried or concurrent outcomes are submitted
**When** idempotency, revision, and uniqueness checks run
**Then** exactly one outcome is stored for later learning
**And** real-SQLite tests prove atomicity, immutable source evidence, unknown optionals, and duplicate prevention.

### Story 2.3: Complete Baseline Episodic Learning

**Requirements:** FR16; NFR2, NFR3, NFR7

As a dispatcher,
I want a recorded outcome converted into durable Episodic Memory even before adaptive ranking is enabled,
So that the Human Decision and service result form a complete auditable run without depending on a future epic.

**Acceptance Criteria:**

**Given** a run in `LEARN` has one persisted outcome and immutable decision-time evidence
**When** the baseline Learning Service executes
**Then** it appends exactly one Episodic Memory record linked to the run, Work Order, Decision, outcome, recommendation, alternatives, and source evidence
**And** no source record or earlier episode is overwritten.

**Given** the first observation for a pattern grouping is processed
**When** the baseline learning policy records its result
**Then** it may persist only an inactive, non-influential pattern state with its sample count and support
**And** one observation cannot activate a Semantic Pattern or influence eligibility or scoring.

**Given** baseline learning succeeds
**When** its Unit of Work commits
**Then** the episode append, `(outcome_id, learning_policy_version)` ledger result, any inactive pattern result, and transition to `COMPLETED` are atomic
**And** the completed run is independently reproducible without Epic 3.

**Given** learning persistence fails or the process crashes before commit
**When** failure handling executes
**Then** the outcome remains durable while the run enters retryable `LEARN_FAILED`
**And** no partial episode, ledger, pattern result, or completion transition remains.

**Given** a failed or already completed learning command is retried
**When** uniqueness and idempotency guards execute
**Then** the missing transaction is applied once or the original completed result is returned
**And** the same outcome/policy version is never counted twice.

**Given** baseline learning tests execute
**When** success, first observation, rollback, crash, retry, and duplicate cases run against real SQLite
**Then** the run reaches `COMPLETED` with one linked episode
**And** no active Semantic Pattern or Hard Constraint change is produced.

### Story 2.4: Complete the Accessible Decision and Outcome Flow

**Requirements:** FR15, FR16; NFR6

As a dispatcher,
I want to record my decision and the later service result from the browser,
So that the complete human-controlled workflow is usable without technical tools.

**Acceptance Criteria:**

**Given** a run is waiting for a decision
**When** the decision view renders
**Then** acceptance, eligible override, and decline actions are keyboard accessible
**And** the evidence being preserved with the decision remains visible.

**Given** the dispatcher chooses an override
**When** the form is submitted
**Then** a reason is required and only eligible alternatives can be selected
**And** validation errors are associated with controls and announced without losing entered text.

**Given** an assignment decision succeeds
**When** the interface receives the canonical server state
**Then** it shows `WAIT_FOR_OUTCOME` and provides later outcome capture
**And** it does not keep a browser transaction or infer state from animation.

**Given** the outcome form is completed
**When** it is submitted
**Then** optional unknown values remain distinguishable from explicit negative values
**And** duplicate submission is prevented through the idempotent API.

**Given** the complete UJ-2 browser scenario runs
**When** Martín overrides an eligible recommendation, records a reason, and later records the result
**Then** the visible state matches the immutable Decision and Outcome records and, after learning, their linked Episodic Memory
**And** keyboard, focus, semantic-label, error, conflict, and retry behavior satisfy the named accessibility scope.

## Epic 3: Controlled Learning and Memory Experimentation

The system can learn conservatively from accumulated outcomes and demonstrate how Memory changes recommendations without ever altering Hard Constraint results.

### Story 3.1: Promote Semantic Patterns Conservatively and Exactly Once

**Requirements:** FR17; NFR2, NFR3, NFR7

As Rossy,
I want completed outcomes aggregated through a conservative learning policy,
So that repeated evidence can influence future recommendations without turning one observation into a rule.

**Acceptance Criteria:**

**Given** an existing Episodic Memory record has not been processed by the current Semantic Pattern policy version
**When** the Semantic Pattern policy processes it
**Then** it groups the existing episode by versioned pattern type and grouping keys without appending a duplicate episode
**And** records the policy version, supporting episode ID, sample count, confidence, update time, and decay parameters.

**Given** the Semantic Pattern policy is enabled for a new run in `LEARN`
**When** the full Learning Service commits
**Then** the episode append, Semantic Pattern policy ledger, pattern update, and transition to `COMPLETED` occur in one transaction
**And** the baseline exactly-once and `LEARN_FAILED` recovery guarantees remain intact.

**Given** the preserved legacy learning import manifest exists
**When** Semantic Pattern persistence is introduced
**Then** legacy records are imported idempotently with retained external IDs and timestamp provenance
**And** they remain inactive hypotheses unless they belong to a named synthetic fixture.

**Given** fewer than three consistent episodes support a pattern
**When** learning completes
**Then** the pattern remains inactive
**And** one observation cannot create an active Semantic Pattern.

**Given** a consistent episode is processed
**When** confidence is updated
**Then** it adds `0.20 × (1 − confidence)`
**And** consistency requires matching pattern type/grouping keys and agreeing numeric direction.

**Given** a contradictory episode is processed
**When** confidence is updated
**Then** confidence is multiplied by `0.70`
**And** the contradiction and supporting episode remain auditable.

**Given** a pattern has aged without supporting evidence
**When** decay is evaluated
**Then** the configured 90-day half-life is applied from persisted UTC timestamps
**And** the pattern becomes inactive below `0.50` confidence and is promoted only with at least three consistent episodes and confidence at or above `0.60`.

**Given** learning succeeds
**When** a pre-existing episode is incorporated into a Semantic Pattern
**Then** its pattern-policy ledger and Semantic Pattern update are atomic
**And** uniqueness on `(outcome_id, learning_policy_version)` prevents a second application without duplicating Episodic Memory.

**Given** learning fails or the process crashes
**When** failure handling runs
**Then** the outcome and prior evidence remain durable while the run enters retryable `LEARN_FAILED`
**And** an idempotent retry returns to `LEARN`, applies any missing update once, and completes without double-counting.

### Story 3.2: Apply Active Memory Without Changing Eligibility

**Requirements:** FR17; NFR2, NFR4, NFR7

As a dispatcher,
I want proven Semantic Patterns reflected transparently in candidate scoring,
So that accumulated evidence can improve ranking without weakening safety rules.

**Acceptance Criteria:**

**Given** active Semantic Patterns match an eligible candidate
**When** scoring reads its isolated Memory snapshot
**Then** the Memory component is `clamp(50 + Σ(confidence × signed_effect_points))`
**And** every contribution identifies its pattern, confidence, effect, and supporting episode count.

**Given** a pattern is inactive, decayed below threshold, contradictory, or outside the run's Memory snapshot
**When** scoring executes
**Then** it contributes nothing
**And** the stored run result remains reproducible if patterns change later.

**Given** Memory contains evidence about a Technician
**When** Eligibility Policy runs
**Then** it performs no Memory read and produces the same Hard Constraint results
**And** Memory can influence only eligible candidates through the configured score component.

**Given** active support changes the leading candidate
**When** recommendation evidence is assembled
**Then** the changed Memory contribution and rank are visible
**And** Objective Score and Recommendation Confidence remain separate calculations.

**Given** historical-evidence confidence is calculated
**When** matching active supporting episodes are counted
**Then** it uses `min(100, 10 × active_supporting_episode_count)`
**And** unrelated or inactive evidence is excluded.

**Given** Memory scoring tests run
**When** active, inactive, contradictory, decayed, bounded, and rank-changing cases execute
**Then** component arithmetic is exact and deterministic
**And** all Hard Constraint fixtures remain invariant.

### Story 3.3: Compare Identical Scenarios with Memory On and Off

**Requirements:** FR19; NFR2, NFR6, NFR7

As Rossy,
I want to compare the same scenario with Memory enabled and disabled,
So that I can demonstrate exactly what learning changed and what remained invariant.

**Acceptance Criteria:**

**Given** a versioned Scenario Fixture
**When** paired comparison runs are created
**Then** both use identical Work Order, Technician, environment, clock, and non-memory configuration snapshots
**And** they differ only in Memory Experiment Mode and have linked run identifiers.

**Given** Memory Mode is disabled
**When** scoring executes
**Then** Semantic Pattern reads are disabled and the Memory component is neutral 50
**And** outcome and Episodic Memory writes remain enabled.

**Given** both paired runs complete
**When** their results are compared
**Then** the comparison identifies changed ranks, Memory contributions, recommendation, confidence, and relevant KPI inputs
**And** Hard Constraint results are byte-equivalent after excluding run-specific identifiers.

**Given** a fixture contains sufficient active evidence to change ordering
**When** the paired runs execute
**Then** at least one seeded comparison shows a visible rank or recommendation change
**And** another seeded comparison correctly demonstrates no ranking change.

**Given** comparison results are opened in the browser
**When** a keyboard or assistive-technology user inspects them
**Then** both modes, differences, invariants, warnings, and evidence links are available as text
**And** status is not communicated by color alone.

**Given** comparison contract and browser tests run
**When** changed-rank, unchanged-rank, no-candidate, stale-data, and retry cases execute
**Then** paired inputs and Hard Constraints remain invariant
**And** each reported difference resolves to stored structured evidence.

## Epic 4: Operational and Academic Evidence

Rossy can measure the prototype, replay scenarios through the local API, and produce a reproducible evidence package suitable for the course submission.

### Story 4.1: Compute and Review Reproducible Prototype KPIs

**Requirements:** FR18; NFR2, NFR6, NFR7

As Rossy,
I want operational and system KPIs computed from stored evidence,
So that I can evaluate the prototype with transparent definitions instead of unsupported claims.

**Acceptance Criteria:**

**Given** a selected UTC window and configuration version
**When** KPI calculation runs
**Then** each result records its numerator, denominator, exclusions, time window, unit, configuration version, and source evidence
**And** insufficient data produces `unavailable` rather than zero.

**Given** eligible evidence exists
**When** KPI-1 through KPI-4 are calculated
**Then** the system reports median/p95 time from run start to Human Decision, SLA compliance, eligible override rate, and service-duration mean absolute error using the PRD contracts
**And** abandoned or incomplete records are excluded and reported as specified.

**Given** workload and decision evidence exists
**When** KPI-5 and KPI-6 are calculated
**Then** workload balance is the population standard deviation of assigned workload hours across available Technicians at window end
**And** recommendation acceptance is accepted recommendations divided by decisions containing a recommendation.

**Given** stage timing and completed outcome evidence exists
**When** KPI-7 and KPI-8 are calculated
**Then** latency reports median/p95 for the total deterministic path and each stage
**And** First-Time Fix Rate uses only completed outcomes where First-Time Fix is known.

**Given** KPI results are persisted
**When** they are queried later
**Then** versioned `kpi_events` reproduce the same results from their linked evidence
**And** queries remain side-effect free.

**Given** the KPI panel is opened
**When** a keyboard or assistive-technology user inspects values
**Then** definitions, windows, unavailable states, numerators, denominators, exclusions, and units are accessible as text
**And** charts or color treatments have equivalent labels and tabular evidence.

### Story 4.2: Replay and Reset Academic Scenarios Safely

**Requirements:** FR20; NFR2, NFR3, NFR7

As Rossy,
I want to replay stored scenarios and reset the simulator to a known fixture,
So that classroom demonstrations can be repeated without contaminating evidence.

**Acceptance Criteria:**

**Given** a retrievable Dispatch Run
**When** replay is requested by identifier and Memory Mode
**Then** a new run is created with `source_run_id`, copied immutable inputs, configuration, and an isolated Memory read snapshot
**And** the original run and evidence remain unchanged.

**Given** an identical replay request and `Idempotency-Key`
**When** it is retried
**Then** the original replay response is returned
**And** a different request hash with the same key returns `409 CONFLICT`.

**Given** a simulation or replay completes
**When** its `/api/v1` resource is returned
**Then** the response includes run state, eligibility evidence, score breakdown, confidence, warnings, alternatives, and chronological transitions
**And** it validates against generated versioned OpenAPI schemas.

**Given** active runs exist
**When** reset is requested
**Then** reset is rejected with a stable conflict error
**And** no tables or exported evidence are modified.

**Given** no active runs exist and reset is confirmed
**When** the command executes
**Then** it backs up SQLite, clears operational, run-evidence, idempotency, episodic, and learning tables, and reloads the selected fixture in one transaction
**And** exported reports are never deleted.

**Given** fixture reload or reset fails
**When** the transaction rolls back
**Then** the pre-reset database remains recoverable
**And** replay/reset integration and contract tests prove isolation, provenance, idempotency, backup, rollback, and export preservation.

### Story 4.3: Generate and Export the Academic Evidence Package

**Requirements:** FR21; NFR4, NFR6, NFR7

As Rossy,
I want a reproducible report for selected academic scenarios,
So that I can submit defensible evidence of behavior, limitations, and architectural control.

**Acceptance Criteria:**

**Given** selected scenario and paired comparison identifiers
**When** the evidence package is generated
**Then** it identifies configuration and runtime versions, scenario inputs, linked run IDs, results, Memory Modes, comparison differences, Hard Constraint invariants, KPI values, and benchmark metadata
**And** every result links to retrievable structured evidence.

**Given** the report describes system learning
**When** limitations and conclusions are rendered
**Then** it explicitly states that data is synthetic and learning is statistical aggregation rather than model fine-tuning
**And** it documents rejected alternatives, known risks, unresolved assumptions, and limits on real-world efficacy claims.

**Given** a KPI or expected outcome lacks sufficient evidence
**When** the report is generated
**Then** it marks the result unavailable or incomplete
**And** it does not replace missing evidence with zero, fabricated values, or unsupported claims.

**Given** the same selected runs and configuration are reported repeatedly
**When** generation runs without changed source evidence
**Then** the semantic report content and machine-readable manifest are reproducible
**And** generated files remain outside destructive reset scope.

**Given** the UJ-3 browser flow is executed
**When** Rossy compares Memory modes, inspects states and KPIs, and exports the evidence package
**Then** all displayed and exported claims resolve to the same persisted contracts
**And** keyboard-only operation, visible focus, semantic labels, and textual status alternatives pass the named accessibility scope.

### Story 4.4: Verify the Course-Ready System and Complete API Cutover

**Requirements:** FR1–FR21 (release verification); NFR1–NFR7

As Rossy,
I want the complete system verified through its canonical API before legacy removal,
So that the course delivery is reproducible and no working journey is lost during cutover.

**Acceptance Criteria:**

**Given** the final automated academic suite runs
**When** UJ-1 through UJ-3, hard-rule, uncertainty, learning, Memory comparison, KPI, replay, report, failure, and recovery scenarios execute exclusively through `/api/v1`
**Then** all FR1 through FR21, NFR1 through NFR7, and SM-1 through SM-10 have traceable passing or explicitly unavailable evidence
**And** the temporary legacy routes and `server.py` may be removed only after their journey and error smoke-test gate passes.

**Given** any required journey or error scenario still depends on a legacy route
**When** the cutover gate is evaluated
**Then** legacy adapters and `server.py` remain available
**And** the failing canonical path is reported without deleting compatibility behavior.

**Given** every canonical journey and error test passes
**When** legacy surfaces are removed
**Then** no duplicate business logic or obsolete route remains
**And** the local launch, exported evidence, backups, and reproducible fixtures continue to pass their verification suites.

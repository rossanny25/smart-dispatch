---
project_name: 'smart-dispatch-ia-spec-v2'
user_name: 'Rossy'
date: '2026-07-27'
sections_completed: ['technology_stack', 'language_specific_rules', 'framework_specific_rules', 'testing_rules', 'code_quality_rules', 'development_workflow_rules', 'critical_dont_miss_rules']
existing_patterns_found: 7
status: 'complete'
rule_count: 69
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

### Brownfield Baseline

- Python 3.12 standard-library `http.server` runtime in `server.py`
- Static vanilla HTML, CSS, and JavaScript frontend
- Same-origin JSON requests to legacy `/api/*` routes
- Module-level Python operational data and `data/learning_store.json` persistence
- No declared package manager, dependency lock, automated tests, build process, or deployment manifest

### Binding Target Stack

- Python 3.12.10
- uv 0.11.16 with authoritative `pyproject.toml` and `uv.lock`
- FastAPI 0.138.2 and Uvicorn 0.46.0
- Pydantic 2.13.4
- SQLAlchemy Core 2.0.51 and Alembic 1.18.5
- SQLite 3.35.0 capability floor
- Vanilla HTML/CSS/JavaScript with an ECMAScript 2023 baseline
- pytest 9.1.1, coverage.py 7.13.5, and Playwright for Python 1.60.0

## Critical Implementation Rules

### Language-Specific Rules

- Use Python 3.12.10 syntax and standard-library behavior; do not introduce compatibility branches for older Python versions.
- Use `snake_case` for Python modules, functions, variables, API JSON fields, and database identifiers; use singular `PascalCase` for domain types.
- Represent domain identifiers as opaque UUID values and retain legacy string identifiers only through explicit migration/provenance fields.
- Use timezone-aware UTC internally and serialize API timestamps as ISO 8601 values ending in `Z`; never persist naive timestamps.
- Use `Decimal` for score, confidence, penalty, and KPI arithmetic. Do not use binary floating-point or intermediate presentation rounding.
- Model boundary data with versioned Pydantic contracts and `extra="forbid"`; validation failure must produce a typed error and prevent mutation or State Transition.
- Keep domain policies pure: no mutable module globals, clock reads, database calls, network calls, or provider SDK access.
- Raise typed domain/application errors and map them once in the HTTP adapter; never swallow exceptions or expose stack traces through API responses.
- Keep browser code at the ECMAScript 2023 baseline and dependency-free unless the Architecture Spine is formally changed.
- Browser JavaScript may render API resources and submit commands only; it must not calculate eligibility, scores, confidence, learning, KPIs, or authoritative state.
- Insert untrusted API values with `textContent` or equivalent safe DOM APIs; never interpolate them into executable HTML.

### Framework-Specific Rules

- Preserve the hexagonal dependency direction: FastAPI routes and persistence adapters call application ports; domain packages must not import FastAPI, Pydantic, SQLAlchemy, SQLite, browser code, or model-provider SDKs.
- Use `app/main.py` only as the composition root. Business behavior belongs in application use cases or pure domain policies, never in route handlers.
- Keep canonical routes under `/api/v1`; use the shared success/error envelopes and generated OpenAPI contracts as the API authority.
- Require a route-scoped `Idempotency-Key` for every external mutation. The same key and request hash returns the original response; a different hash returns `409 CONFLICT`.
- Execute every mutating application command through one Unit of Work. Repositories must not commit independently.
- Persist each State Machine advancement in its own transaction and protect the run revision with compare-and-swap.
- Run one FastAPI/Uvicorn process and one worker against SQLite. Enable foreign keys, WAL mode, and the configured busy timeout on every connection.
- Run Alembic before serving. Schema-changing migration and destructive reset require a SQLite backup; migration failure is fail-closed.
- Build every calculation from immutable `run_snapshots`, never from mutable operational rows.
- Keep deterministic local Capture and Analyze adapters as the MVP default. An optional LLM adapter must satisfy the same Pydantic contract and record provider/model metadata.
- Serve vendored frontend assets from FastAPI on the same origin and bind to `127.0.0.1` by default.

### Testing Rules

- Mirror architecture boundaries under `tests/unit`, `tests/integration`, `tests/contract`, and `tests/browser`.
- Test domain policies as pure units with explicit clocks, snapshots, and configuration inputs; do not hide domain behavior behind database or HTTP mocks.
- Run repository and Unit of Work integration tests against real temporary SQLite databases with foreign keys, WAL behavior, migrations, rollback, and uniqueness constraints enabled.
- Validate every `/api/v1` response against generated OpenAPI contracts, including `413`, `415`, `422`, `409`, typed failures, idempotent retries, and `NO_FEASIBLE_CANDIDATES`.
- Use deterministic fixture identifiers, timestamps, Work Orders, Technician rosters, environment data, and configuration versions.
- In Memory on/off tests, paired fixtures may differ only by Memory Experiment Mode; assert identical Hard Constraint results.
- Add a failing regression test before every defect fix. Preserve explicit coverage for the legacy priority-5 `alerts.push(...)` failure.
- Test crash recovery and exactly-once behavior at every transaction boundary, especially stage commits, decisions, outcomes, Episodic Memory, and Semantic Pattern updates.
- Run browser smoke tests with Playwright 1.60.0 and its pinned Chrome-for-Testing build; tests must not depend on external network assets.
- Cover UJ-1 through UJ-3, keyboard operation, visible focus, semantic labels, textual status alternatives, recoverable errors, and stale-data/no-candidate paths.
- Benchmark 100 warm deterministic runs on the seeded dataset and record hardware, runtime, fixture, and configuration versions; p95 must satisfy NFR1.
- Treat SM-1 through SM-10 as testable evidence contracts, not narrative goals.

### Code Quality & Style Rules

- Follow the Architecture Spine structural seed: `app/api/v1`, `app/application`, bounded `app/domain/*`, `app/contracts`, `app/adapters`, `app/migrations`, `frontend`, `data/fixtures`, and boundary-mirrored tests.
- Keep one bounded responsibility per module. Do not recreate the current all-in-one `server.py` structure inside a new file.
- Use imperative names for commands, past-tense names for events, plural `snake_case` database tables, and explicit foreign keys.
- Keep configuration immutable and versioned in persistence. Environment variables may select paths or secrets only; they must not silently change business formulas.
- Emit structured JSON logs with `request_id`, `run_id`, `stage`, `duration_ms`, and `status`; never log raw addresses, complete incident narratives, or exact GPS.
- Comment non-obvious invariants and trade-offs, especially where code enforces an Architecture Decision; do not add comments that merely restate syntax.
- Keep migrations small, ordered, reversible where practical, and paired with integration tests and backups for schema-changing operations.
- Avoid broad frontend rewrites. Preserve vanilla JavaScript and existing visual structure unless a story explicitly requires a focused change.
- Do not introduce a formatter, linter, frontend framework, ORM model layer, or new infrastructure merely by preference; such changes require an explicit architecture decision.

### Development Workflow Rules

- Implement one approved sprint story at a time and use only completed earlier stories as dependencies.
- Before coding, read the active story, `project-context.md`, the PRD requirement references, and the relevant Architecture Decisions.
- Follow test-first development for behavior and defects: failing test, minimal implementation, then refactor with the full affected suite green.
- Keep each story internally complete across domain, application, contracts, persistence, API, UI, migration, and tests only where that story requires them.
- Update generated OpenAPI, Alembic revisions, fixtures, configuration versions, and evidence contracts in the same story as the behavior they govern.
- Use `uv sync --frozen` for provisioning and `uv run smart-dispatch` for the canonical local launch once the target runtime exists.
- Do not overwrite or discard unrelated workspace changes. Limit edits to the active story and preserve brownfield behavior through the compatibility adapter.
- Run boundary-relevant tests during development and the complete required suite before marking a story ready for review.
- After development, run BMAD code review; unresolved findings return to development before the next story begins.
- Remove legacy routes or `server.py` only after all UJ-1 through UJ-3 journey and error smoke tests pass exclusively through `/api/v1`.
- No branch naming, commit format, pull-request, CI/CD, or deployment convention is currently authoritative; do not invent one inside implementation work.

### Critical Don't-Miss Rules

- Only `DispatchOrchestrator` may advance a run. Agent stages, routes, repositories, and browser code must never transition state directly.
- Preserve stage semantics: CAPTURE normalizes; ANALYZE derives with provenance; PLAN applies all Hard Constraints and then scores eligible candidates; EVALUATE adds validation, confidence, warnings, and explanations without changing eligibility or rank.
- Availability, all certifications, shift, maximum workday, four-hour driving limit, and required EPP are Hard Constraints. Priority and Memory can never bypass them.
- The old priority-5 overtime exception is superseded. Distance over 50 km is always a soft score penalty and never an eligibility rule.
- Objective Score and Recommendation Confidence are independent values with separate formulas and evidence. A high score may correctly have low confidence.
- Apply calculation registry `v1` exactly and use the immutable run snapshot. Do not invent alternate normalization, tie-break, freshness, promotion, decay, or KPI formulas.
- `NO_FEASIBLE_CANDIDATES` contains all rejection evidence but no recommendation, candidate score for ineligible Technicians, or Recommendation Confidence.
- Record Decision and Outcome as separate atomic commands. Never keep a transaction open while field service occurs.
- Append Episodic Memory and update the learning ledger, Semantic Pattern, and completion transition atomically during LEARN.
- One episode cannot activate a Semantic Pattern. Apply the configured minimum evidence, contradiction penalty, confidence thresholds, and 90-day decay; Memory never participates in eligibility.
- Resume from the last committed state. Never recompute committed stages or apply the same outcome/policy version twice.
- Replay creates a new linked run with copied inputs and an isolated Memory read snapshot; it never mutates the source run.
- Reset must reject active runs, back up SQLite, reload one fixture transactionally, and never delete exported reports.
- Bind locally, use same-origin vendored assets, enforce the 1 MiB JSON limit, and never expose raw addresses or exact GPS through logs or long-term Semantic Patterns.
- Explanations must be reconstructable from structured stored evidence. Never store, render, or claim private chain-of-thought.

---

## Usage Guidelines

**For AI Agents:**

- Read this file before implementing any code.
- Follow all rules exactly; when uncertain, prefer the more restrictive interpretation.
- Update this file only when an approved architecture or implementation pattern changes.

**For Humans:**

- Keep this file focused on non-obvious implementation constraints.
- Update it when the binding stack or Architecture Spine changes.
- Review it periodically and remove rules that become obsolete or universally enforced by tooling.

Last Updated: 2026-07-27

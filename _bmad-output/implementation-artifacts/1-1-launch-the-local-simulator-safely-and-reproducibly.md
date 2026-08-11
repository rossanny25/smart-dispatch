---
baseline_commit: NO_VCS
---

# Story 1.1: Launch the Local Simulator Safely and Reproducibly

Status: done

## Story

As Rossy or a course evaluator,
I want to launch the local simulator from a reproducible environment,
so that the academic demonstration starts consistently without risking existing evidence.

## Requirements Traceability

- **Functional:** FR20, runtime foundation only.
- **Non-functional:** NFR3 (fail-closed integrity). NFR5 is contextual: this story stays inside local development, so non-local HTTPS and long-term Semantic Pattern location handling remain out of scope.
- **Architecture:** AD-13, AD-15, AD-22, AD-26; structural constraints from AD-1 and AD-19.
- **Epic requirements registry:** AR13, AR22, AR24, and AR26. AR22 calculation behavior and AR26 future API/KPI behavior are guardrails only; this story does not implement scoring, replay, or KPI capabilities.

## Acceptance Criteria

1. **Reproducible clean launch**
   - **Given** a clean project checkout with Python 3.12.10 and uv 0.11.16 available
   - **When** `uv sync --frozen` and `uv run smart-dispatch` are executed
   - **Then** the application starts through FastAPI 0.138.2 and Uvicorn 0.46.0 on `127.0.0.1:8000` with exactly one worker
   - **And** `.python-version`, `pyproject.toml`, and `uv.lock` define the approved runtime and exact dependency graph
   - **And** importing `app.main` alone does not migrate, create files, open the production database, or bind a socket.

2. **SQLite operating envelope**
   - **Given** the application starts with a valid file-backed SQLite database
   - **When** any application database connection is opened
   - **Then** `PRAGMA foreign_keys` is `1`, `journal_mode` is `wal`, and `busy_timeout` is the single documented nonzero default of 5000 milliseconds
   - **And** the runtime refuses startup when the SQLite library version is lower than 3.35.0
   - **And** the default database is `data/smart_dispatch.db`.

3. **Runtime data is excluded from source control**
   - **Given** the runtime creates SQLite or test artifacts
   - **When** repository-ignore rules are evaluated
   - **Then** `data/smart_dispatch.db`, its `-wal` and `-shm` files, database backups, temporary test databases, `.venv`, Python caches, and test caches are ignored
   - **And** the tracked `data/learning_store.json` seed/evidence file is not ignored or deleted.

4. **Migration-before-serve and recoverable backup**
   - **Given** an existing SQLite database has one or more pending Alembic revisions
   - **When** the canonical launcher starts
   - **Then** it creates a collision-safe pre-upgrade backup through SQLite's backup API before applying any pending revision
   - **And** the backup passes `PRAGMA integrity_check`, can be opened independently, and contains the pre-migration schema and data
   - **And** Alembic reaches the configured head before Uvicorn begins accepting requests.

5. **Fail-closed migration behavior**
   - **Given** a migration or backup verification fails
   - **When** the launcher handles the failure
   - **Then** Uvicorn is never started and the process exits nonzero
   - **And** the error identifies the failed operation or revision without exposing raw stored data, SQL contents, or an unnecessary user-home path
   - **And** unrelated pre-existing database schema and rows remain logically unchanged
   - **And** if the failed revision can leave the source database modified, the launcher restores the verified pre-upgrade backup before returning failure.

6. **Thin legacy entry point**
   - **Given** `server.py` is used during the brownfield migration period
   - **When** it launches the application
   - **Then** it calls the same canonical launcher/composition root used by the `smart-dispatch` console script
   - **And** it does not contain a second implementation of dispatch business rules
   - **And** the existing `/api/*` behavior is mechanically relocated once into a named temporary FastAPI compatibility adapter, without duplicating or redesigning its contracts or rules
   - **And** characterization smoke tests prove the current technicians, orders, memory, reset, simulate, and confirm routes remain reachable for the existing SPA
   - **And** the current legacy source and `data/learning_store.json` are preserved for the later Story 1.10 semantic migration.

7. **Minimal initial schema**
   - **Given** the Story 1.1 production migrations are at head
   - **When** SQLite schema objects are listed
   - **Then** only Alembic's version table, justified runtime metadata if explicitly required, and SQLite internal objects exist
   - **And** no Work Order, Technician, Dispatch Run, candidate, decision, outcome, Episodic Memory, Semantic Pattern, KPI, replay, idempotency, or other future-domain table exists.

8. **Existing evidence is byte-preserved**
   - **Given** `data/learning_store.json` exists before startup
   - **When** clean startup, existing-database startup, migration success, migration failure, and focused tests run
   - **Then** the file's bytes and checksum remain unchanged
   - **And** this story never imports, reseeds, rewrites, truncates, or deletes it.

9. **Local-only and predictable process behavior**
   - **Given** the canonical launcher is invoked
   - **When** the process binds successfully
   - **Then** it listens only on IPv4 loopback at port 8000, does not enable wildcard CORS, and serves the existing root/static application from the same origin
   - **And** essential startup does not require an external network service or optional LLM
   - **And** local `index.html`, `index.css`, and `main.js` return successfully without claiming that later canonical journeys or external CDN resources are complete
   - **And** a second launch while the port is occupied fails clearly rather than switching host, port, or worker count.

10. **Reproducible verification evidence**
    - **Given** the Story 1.1 test suite runs against temporary file-backed SQLite databases
    - **When** clean startup, existing database, pending migration, backup/restore, migration failure, per-connection PRAGMAs, occupied port, legacy entry point, and evidence-preservation cases execute
    - **Then** all cases pass reproducibly
    - **And** the tests prove loopback-only binding, one worker, pre-serve migration ordering, valid backup restoration, fail-closed startup, minimal schema, and unchanged `learning_store.json`.

## Tasks / Subtasks

- [x] 1. Establish the pinned Python project and exact dependency graph (AC: 1, 10)
  - [x] Add `.python-version` with `3.12.10`.
  - [x] Add `pyproject.toml` with an exact Python constraint, the `smart-dispatch` console script, and the architecture-pinned runtime/test dependencies.
  - [x] Generate and commit `uv.lock`; verify `uv sync --frozen` succeeds from a clean environment.
  - [x] Do not introduce a formatter, linter, ORM model layer, frontend framework, container, CI/CD system, or unrelated dependency.

- [x] 2. Create an import-safe FastAPI composition root and canonical launcher (AC: 1, 5, 9)
  - [x] Create `app/main.py` as the composition root or app-factory surface only.
  - [x] Create a bounded runtime launcher that validates SQLite capability, performs backup/migration work, and only then invokes Uvicorn.
  - [x] Pin host `127.0.0.1`, port `8000`, and one worker in the launcher; do not provide a non-loopback fallback.
  - [x] Serve the existing root document and local static files from FastAPI without moving business calculations into the HTTP layer.
  - [x] Do not add a domain API merely to simplify startup testing; use the root/static response as the readiness request unless a runtime-only health route is explicitly justified and tested as side-effect free.

- [x] 3. Add the SQLite connection foundation (AC: 2, 7, 10)
  - [x] Add the persistence adapter/configuration module under `app/adapters/persistence`.
  - [x] Default to `data/smart_dispatch.db`; permit path injection only for tests/local data selection.
  - [x] Resolve the default DB, backup, migration, and frontend paths from a stable project/config location rather than the caller's arbitrary working directory.
  - [x] Apply and verify foreign keys, WAL, and the Story 1.1 `[ASSUMPTION]` default of 5000 ms busy timeout on every connection; keep it named, documented, and covered by a focused test.
  - [x] Validate `sqlite3.sqlite_version >= 3.35.0` before migration or serving.
  - [x] Keep all domain repository interfaces, models, and tables out of this story.

- [x] 4. Add Alembic with a minimal production baseline (AC: 4, 5, 7)
  - [x] Add `alembic.ini`, an environment wired to the configured database path, and the migration package.
  - [x] Add the smallest initial revision needed to establish the migration baseline; do not create placeholder domain tables.
  - [x] Ensure migration configuration is callable from the launcher and test harness without import-time side effects.
  - [x] Use test-only revisions/fixtures to exercise real schema changes, backup, rollback/failure, and restore behavior.

- [x] 5. Implement and verify safe pre-migration backup (AC: 4, 5, 8)
  - [x] For an existing database with pending revisions, conservatively back up before upgrade even when a revision's SQL cannot be classified reliably.
  - [x] Use SQLite's online backup API rather than filesystem copy so WAL state is captured safely.
  - [x] Use a UTC, collision-safe name under an ignored backup directory and never overwrite an earlier backup.
  - [x] Run `PRAGMA integrity_check` on the backup before applying migrations.
  - [x] On any failure, leave the source DB/evidence recoverable and prevent server startup.

- [x] 6. Convert `server.py` into the compatibility launcher without stealing Story 1.10 (AC: 6, 8)
  - [x] Make `python3 server.py` delegate to the canonical runtime launcher.
  - [x] Move the existing legacy route implementation exactly once from `server.py` into `app/adapters/legacy/compatibility.py` (or an equivalently named temporary adapter) and mount it in the canonical FastAPI app.
  - [x] Preserve the existing `/api/technicians`, `/api/orders`, `/api/memory/learning`, `/api/reset`, `/api/dispatch/simulate`, and `/api/dispatch/confirm` request/response behavior through characterization tests; do not create a second copy.
  - [x] Do not migrate JSON learning records, create canonical dispatch use cases, correct scoring/eligibility behavior, or claim the priority-5 regression is fixed in this story.
  - [x] Mark this compatibility adapter as a temporary brownfield exception. Story 1.10 owns converting it into thin `/api/*` translation over canonical application use cases, and Story 1.11 owns the Epic 1 cutover gate.

- [x] 7. Protect runtime artifacts and update launch documentation (AC: 1, 3, 8, 9)
  - [x] Add a root `.gitignore` with database, WAL/SHM, backup, environment, cache, and test-artifact patterns.
  - [x] Update `README.md` and `docs/development-guide.md` with prerequisites, exact frozen install/run commands, canonical and compatibility entry points, local URL, database/backup locations, and failure behavior.
  - [x] State that HTTPS/authentication are required before non-local use and are intentionally out of MVP scope.
  - [x] State that Playwright browser binaries are not installed or exercised by this story.

- [x] 8. Add focused unit and real-SQLite integration tests (AC: 1-10)
  - [x] Test metadata pins, console-script wiring, import safety, and explicit Uvicorn host/port/worker arguments.
  - [x] Test every independently opened connection for required PRAGMAs, foreign-key rejection, bounded lock contention, and SQLite capability floor.
  - [x] Test fresh DB migration and the exact allowed production schema-object list.
  - [x] Test an existing DB with sentinel schema/data through backup, migration, integrity check, restore, and failure paths.
  - [x] Add `test_failed_migration_restores_or_preserves_sentinel_and_never_starts_uvicorn` as mandatory evidence for AC 5 and AC 10.
  - [x] Add process-level `test_canonical_and_server_entrypoints_use_same_app_and_keep_legacy_routes` as mandatory evidence for AC 6 and AC 10.
  - [x] Spawn the real canonical command, issue a local HTTP request, shut down cleanly, and test occupied-port failure.
  - [x] Hash `data/learning_store.json` before and after all startup/failure cases.

### Review Findings

- [x] [Review][Patch] Protect `data/learning_store.json` with a separate ignored runtime working copy — Decision: read the tracked evidence as the initial seed, but persist all compatibility-route changes to a distinct runtime file so the original remains byte-preserved [app/adapters/legacy/compatibility.py:17,128-197,460-537]
- [x] [Review][Patch] Recover a failed first migration instead of leaving a poisoned fresh database [app/startup.py:37-60]
- [x] [Review][Patch] Serialize migration preparation across concurrent launchers so a stale backup cannot revert another process [app/startup.py:37-52]
- [x] [Review][Patch] Restore migration state when interruption uses `KeyboardInterrupt` or `SystemExit` [app/startup.py:40-60]
- [x] [Review][Patch] Apply and verify the SQLite connection policy on backup, integrity-check, and restore connections [app/adapters/persistence/backup.py:18-74]
- [x] [Review][Patch] Read back and fail closed when required PRAGMAs are not effective [app/adapters/persistence/database.py:38-48]
- [x] [Review][Patch] Preserve the failed startup operation or revision in the sanitized error [app/startup.py:49-60]
- [x] [Review][Patch] Construct SQLite URLs and read-only URIs safely for filenames containing URL metacharacters [app/adapters/persistence/database.py:51-60]
- [x] [Review][Patch] Add real pending-success and failing-Alembic migration fixtures with backup, ordering, restore, and evidence checks [tests/integration/test_startup_safety.py:59-126]
- [x] [Review][Patch] Verify the complete allowed `sqlite_schema` object set, not only table names [tests/integration/test_migrations.py:20-23]
- [x] [Review][Patch] Exercise all required legacy routes through both real process entry points [tests/integration/test_launch_process.py:42-86]
- [x] [Review][Patch] Prove PRAGMAs on distinct physical SQLite connections rather than pooled reuse [tests/integration/test_database_runtime.py:22-37]
- [x] [Review][Patch] Send an `Origin` header so the wildcard-CORS regression assertion is meaningful [tests/unit/test_runtime.py:69-82]
- [x] [Review][Patch] Ignore injected runtime database names and their WAL/SHM sidecars [`.gitignore`:8-12]
- [x] [Review][Patch] Make process readiness prove that the response came from the spawned launcher [tests/integration/test_launch_process.py:15-30]
- [x] [Review][Defer] Make legacy confirmation persistence atomic and roll back in-memory mutations on write failure [app/adapters/legacy/compatibility.py:473-537] — deferred, pre-existing
- [x] [Review][Defer] Validate malformed legacy simulation environments and learning-store structures instead of returning HTTP 500 [app/adapters/legacy/compatibility.py:186-190,297-341,405-417] — deferred, pre-existing
- [x] [Review][Defer] Replace collision-prone four-digit epoch order identifiers [app/adapters/legacy/compatibility.py:277-293] — deferred, pre-existing

## Dev Notes

### Non-Destructive Invariants

- `data/learning_store.json` is the only existing persistent brownfield evidence. Treat it as immutable input in Story 1.1.
- Never delete or recreate an existing SQLite database after a migration error.
- Never use raw file copy as the database-backup mechanism.
- Importing application modules must have no file, database, migration, network, or socket side effects.
- Uvicorn must not start until backup verification and Alembic upgrade complete.
- The runtime DB, WAL/SHM files, backups, test databases, and environments must remain untracked.

### Scope Boundary

**In scope:** pinned runtime metadata; exact dependency lock; FastAPI composition root; canonical/compatibility launch; mechanical relocation and mounting of the current legacy HTTP behavior as one temporary compatibility adapter; SQLite connection configuration; Alembic infrastructure; minimal migration baseline; safe backup; root/static reachability; launch documentation; focused tests.

**Out of scope:** new or redesigned Work Order and dispatch behavior; canonical domain tables; State Machine; corrected eligibility/scoring/confidence; idempotency; replay/reset redesign; JSON learning migration; the priority-5 rule correction; `/api/v1` business cutover; UI redesign; production HTTPS/auth; multi-process deployment; browser-flow testing.

FR20 is cited only as the runtime foundation. Full simulation/replay API behavior remains in later stories.

### Brownfield State and Preservation

- Current `server.py` combines static serving, legacy `/api/*` routes, module-level operational data, scoring/evaluation logic, and JSON learning writes.
- It currently binds all interfaces and enables wildcard CORS. The canonical launcher must replace those startup defaults with loopback-only, same-origin behavior.
- The SPA currently calls legacy routes from `frontend/main.js`; preserve them through the temporary mounted compatibility adapter, but do not represent them as canonically migrated.
- Preserve `frontend/index.html`, `frontend/index.css`, `frontend/main.js`, prompts, specs, and the JSON store unless a narrowly necessary launcher/static-serving change is documented.
- The external font/icon references in `frontend/index.html` are a known offline-UI gap. Do not redesign or vendor the UI here; Story 1.9 owns browser/accessibility work.

### Architecture Compliance

- Dependencies point inward: FastAPI and persistence code are adapters; `app/main.py` is composition only.
- Do not place migration, backup, SQLite, or Uvicorn work in domain packages.
- Use SQLAlchemy Core, not an ORM model layer.
- Use one FastAPI/Uvicorn process and one worker.
- Use Alembic before serving and SQLite's backup API before any pending upgrade of an existing DB.
- Apply SQLite connection PRAGMAs on every connection.
- Keep exceptions typed/sanitized at the launcher boundary; do not swallow errors.
- Do not invent future tables, routes, contracts, calculations, or configuration registries.
- The temporary legacy adapter may preserve existing brownfield logic only; it is an explicitly tracked exception and must not become a second implementation beside another active legacy copy.

### Library and Framework Requirements

| Technology | Required version | Story use |
| --- | --- | --- |
| Python | 3.12.10 | Runtime |
| uv | 0.11.16 | Provisioning and exact lock |
| FastAPI | 0.138.2 | Composition root and local HTTP/static surface |
| Uvicorn | 0.46.0 | Loopback-only single-worker ASGI process |
| Pydantic | 2.13.4 | Available for future strict contracts; do not invent domain models |
| SQLAlchemy Core | 2.0.51 | Connection/transaction foundation |
| Alembic | 1.18.5 | Migration baseline and pre-serve upgrades |
| SQLite | CPython bundled, >=3.35.0 | Runtime persistence |
| pytest | 9.1.1 | Unit/integration/process tests |
| coverage.py | 7.13.5 | Test evidence |
| Playwright Python | 1.60.0 | Pin now; browser installation/tests remain later |

The Architecture Spine is authoritative even when newer compatible releases exist. Do not upgrade a pin while implementing this story.

### File Structure Requirements

Expected new files/directories:

```text
.python-version
pyproject.toml
uv.lock
.gitignore
alembic.ini
app/
  __init__.py
  main.py
  runtime.py
  adapters/
    __init__.py
    legacy/
      __init__.py
      compatibility.py
    persistence/
      __init__.py
      database.py
      backup.py
  migrations/
    env.py
    script.py.mako
    versions/
      <initial_runtime_revision>.py
tests/
  unit/
    test_runtime.py
  integration/
    test_database_runtime.py
    test_migrations.py
    test_launch_process.py
```

Expected updates:

- `server.py` — thin compatibility entry point.
- `README.md` — accurate reproducible setup.
- `docs/development-guide.md` — exact install/run/test and recovery guidance.

Do not create empty future domain packages merely to mirror the complete structural seed.

### Testing Requirements

- Use test-first development: failing test, minimal implementation, refactor.
- Use real temporary file-backed SQLite databases for persistence/migration behavior; do not substitute `:memory:` for WAL/backup/concurrency tests.
- Assert behavior, not merely that files exist: restore backups, verify sentinel data, test FK failure and lock timeout, and prove no listener starts after migration failure.
- Keep production migrations minimal; use test-only migration fixtures for destructive/failure scenarios.
- Tests must not depend on external network assets, model providers, or user-global state.
- Root/static smoke tests verify only that the three local files are served; they must not claim UJ-1 completion, fetch CDN assets, or substitute for Story 1.9 browser tests.
- Preserve deterministic paths and clean up only test-owned temporary files.

### Latest Technical Information

- Python 3.12.10 is an intentionally frozen course runtime even though later 3.12 security releases exist.
- uv 0.11.16, FastAPI 0.138.2, Uvicorn 0.46.0, Pydantic 2.13.4, SQLAlchemy 2.0.51, Alembic 1.18.5, pytest 9.1.1, coverage.py 7.13.5, and Playwright 1.60.0 are published releases.
- Newer versions of several packages exist as of 2026-07-27; reproducibility takes precedence over opportunistic upgrades.
- Use documented APIs from the pinned lines. In particular, use Python/SQLite's backup API and Alembic's programmatic upgrade path rather than shelling out or copying live database files.

Official references:

- Python 3.12.10: https://www.python.org/downloads/release/python-31210/
- uv 0.11.16: https://github.com/astral-sh/uv/releases/tag/0.11.16
- FastAPI 0.138.2: https://pypi.org/project/fastapi/0.138.2/
- Uvicorn 0.46.0: https://pypi.org/project/uvicorn/0.46.0/
- Pydantic 2.13.4: https://pypi.org/project/pydantic/2.13.4/
- SQLAlchemy 2.0.51: https://pypi.org/project/SQLAlchemy/2.0.51/
- Alembic 1.18.5: https://pypi.org/project/alembic/1.18.5/
- pytest 9.1.1: https://pypi.org/project/pytest/9.1.1/
- coverage.py 7.13.5: https://pypi.org/project/coverage/7.13.5/
- Playwright 1.60.0: https://pypi.org/project/playwright/1.60.0/

### Project Structure Notes

- No previous story implementation exists; Story 1.1 establishes the first target-stack patterns.
- The workspace currently has no root `.gitignore`, project metadata, lock file, migration framework, or automated tests.
- Git metadata was not detected in the project root, so ignore patterns must be validated directly and with `git check-ignore` only when Git is available.
- Canonical paths must remain stable when the console script is invoked outside the repository root; tests may override data paths, but production defaults must not follow an arbitrary current working directory.
- Keep the implementation incremental: runtime first, future tables and business behavior only when their owning stories begin.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.1]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — FR20, NFR3, NFR5, Constraints, Non-Goals]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/addendum.md` — Brownfield Baseline, SQLite]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-1, AD-13, AD-15, AD-19, AD-22, AD-26, Stack, Structural Seed]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — Deployment and Operations, Brownfield Migration]
- [Source: `_bmad-output/project-context.md` — Technology Stack, Framework Rules, Testing Rules, Development Workflow]
- [Source: `docs/index.md` and `docs/architecture.md` — current brownfield runtime]
- [Source: `docs/development-guide.md` — obsolete current launch instructions]
- [Source: `server.py` — current entry point, legacy routes, all-interface bind, JSON persistence]
- [Source: `frontend/main.js` — current legacy API calls]

## Definition of Done

- [x] Every acceptance criterion has automated evidence or a documented, reproducible inspection command.
- [x] `uv sync --frozen` succeeds from a clean checkout.
- [x] `uv run smart-dispatch` migrates before serving and responds on `127.0.0.1:8000`.
- [x] The focused Story 1.1 unit/integration/process suite passes.
- [x] The dependency lock, allowed schema objects, required PRAGMAs, SQLite version, backup integrity/restore, and failure/no-listener behaviors are captured in test output.
- [x] `data/learning_store.json` has the same checksum before and after verification.
- [x] Runtime artifacts are ignored and no future-domain table or API behavior was introduced.
- [x] README and development guidance match the implemented commands and limitations.
- [x] Story completion notes list exact commands, exit results, and every created/modified file.

## Dev Agent Record

### Agent Model Used

GPT-5.4

### Implementation Plan

- Establish the exact uv/Python dependency graph first.
- Add the import-safe FastAPI composition root and launch boundary.
- Add SQLite connection, migration, backup, and restoration services.
- Relocate the legacy HTTP behavior once into a temporary FastAPI adapter.
- Finish with documentation, process-level verification, and the complete regression suite.

### Debug Log References

- `uv sync --frozen` — 27 locked packages checked successfully.
- `uv run pytest -q` — 34 tests passed after code-review corrections.
- `uv lock --check` — lock resolved and current.
- `uv run python -m compileall -q app server.py tests` — passed.
- Manual `uv run smart-dispatch` — root and `/api/technicians` returned HTTP 200 on `127.0.0.1:8000`; clean shutdown passed.
- `data/learning_store.json` SHA-256 remained `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created.
- Task 1 complete: Python 3.12.10, uv build metadata, exact runtime/dev dependencies, and `uv.lock` established; `uv sync --frozen` and three metadata tests pass.
- Added an import-safe FastAPI composition root and fail-closed loopback-only Uvicorn launcher.
- Added per-connection SQLite foreign keys, WAL, 5000 ms busy timeout, and SQLite capability validation.
- Added a minimal Alembic baseline with no future domain tables.
- Added verified online backup, integrity checking, failure restoration, and pre-serve migration ordering.
- Relocated legacy HTTP behavior once into a temporary FastAPI adapter; `server.py` now delegates to the canonical launcher.
- Added repository hygiene and reproducible developer documentation.
- Added 34 unit/integration/process tests covering all ten acceptance criteria; complete suite and manual launch verification pass.
- Code review corrections protect the tracked learning evidence through an ignored runtime working copy, validate SQLite policy on every connection, serialize concurrent migration startup, recover first-run and interrupted failures, and preserve actionable operation names in sanitized errors.
- Added real test-only Alembic success/failure revisions, complete `sqlite_schema` verification, distinct physical-connection checks, meaningful CORS requests, and full real-process legacy-route characterization for both launchers.

### File List

- `.gitignore`
- `.python-version`
- `README.md`
- `alembic.ini`
- `app/__init__.py`
- `app/adapters/__init__.py`
- `app/adapters/legacy/__init__.py`
- `app/adapters/legacy/compatibility.py`
- `app/adapters/persistence/__init__.py`
- `app/adapters/persistence/backup.py`
- `app/adapters/persistence/database.py`
- `app/main.py`
- `app/migrations/__init__.py`
- `app/migrations/env.py`
- `app/migrations/runtime.py`
- `app/migrations/script.py.mako`
- `app/migrations/versions/20260727_0001_runtime_baseline.py`
- `app/runtime.py`
- `app/startup.py`
- `docs/development-guide.md`
- `_bmad-output/implementation-artifacts/1-1-launch-the-local-simulator-safely-and-reproducibly.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `server.py`
- `tests/asgi_client.py`
- `tests/fixtures/migrations/failure/20260728_0002_review_failure.py`
- `tests/fixtures/migrations/success/20260728_0002_review_success.py`
- `tests/integration/test_database_runtime.py`
- `tests/integration/test_launch_process.py`
- `tests/integration/test_legacy_compatibility.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_startup_safety.py`
- `tests/unit/test_project_metadata.py`
- `tests/unit/test_repository_hygiene.py`
- `tests/unit/test_runtime.py`
- `_bmad-output/implementation-artifacts/deferred-work.md`
- `uv.lock`

### Change Log

- 2026-07-27: Implemented Story 1.1 runtime, SQLite/Alembic safety, legacy compatibility, documentation, and complete automated verification.
- 2026-07-28: Applied all 15 code-review patches, expanded verification from 27 to 34 tests, and marked the story done.

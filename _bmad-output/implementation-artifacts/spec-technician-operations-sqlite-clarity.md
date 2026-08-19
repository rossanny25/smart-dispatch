---
title: 'Technician Operations SQLite And Decision Clarity'
type: 'feature'
created: '2026-08-18'
status: 'in-review'
review_loop_iteration: 0
baseline_commit: '762c44a'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/ai-project-status.md'
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent -- do not modify unless human renegotiates">

## Intent

**Problem:** The app still feels like a demo because service technicians are
loaded from JSON, cannot be edited in the product UI, their schedules are not
visible, invalid incident text is accepted too easily, and the semantic memory
panel does not explain what it learns or how it affects dispatch.

**Approach:** Move the legacy technician roster into SQLite-backed operational
storage, seed it from the existing JSON only when the database is empty, expose
admin-only technician create/edit controls, show schedules and decision criteria
in the technician and recommendation UI, and reject or explain low-information
service requests instead of silently processing nonsense.

## Boundaries & Constraints

**Always:** Preserve the current FastAPI/vanilla frontend deployment shape,
keep Render on free SQLite storage, keep legacy `/api/technicians` and
`/api/dispatch/*` working, protect technician writes for `admin` users only,
store structured fields such as certifications, PPE, GPS coordinates, and shift
as validated JSON/text in SQLite, and keep hard rules before scoring.

**Ask First:** Adding external map providers, email delivery, OAuth, a paid DB,
a frontend framework, or removing the seed JSON files.

**Never:** Do not break the guided demo, do not make browser JavaScript compute
eligibility or score, do not delete the final report/evidence files, and do not
claim the semantic memory is an LLM vector database when it is currently a
deterministic learning ledger.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| SQLITE_TECH_BOOTSTRAP | Fresh DB after startup | Existing five seed technicians are persisted once in SQLite | Startup fails closed if table exists but persistence is corrupt |
| ADMIN_TECH_CRUD | Admin creates or edits technician name, zone, status, certifications, shift, workload, rating, PPE, GPS | `/api/technicians` returns the updated roster and dispatch uses it immediately | Invalid role receives `403`; invalid payload returns `422` |
| TECH_SCHEDULE_VISIBILITY | User views technician cards | Cards show status, zone, workload, rating, shift hours, certifications, and edit control for admins | Missing optional fields render as clearly unavailable |
| UNCLEAR_ORDER_TEXT | Request text like `asdfasdf` plus vague address | App rejects the order with a clear message that category/skill cannot be inferred | No order is inserted and no dispatch simulation starts |
| DECISION_EXPLANATION | User runs dispatch | Recommendation explains hard rules, score components, and memory effect separately | No feasible candidates still shows rejection evidence only |
| MEMORY_EXPLANATION | User views semantic memory panel | Panel explains memory sources: completion duration and dispatcher feedback | Empty memory shows an operational empty state |

</frozen-after-approval>

## Code Map

- `app/adapters/legacy/compatibility.py` -- legacy UI API and dispatch simulator; replace technician globals with SQLite-backed roster helpers.
- `app/adapters/persistence/schema.py` -- add metadata for persisted operational technicians.
- `app/migrations/versions/` -- add technician table migration after the users revision.
- `app/startup.py` -- seed technician roster from existing JSON when DB is empty.
- `app/main.py` -- pass the resolved database path into compatibility routes/admin checks if needed.
- `frontend/index.html` -- add admin technician editor and explanation panels.
- `frontend/main.js` -- render editable technician cards, submit technician changes, show validation errors, and display decision/memory explanations.
- `frontend/index.css` -- style technician editor, schedule chips, validation messages, and explanation blocks.
- `tests/integration/test_legacy_compatibility.py` -- cover SQLite-backed roster, admin technician CRUD, unclear-order rejection, and dispatch use of edited technicians.
- `docs/ai-project-status.md`, `docs/runbook.md`, `docs/TASKS.md` -- update current status and next work.

## Tasks & Acceptance

**Execution:**
- [x] `app/migrations/versions/20260818_0009_technicians.py` -- create `service_technicians` with unique legacy id, name, zone, status, certifications JSON, shift start/end, workload, rating, PPE JSON, GPS JSON, and timestamps.
- [x] `app/adapters/persistence/schema.py` -- mirror the technician table constraints and JSON validity checks.
- [x] `app/adapters/legacy/compatibility.py` -- add SQLite roster bootstrap/read/create/update helpers and make dispatch read current technicians from SQLite.
- [x] `app/adapters/legacy/compatibility.py` -- add admin-only POST/PATCH routes for technician administration.
- [x] `app/adapters/legacy/compatibility.py` -- reject low-information service text before order insertion and return actionable Spanish error copy.
- [x] `frontend/index.html`, `frontend/main.js`, `frontend/index.css` -- add admin technician CRUD UI and visible shift/criteria/memory explanations.
- [x] `tests/integration/test_legacy_compatibility.py` and new focused tests if useful -- cover persistence, edit propagation into dispatch, vague request rejection, and authorization.
- [x] `docs/*` handoff files -- record the operational shift from JSON roster to SQLite-managed technicians and remaining limits.

**Acceptance Criteria:**
- Given a fresh runtime database, when startup completes, then `/api/technicians` returns the seeded technicians from SQLite rather than an in-memory JSON list.
- Given an admin edits a technician's certifications or shift, when dispatch simulation runs, then eligibility and hard-rule evidence reflect the edited values.
- Given a non-admin user calls technician write routes, when the request is processed, then the API returns `403`.
- Given an unclear request such as `asdfasdf`, when the form is submitted, then the UI shows a clear rejection and no new order is created.
- Given the memory panel is visible, when learnings exist, then the user can see what evidence created them and whether they influenced the current recommendation.

## Design Notes

This slice intentionally keeps orders on the existing compatibility route while
moving technicians first. Technician data is the highest-value operational
entity for the user's current complaint, and migrating it first makes the UI
editable without risking the whole dispatch-run canonical migration. The seed
JSON remains as a bootstrap fixture and evidence source, not as the runtime
source of truth.

## Verification

**Commands:**
- `.venv/bin/python -m pytest tests/integration/test_legacy_compatibility.py tests/integration/test_user_admin.py tests/integration/test_migrations.py tests/unit/test_runtime.py` -- expected: selected tests pass.
- `.venv/bin/python -m py_compile app/adapters/legacy/compatibility.py app/main.py app/startup.py app/migrations/versions/20260818_0009_technicians.py` -- expected: no syntax errors.
- `node --check frontend/main.js` -- expected: no syntax errors.
- `docker build -t smart-dispatch-ia:technician-ops .` -- expected: image builds.

**Performed:**
- `.venv/bin/python -m py_compile app/adapters/legacy/compatibility.py app/main.py app/startup.py app/migrations/versions/20260818_0009_technicians.py tools/build_final_report_pdf.py` -- passed.
- `node --check frontend/main.js` -- passed.
- `.venv/bin/python -m pytest tests/integration/test_legacy_compatibility.py tests/integration/test_migrations.py tests/integration/test_user_admin.py tests/unit/test_runtime.py` -- passed: `61 passed`.
- `.venv/bin/python -m pytest` -- passed: `310 passed`.
- `docker build -t smart-dispatch-ia:technician-ops .` -- passed.
- Docker Compose smoke on `8050` -- passed: admin login `200`, `/api/technicians` returned SQLite-backed records with timestamps, admin technician creation returned `201`, and unclear order text returned `422`.

## Spec Change Log

- Review finding: reset and technician writes could mutate technician runtime
  data too broadly. Amended implementation to require admin on reset, require
  idempotency on technician create/update, and avoid write fallback when the
  SQLite technician table is unavailable. This avoids silent loss of admin
  edits or accidental double-submit mutations. KEEP: SQLite-backed roster and
  admin-visible technician editor remain.
- Review finding: technician boundary and DB validation were too permissive.
  Amended validation to reject unknown fields, invalid ids, non-string list
  values, non-finite numbers, and strengthened migration/schema constraints for
  workload, rating, shift format, list JSON, and GPS shape. This avoids corrupt
  persisted operational data entering dispatch evidence. KEEP: seed bootstrap
  and editable operational fields remain.
- Review finding: unclear-order filter rejected valid terse incidents and could
  accept misleading substrings. Amended text normalization and known-term
  matching so concise requests like `fuga gas` with a numbered address pass,
  while random text still returns an actionable `422`. KEEP: no order insertion
  for low-information requests.

---
title: 'Service Visit Calendar'
type: 'feature'
created: '2026-08-19'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'c0e113b'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The app can assign and complete work, but there is no operational
calendar showing which technician has visits, when they happened, or what
service was assigned. This keeps technician operations feeling incomplete.

**Approach:** Add a SQLite-backed service visit ledger and a frontend
Calendario view. The first slice records a visit automatically when a dispatch
is confirmed, lists visits through `/api/visits`, and displays them grouped by
technician/day without paid map or calendar services.

## Boundaries & Constraints

**Always:** Keep FastAPI, SQLite, Alembic, and vanilla JS; keep the current
legacy dispatch UI routes working; do not introduce external calendar/map
providers; keep visit data same-origin and protected by existing login; preserve
technician SQLite as the operational source for names, shifts, and GPS.

**Ask First:** Manual visit creation independent of dispatch, recurring shifts,
drag-and-drop scheduling, external map tiles, Google Calendar sync, or full
migration of legacy orders into canonical `work_orders`.

**Never:** Store visits only in JSON; bypass the existing confirmation flow;
remove current order queue or technician cards; make maps/calendars depend on a
paid service.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| CONFIRM_VISIT | Dispatcher confirms a dispatch | A completed visit is persisted with order, technician, zone, scheduled window, duration, and feedback | Missing order/technician remains `404` |
| LIST_VISITS | Authenticated user opens Calendario | `/api/visits` returns SQLite visits with technician names and order summary | Empty table returns `[]` |
| RESET_VISITS | Admin resets demo | Visits table is cleared with orders/memory reset | Non-admin reset remains forbidden |
| FILTER_TECH | User selects a technician filter | Calendar shows only matching visits and updates summary counts | Unknown filter shows empty state |

</frozen-after-approval>

## Code Map

- `app/adapters/persistence/schema.py` -- SQLAlchemy table metadata for runtime SQLite.
- `app/migrations/versions/` -- ordered Alembic schema revisions.
- `app/adapters/legacy/compatibility.py` -- legacy API routes and dispatch confirmation flow.
- `frontend/index.html` -- SPA navigation and calendar view markup.
- `frontend/main.js` -- same-origin data loading, rendering, and dispatch UI state.
- `frontend/index.css` -- responsive card/list styling.
- `tests/integration/test_legacy_compatibility.py` -- legacy API behavior coverage.
- `tests/integration/test_migrations.py` -- migration table expectations.

## Tasks & Acceptance

**Execution:**
- [x] `app/adapters/persistence/schema.py` and migration `20260819_0010_service_visits.py` -- add SQLite visit ledger.
- [x] `app/adapters/legacy/compatibility.py` -- add visit store helpers, `/api/visits`, reset cleanup, and confirmation visit creation.
- [x] `frontend/index.html`, `frontend/main.js`, `frontend/index.css` -- add Calendario navigation, filters, summary, and visit cards.
- [x] tests -- cover migration presence, empty visits, confirmation-created visit, reset cleanup, and UI data loading safety.
- [x] docs/handoff -- update project status, runbook, and agent handoff.

**Acceptance Criteria:**
- Given an authenticated user, when `/api/visits` is called before any
confirmation, then the response is `200` with an empty list.
- Given a dispatch is confirmed, when `/api/visits` is called, then the
completed service visit appears with technician and work-order context.
- Given the same dispatch confirmation is retried, when `/api/visits` is
called, then only one visit exists for that order.
- Given the demo is reset by an admin, when `/api/visits` is called, then prior
runtime visits are gone.
- Given the frontend loads, when the user opens Calendario, then visits are
shown with filter and empty-state behavior without leaving the page.

## Spec Change Log

- 2026-08-19 review patch: duplicate confirmation handling now returns the
  existing visit before mutating order state, technician workload, or learning
  memory; concurrent insert races fall back to the existing visit; calendar
  rendering groups visits by day and technician; visit reads resolve current
  technician names from SQLite; API contracts document `/api/visits`.

## Design Notes

Visits intentionally reference legacy order ids as text in this slice. The
calendar becomes useful immediately while the larger work-order migration stays
separate and lower risk.

The service visit ledger is idempotent by `order_id` so repeated confirmation
attempts do not duplicate the operational calendar.

## Verification

**Commands:**
- `.venv/bin/python -m py_compile app/adapters/legacy/compatibility.py app/adapters/persistence/schema.py app/migrations/versions/20260819_0010_service_visits.py` -- expected: no syntax errors.
- `node --check frontend/main.js` -- expected: no syntax errors.
- `.venv/bin/python -m pytest tests/integration/test_legacy_compatibility.py tests/integration/test_migrations.py` -- expected: selected tests pass.
- `.venv/bin/python -m pytest` -- expected: full suite passes.
- `docker compose up -d --build` plus smoke on `8050` -- expected: app serves calendar view and `/api/visits` responds.

**Performed:**
- `.venv/bin/python -m py_compile app/adapters/legacy/compatibility.py app/adapters/persistence/schema.py app/migrations/versions/20260819_0010_service_visits.py` -- passed.
- `node --check frontend/main.js` -- passed.
- `.venv/bin/python -m pytest tests/integration/test_legacy_compatibility.py tests/integration/test_migrations.py` -- passed: `49 passed`.
- `.venv/bin/python -m pytest` -- passed: `312 passed`.
- `docker compose up -d --build` -- passed.
- Docker Compose smoke on `8050` -- passed: login `200`, calendar HTML present, `/api/visits` returned `[]`, confirmation returned `200`, and `/api/visits` returned one `completada` visit.
- Docker Compose reset/idempotency smoke on `8050` -- passed: reset cleared visits, duplicate confirmation returned the same visit id, and `/api/visits` kept one visit for the order.
- Review patch verification: `.venv/bin/python -m py_compile ...`,
  `node --check frontend/main.js`, and focused legacy/migration tests passed
  after idempotent confirmation, current technician-name resolution, grouped
  calendar rendering, and API contract updates.
- Final verification after review fixes: `.venv/bin/python -m pytest` passed
  with `312 passed`; Docker Compose smoke on `8050` passed with reset,
  duplicate confirmation, and one final completed visit.

## Suggested Review Order

**Visit Ledger**

- Schema adds a persisted visit ledger with one entry per order.
  [`schema.py:142`](../../app/adapters/persistence/schema.py#L142)

- Migration creates the same constraints and indexes for runtime upgrades.
  [`20260819_0010_service_visits.py:15`](../../app/migrations/versions/20260819_0010_service_visits.py#L15)

**Confirmation Flow**

- Existing visits are detected before mutating workload or memory.
  [`compatibility.py:1231`](../../app/adapters/legacy/compatibility.py#L1231)

- Visit reads resolve current technician names from SQLite.
  [`compatibility.py:596`](../../app/adapters/legacy/compatibility.py#L596)

- Concurrent duplicate inserts fall back to the existing visit.
  [`compatibility.py:688`](../../app/adapters/legacy/compatibility.py#L688)

- Calendar endpoint exposes authenticated visit history.
  [`compatibility.py:964`](../../app/adapters/legacy/compatibility.py#L964)

**Calendar UI**

- Navigation and markup add Calendario as a first-class app section.
  [`index.html:80`](../../frontend/index.html#L80)

- Data loading includes `/api/visits` with array guards.
  [`main.js:603`](../../frontend/main.js#L603)

- Calendar rendering groups visits by day and technician.
  [`main.js:767`](../../frontend/main.js#L767)

- Completion submit disables during the request to prevent double clicks.
  [`main.js:1258`](../../frontend/main.js#L1258)

- Calendar cards wrap long operational text on narrow screens.
  [`index.css:722`](../../frontend/index.css#L722)

**Verification**

- Integration coverage checks empty visits, confirmation, rename, retry, and reset.
  [`test_legacy_compatibility.py:199`](../../tests/integration/test_legacy_compatibility.py#L199)

- API documentation records the new route and confirmation response shape.
  [`api-contracts.md:66`](../../docs/api-contracts.md#L66)

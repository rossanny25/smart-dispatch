---
title: 'Dashboard Navigation And Admin Window'
type: 'feature'
created: '2026-08-19'
status: 'done'
review_loop_iteration: 0
baseline_commit: '56308e8e58a7f256c1a1ad0d15f5a1748256a717'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/AGENTS.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The browser UI has become too dense because service capture,
orders, guided demo, agent traces, recommendation evidence, users, and
technician editing all render in one long dashboard. This makes the application
feel more like a demo board than an operational tool.

**Approach:** Add a top navigation bar that switches between the main
operational sections, and move user administration plus technician creation and
editing into a separate admin window. Keep the existing vanilla frontend,
same-origin API calls, and current backend contracts.

## Boundaries & Constraints

**Always:** Preserve the existing FastAPI/static frontend stack; keep admin
actions restricted by current session role; keep service request, work-order
queue, guided demo, agent console, recommendation, technicians, and memory
reachable; preserve the current `/api` and `/api/v1` calls; avoid changing
dispatch formulas or persistence behavior.

**Ask First:** Introducing a frontend framework, replacing the visual identity,
changing API contracts, adding real map providers, or splitting admin into
server-rendered pages.

**Never:** Hide required operational evidence after dispatch; remove the guided
demo; remove admin edit flows; store UI-only edits outside SQLite; add paid
services or third-party accounts.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| MAIN_NAV | Authenticated user opens app | Default view shows service request and queue, with nav buttons for the other operational sections | Missing sections leave current view unchanged |
| ADMIN_NAV | Admin session | Users and technicians admin button opens a separate modal/window with tabs | Non-admin does not see admin nav |
| TECH_EDIT | Admin clicks edit on a technician card | Admin window opens on technician tab and preloads the selected technician | Missing technician id does nothing |
| DISPATCH_RESULT | User runs dispatch | Agent console and recommendation view becomes active/visible so evidence is not hidden | Failed simulation shows current error behavior |
| MOBILE | Narrow viewport | Navigation wraps cleanly and admin window remains usable without text overlap | Browser retains native scrolling |

</frozen-after-approval>

## Code Map

- `frontend/index.html` -- current single-page layout and admin forms.
- `frontend/main.js` -- session-aware UI state, admin form handlers, guided demo, dispatch rendering.
- `frontend/index.css` -- responsive layout, cards, forms, admin and evidence styling.
- `docs/runbook.md` -- technical action log and AI handoff evidence.
- `docs/ai-project-status.md` -- current status and next-action summary.

## Tasks & Acceptance

**Execution:**
- [x] `frontend/index.html` -- add section navigation, mark cards as view sections, and move admin forms into an admin window.
- [x] `frontend/main.js` -- implement view switching, admin window open/close/tab logic, and route existing edit actions into that window.
- [x] `frontend/index.css` -- style navigation, active sections, admin window, responsive layout, and prevent overcrowding on mobile.
- [x] `docs/runbook.md` and `docs/ai-project-status.md` -- document the dashboard navigation/admin-window change.
- [x] tests/checks -- run syntax, existing pytest suite, and Docker smoke if frontend/backend behavior changed.

**Acceptance Criteria:**
- Given a logged-in admin, when the app loads, then the main screen is not a
single fully expanded admin dashboard and admin tools open in a separate
window.
- Given a non-admin user, when the app loads, then user and technician
administration controls are not visible.
- Given an admin clicks edit on a technician card, when the admin window opens,
then the technician form is populated and saving still updates SQLite-backed
dispatch data.
- Given a dispatch is executed, when results return, then agent trace,
recommendation, hard rules, score, confidence, and override remain reachable.
- Given a narrow viewport, when navigation wraps, then labels and controls do
not overlap.

## Spec Change Log

- Review finding: console could become blank after reset or confirmation, and
  simulation failure could still mark the cycle as complete. Amended frontend
  state transitions so reset returns to the request view, confirmation returns
  to the order queue, failed simulation marks the plan step and cycle as error,
  and completed dispatch results force the console view visible. KEEP: section
  navigation and separate admin window remain.

## Design Notes

Treat the new navigation as section state inside the existing SPA rather than
new routes. This keeps Render/Docker simple and avoids backend routing changes.
The admin window behaves like a modal workspace with tabs so daily dispatch
users do not have to visually carry forms for user creation or technician
editing.

## Verification

**Commands:**
- `node --check frontend/main.js` -- expected: no syntax errors.
- `.venv/bin/python -m pytest` -- expected: test suite passes.
- `docker build -t smart-dispatch-ia:navigation-admin .` -- expected: image builds.
- Docker Compose smoke on `8050` -- expected: login works and core APIs still respond.

**Performed:**
- `node --check frontend/main.js` -- passed.
- `.venv/bin/python -m pytest` -- passed: `310 passed`.
- `docker compose up -d --build` -- passed.
- Docker Compose smoke on `8050` -- passed: served new navigation/admin-window HTML and `/api/technicians` returned 5 records with admin session.
- Playwright visual QA was attempted but the local Chromium binary was not installed in `~/Library/Caches/ms-playwright`; no browser screenshots were captured.

## Suggested Review Order

**Navigation Shell**

- Start with the new top-level operational sections.
  [`index.html:59`](../../frontend/index.html#L59)

- Section visibility is centralized in one small state function.
  [`main.js:172`](../../frontend/main.js#L172)

- One active view replaces the previous permanent two-column dashboard.
  [`index.css:201`](../../frontend/index.css#L201)

**Admin Window**

- Admin forms now live in a separate modal workspace.
  [`index.html:459`](../../frontend/index.html#L459)

- Existing admin cards are moved into the modal without duplicating forms.
  [`main.js:194`](../../frontend/main.js#L194)

- Technician edit opens the admin window on the technician tab.
  [`main.js:670`](../../frontend/main.js#L670)

- Modal layout and tabs define the separate administration surface.
  [`index.css:472`](../../frontend/index.css#L472)

**Dispatch States**

- Dispatch forces the console view before running the agent cycle.
  [`main.js:896`](../../frontend/main.js#L896)

- Failed simulation now leaves explicit error evidence.
  [`main.js:985`](../../frontend/main.js#L985)

- Completed recommendations force visible console evidence.
  [`main.js:1047`](../../frontend/main.js#L1047)

- Confirmation returns to queue instead of a blank console.
  [`main.js:1175`](../../frontend/main.js#L1175)

- Reset returns to service capture instead of a blank console.
  [`main.js:1204`](../../frontend/main.js#L1204)

**Handoff**

- Current project status records the new navigation shape.
  [`ai-project-status.md:3`](../../docs/ai-project-status.md#L3)

- Runbook records the technical action log entry.
  [`runbook.md:326`](../../docs/runbook.md#L326)

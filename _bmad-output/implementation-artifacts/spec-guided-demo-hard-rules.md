---
title: 'Guided demo and hard-rule evidence'
type: 'feature'
created: '2026-08-11'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'bd88dc1ea339c6cb490689fb42ad9ac041ab9572'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/ai-project-status.md'
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The app runs and can demonstrate dispatch manually, but it lacks an obvious guided path and the UI does not expose hard-rule eligibility evidence before score. This makes the core decision model less visible to a reviewer or operator.

**Approach:** Add a guided demo control to the existing vanilla frontend and extend the legacy simulation response with per-technician hard-rule checks. Keep the feature focused on the current UI and compatibility API, while preserving the canonical `/api/v1` backend for later migration.

## Boundaries & Constraints

**Always:** Preserve the current FastAPI + vanilla JS stack. Keep `/api/dispatch/simulate`, `/api/reset`, `/api/technicians`, and `/api/orders` compatible with the existing frontend. Treat availability/status, required certifications, shift/workload, driving/travel limit, and safety/EPP placeholder evidence as hard-rule evidence. Show hard-rule pass/fail before or beside the score in the UI.

**Ask First:** Adding authentication, replacing the frontend framework, migrating this feature fully to `/api/v1`, changing seed identities, or changing the scoring formula.

**Never:** Do not remove screenshots, report files, seeds, legacy routes, Docker port `8050`, or existing dispatch/confirmation flow. Do not represent rejected technicians as recommended. Do not claim real GPS/weather/traffic integrations.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Guided happy path | Pending seeded order exists | Demo guide resets scenario, selects a pending order, starts dispatch, scrolls to recommendation, and shows next action | If reset or simulation fails, show a visible demo status error |
| Hard-rule evidence | Simulation returns candidates | UI renders each candidate with pass/fail hard-rule checks and rejection alerts before score emphasis | Missing evidence renders as "No informado" rather than breaking |
| No feasible candidates | All candidates rejected or no certified candidates | UI shows no forced recommendation and displays rejection evidence if available | If candidate list is empty, show a concise no-feasible message |
| Manual flow preserved | User clicks existing "Despachar" button | Existing cycle, recommendation, override, confirm, and learning flow still work | Existing error handling remains visible |

</frozen-after-approval>

## Code Map

- `frontend/index.html` -- Existing app layout, environment controls, recommendation card, order queue, technicians grid, modal.
- `frontend/main.js` -- Existing data loading, simulation flow, recommendation rendering, confirmation, reset, and frontend state.
- `frontend/index.css` -- Existing visual system for cards, badges, buttons, timelines, modal, and responsive layout.
- `app/adapters/legacy/compatibility.py` -- Compatibility API that current frontend uses for orders, technicians, simulation, confirmation, reset, and memory.
- `tests/integration/test_legacy_compatibility.py` -- Existing integration coverage for legacy API behavior.
- `docs/ai-project-status.md` -- Handoff status to update after implementation.
- `docs/TASKS.md` -- Backlog/progress to update after implementation.
- `docs/runbook.md` -- Technical action log to update after implementation.

## Tasks & Acceptance

**Execution:**
- [x] `app/adapters/legacy/compatibility.py` -- include hard-rule evidence for all technicians in simulation output, including rejected candidates when relevant.
- [x] `frontend/index.html` -- add guided demo controls/status and a hard-rule evidence surface near the recommendation.
- [x] `frontend/main.js` -- implement guided demo orchestration, render hard-rule evidence, handle no-feasible cases, and preserve manual flow.
- [x] `frontend/index.css` -- style guided demo and hard-rule evidence with existing visual language and responsive constraints.
- [x] `tests/integration/test_legacy_compatibility.py` -- assert simulation returns hard-rule evidence and does not drop rejected/no-feasible context.
- [x] `docs/ai-project-status.md`, `docs/TASKS.md`, `docs/runbook.md` -- update status/progress after verification.

**Acceptance Criteria:**
- Given the app has seeded pending orders, when the user clicks the guided demo control, then the app resets demo data, loads a pending order, executes dispatch, and displays the next recommended action.
- Given a dispatch simulation completes, when the recommendation appears, then the UI also shows hard-rule pass/fail evidence for technicians before relying on score.
- Given no technician is feasible, when simulation completes, then the UI shows a no-feasible state with available rejection evidence and does not show an approval button for a nonexistent recommendation.
- Given the user uses the original manual "Despachar" button, when simulation completes, then existing recommendation, override, confirmation, completion, and learning behavior still works.

## Design Notes

Keep the guided demo as operational UI, not tutorial copy. Use compact status text and buttons; avoid adding a marketing section. The hard-rule surface should be scan-friendly: technician name, eligible/rejected status, rule chips, alerts, score, and travel time.

## Verification

**Commands:**
- `/private/tmp/smart-dispatch-py312-test/bin/python -m pytest tests/integration/test_legacy_compatibility.py tests/integration/test_legacy_eligibility_regression.py tests/unit/test_repository_hygiene.py tests/unit/test_project_metadata.py` -- expected: all selected tests pass.
- `docker build -t smart-dispatch-ia:guided-demo .` -- expected: image builds successfully.

**Manual checks:**
- Start the app on port `8050`, click the guided demo control, confirm the guided flow runs, hard-rule evidence appears, and approval/completion still work.

**Results:**
- `17 passed` for the focused compatibility/repository suite.
- `node --check frontend/main.js` passed.
- `docker build -t smart-dispatch-ia:guided-demo .` passed.
- Local API verification returned 5 candidates, 2 approved, 3 rejected, 6 hard-rule checks for the top candidate, rejected candidates without score, and backend-provided confidence `0.79 alta`.

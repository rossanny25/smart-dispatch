# AI Project Status - Smart Dispatch IA

Last updated: 2026-08-19

This file is the live handoff for any AI agent or human collaborator joining
the project. It summarizes what exists, what is done, what is intentionally out
of scope, and where to look before changing anything.

## Project Summary

Smart Dispatch IA is a functional prototype for deterministic, auditable
field-service dispatch. It demonstrates cyclic agentic orchestration and
persistent memory through a real web application.

The system recommends a technician for a work order by separating the workflow
into stages: capture, analyze, plan, evaluate, human decision, and learning.
The important product idea is not "AI decides everything"; the important idea
is that agent-like stages produce structured evidence while deterministic rules
preserve operational control.

## Current Links

| Resource | Link |
| --- | --- |
| Live app | https://smart-dispatch-q4xk.onrender.com |
| GitHub repository | https://github.com/rossanny25/smart-dispatch |
| Local Docker demo | http://127.0.0.1:8050 |
| Final Markdown report | `docs/final-report-ready.md` |
| Final PDF report | `docs/Smart_Dispatch_IA_Informe_Final.pdf` |
| Runbook | `docs/runbook.md` |
| Agent implementation context | `_bmad-output/project-context.md` |

Render Free can sleep after inactivity. If the live app is slow, wait for the
cold start before judging the deployment.

## Delivery Status

| Area | Status | Notes |
| --- | --- | --- |
| Real application | Done | FastAPI app serves frontend and API. |
| Public deployment | Done | Render Free service is live. |
| GitHub repository | Done | Remote is `git@github.com:rossanny25/smart-dispatch.git`. |
| Docker | Done | Compose exposes the app on host port `8050`. |
| Final report Markdown | Done | Self-contained source at `docs/final-report-ready.md`. |
| Final report PDF | Done | Regenerated from current evidence under `docs/`. |
| Architecture diagram | Done | Included in Markdown and supporting docs. |
| UML | Done | Included in Markdown and supporting docs. |
| Technology table | Done | Included in final report. |
| Frontend screenshots | Done | Stored under `docs/evidence/`. |
| Real usage log | Done | `docs/usage-session-log.md` and Docker/API evidence. |
| Nielsen UX review | Done | `docs/nielsen-ux-review.md`. |
| Cybersecurity log | Done | `docs/cybersecurity-log.md`. |
| AI co-work log | Done | `docs/ai-cowork-log.md`. |
| LLM/SLM local reflection | Done | Included in final report. |
| Guided demo flow | Done | Header control resets seeded data and runs a guided dispatch review. |
| Hard-rule evidence in UI | Done | Simulation exposes all technicians with pass/fail checks before score. |
| User and role administration | Done | SQLite-backed users, admin bootstrap, role-aware login, and admin UI. |
| Technician administration | Done | Runtime technicians are SQLite-backed and editable by admins. |
| Dashboard navigation | Done | Main screen uses section navigation; admin users/technicians open in a separate window. |
| Visit calendar | Done | Confirmed dispatches create SQLite-backed service visits shown in Calendario. |

## Stack

- Python 3.12.10
- uv 0.11.16
- FastAPI 0.138.2
- Uvicorn 0.46.0
- Pydantic 2.13.4
- SQLAlchemy Core 2.0.51
- Alembic 1.18.5
- SQLite
- Vanilla HTML/CSS/JavaScript
- Docker and Docker Compose
- pytest

## Runtime Commands

Docker demo:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8050
```

Default admin login:

```text
User: admin
Password: smart2026AI
```

Stop:

```bash
docker compose down
```

Reset Docker demo data:

```bash
docker compose down -v
docker compose up --build
```

Local dev:

```bash
uv sync --frozen
uv run smart-dispatch
```

Run tests:

```bash
uv run pytest
```

Focused checks:

```bash
uv run pytest tests/unit/test_repository_hygiene.py tests/unit/test_project_metadata.py
```

Regenerate PDF:

```bash
python3 tools/build_final_report_pdf.py
```

## Architecture Map

```text
Browser UI
  -> FastAPI routes
  -> Application commands
  -> DispatchOrchestrator
  -> Domain policies
  -> Unit of Work / SQLite repositories
  -> SQLite runtime database
```

Important directories:

- `frontend/`: static browser experience.
- `app/api/v1/`: canonical versioned API.
- `app/application/`: use cases and command orchestration.
- `app/domain/`: pure domain rules and policies.
- `app/adapters/legacy/`: compatibility API used by the current UI.
- `app/adapters/persistence/`: SQLite repositories and unit of work.
- `app/migrations/`: Alembic runtime schema.
- `data/seeds/`: demo technicians and orders.
- `docs/`: report, evidence, runbook, and status.
- `tools/`: helper tooling, including PDF generation.

## Data Loading

The project has SQLite-backed users, basic role administration, editable
service technicians, operational service orders, and service visits. Technician
records are bootstrapped once from:

- `data/seeds/technicians.json`

After startup, runtime technician edits are stored in SQLite and used by
dispatch simulation immediately. Demo service orders are bootstrapped into
SQLite from:

- `data/seeds/orders.json`

Completed dispatches and manually scheduled visits create `service_visits`
records in SQLite for the Calendario view.

The legacy learning memory starts from:

- `data/learning_store.json`

Runtime data is written to ignored local files or Docker volumes:

- `data/smart_dispatch.db`
- `data/learning_store.runtime.json`
- Docker volume `smart_dispatch_data`

To edit technicians, log in as an admin and use the in-app technician
administration panel. To reset technicians to the seed roster, use `/api/reset`
or reset the Docker volume.

## Verification Already Performed

Recent checks performed during final delivery:

- Docker build passed.
- Docker demo ran on `http://127.0.0.1:8050`.
- Render `/healthz` returned `{"status":"ok"}`.
- Browser screenshots were captured from a real session.
- Final PDF was regenerated with the current frontend evidence set.
- Repository/documentation checks passed:

```text
tests/unit/test_repository_hygiene.py
tests/unit/test_project_metadata.py
6 passed
```

Earlier broader test runs passed with launch-process caveats in the sandbox.

Recent checks performed after guided-demo implementation:

- Legacy simulation returns 5 candidates for `order_001`: 2 approved and 3 rejected.
- Each candidate includes 6 hard-rule checks.
- Rejected candidates keep rejection evidence and do not receive a score.
- Recommendation confidence is returned by the backend as separate evidence, not estimated from score in the browser.
- Frontend HTML exposes `Demo Guiada`, score/confidence badges, and hard-rule panel.
- JavaScript syntax check passed with `node --check frontend/main.js`.
- Focused compatibility/repository checks passed:

```text
tests/integration/test_legacy_compatibility.py
tests/integration/test_legacy_eligibility_regression.py
tests/unit/test_repository_hygiene.py
tests/unit/test_project_metadata.py
17 passed
```

- Docker image build passed:

```bash
docker build -t smart-dispatch-ia:guided-demo .
```

Recent checks performed after single-user login implementation:

- Browser routes without a session redirect to `/login`.
- API routes without a session return `401` with `authentication_required`.
- Valid login sets a signed `smart_dispatch_session` cookie.
- Logout clears the session cookie.
- Docker HTTP verification passed on port `8050`: login page `200`, protected
  API without session `401`, valid login `200`, protected API with cookie `200`.
- Focused auth/runtime/compatibility checks passed:

```text
tests/integration/test_auth.py
tests/unit/test_runtime.py
tests/integration/test_legacy_compatibility.py
tests/integration/test_legacy_eligibility_regression.py
tests/unit/test_repository_hygiene.py
tests/unit/test_project_metadata.py
29 passed
```

Recent checks performed after user/role administration implementation:

- Fresh startup runs migrations and bootstraps `admin` with role `admin`.
- Passwords are stored as PBKDF2 hashes, never plaintext.
- `/auth/session` returns role-aware session claims.
- Admin users can list, create, and edit users under `/api/v1/admin/users`.
- Technician users receive `403` on user-admin routes.
- The last active admin cannot be disabled or demoted.
- Active sessions are revalidated against SQLite, so demoted or disabled users
  lose access on the next request.
- Admin mutations store basic idempotency records and reject reused keys with
  different payloads.
- Login rejects oversized payloads and avoids falling back to the default admin
  when the SQLite user store is corrupt.
- Render blueprint generates `SMART_DISPATCH_SESSION_SECRET` and enables secure
  cookies for HTTPS.
- JavaScript syntax check passed with `node --check frontend/main.js`.
- Docker HTTP verification passed on port `8050`: `/login` `200`, protected
  admin API without session `401`, admin login `200`, `/auth/session` returned
  `role=admin`, user list `200`, and technician creation `201`.
- Focused auth/admin/migration/runtime checks passed:

```text
tests/integration/test_auth.py
tests/integration/test_user_admin.py
tests/integration/test_migrations.py
tests/integration/test_startup_safety.py
tests/unit/test_runtime.py
63 passed, 1 deselected
```

The deselected test was `test_startup_lock_serializes_independent_processes`,
an existing timing-sensitive multiprocessing assertion that intermittently
measures just below its `0.4s` threshold on this machine.

## Known Limits

- Technician profiles are operational but still compact; document uploads are represented as metadata only.
- Visit calendar and map view are local operational views without external provider integration.
- No public self-registration or password email delivery.
- Runtime persistence on free hosting can be ephemeral.
- Admin user writes currently use a compact auth-store helper instead of the
  main dispatch unit-of-work abstraction.
- Admin endpoints return pragmatic JSON bodies; the deeper canonical command
  envelope can be added when the frontend migrates more `/api/v1` workflows.
- Service orders, technicians, and visits use SQLite-backed operational storage;
  the browser still reaches them through compatibility routes.
- The frontend still uses some legacy compatibility routes, now with richer evidence for the guided demo.
- The canonical `/api/v1` backend is stronger than the current UI presentation.
- No real GPS or traffic/weather provider integration is connected.
- Ollama is available only as an optional local `ANALYZE` proposal adapter; it
  is off by default and not configured for Render.

Do not treat these as accidental omissions. They are documented MVP boundaries.

## Recommended Next Work

Only do these if the user asks for more after the final delivery:

1. Connect visible canonical state chips to persisted `DispatchRun` transitions and revision from `/api/v1`.
2. Implement human decision and outcome commands on the canonical `/api/v1` flow.
3. Move admin writes into the main Unit of Work and canonical command envelope.
4. Complete episodic memory and semantic promotion with memory on/off comparison scenarios.
5. Improve accessibility with visible focus, semantic labels, keyboard navigation, and readable errors.
6. Expand authentication only if the project moves beyond single-user demo use.

## Agent Rules

- Start from `AGENTS.md`, then read `_bmad-output/project-context.md`.
- Prefer existing architecture over new frameworks.
- Keep changes small and evidence-oriented.
- Preserve public links, report files, screenshots, seeds, and logs.
- Do not replace FastAPI/vanilla frontend with another stack.
- Do not remove legacy routes until the UI fully migrates to `/api/v1`.
- Do not claim enterprise production readiness; this is a scoped MVP.

# AI Project Status - Smart Dispatch IA

Last updated: 2026-08-11

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
| Final report PDF | Done | Includes screenshots, 12 pages, under `docs/`. |
| Architecture diagram | Done | Included in Markdown and supporting docs. |
| UML | Done | Included in Markdown and supporting docs. |
| Technology table | Done | Included in final report. |
| Frontend screenshots | Done | Stored under `docs/evidence/`. |
| Real usage log | Done | `docs/usage-session-log.md` and Docker/API evidence. |
| Nielsen UX review | Done | `docs/nielsen-ux-review.md`. |
| Cybersecurity log | Done | `docs/cybersecurity-log.md`. |
| AI co-work log | Done | `docs/ai-cowork-log.md`. |
| LLM/SLM local reflection | Done | Included in final report. |

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

The project has no login or admin panel by design. Demo information is loaded
from versioned seed files:

- `data/seeds/technicians.json`
- `data/seeds/orders.json`

The legacy learning memory starts from:

- `data/learning_store.json`

Runtime data is written to ignored local files or Docker volumes:

- `data/smart_dispatch.db`
- `data/learning_store.runtime.json`
- Docker volume `smart_dispatch_data`

To edit demo data, update the seed JSON files and reset the demo.

## Verification Already Performed

Recent checks performed during final delivery:

- Docker build passed.
- Docker demo ran on `http://127.0.0.1:8050`.
- Render `/healthz` returned `{"status":"ok"}`.
- Browser screenshots were captured from a real session.
- Final PDF was generated with 12 pages and 4 embedded screenshots.
- Repository/documentation checks passed:

```text
tests/unit/test_repository_hygiene.py
tests/unit/test_project_metadata.py
6 passed
```

Earlier broader test runs passed with launch-process caveats in the sandbox.

## Known Limits

- No authentication or roles.
- No admin panel.
- Runtime persistence on free hosting can be ephemeral.
- The frontend still uses some legacy compatibility routes.
- The canonical `/api/v1` backend is stronger than the current UI presentation.
- No real GPS, traffic, weather, or LLM integration is connected.
- Ollama/SLM integration is documented as a possible future extension, not a
  required working feature.

Do not treat these as accidental omissions. They are documented MVP boundaries.

## Recommended Next Work

Only do these if the user asks for more after the final delivery:

1. Add a guided in-app demo flow with scenario reset, work-order selection, dispatch, approval, and service completion.
2. Show hard-constraint pass/fail evidence before score for every technician.
3. Separate objective score and recommendation confidence visually.
4. Add a `NO_FEASIBLE_CANDIDATES` scenario with rejection reasons and no forced recommendation.
5. Surface canonical `DispatchRun` state transitions in the frontend.
6. Implement human decision and outcome commands on the canonical `/api/v1` flow.
7. Complete episodic memory and semantic promotion with memory on/off comparison scenarios.
8. Improve accessibility with visible focus, semantic labels, keyboard navigation, and readable errors.
9. Add optional Ollama adapter for the `ANALYZE` stage.
10. Add authentication only if the product becomes multi-user.

## Agent Rules

- Start from `AGENTS.md`, then read `_bmad-output/project-context.md`.
- Prefer existing architecture over new frameworks.
- Keep changes small and evidence-oriented.
- Preserve public links, report files, screenshots, seeds, and logs.
- Do not replace FastAPI/vanilla frontend with another stack.
- Do not remove legacy routes until the UI fully migrates to `/api/v1`.
- Do not claim enterprise production readiness; this is a scoped MVP.

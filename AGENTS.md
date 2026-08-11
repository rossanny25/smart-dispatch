# AI Agent Handoff

This repository is an educational field-service dispatch simulator called
Smart Dispatch IA. Read this file before making code, documentation, or
deployment changes.

## Read First

1. `docs/ai-project-status.md` - current status, links, completed work, and next actions.
2. `_bmad-output/project-context.md` - detailed implementation rules for AI agents.
3. `README.md` - setup, Docker, deploy, and report links.
4. `docs/runbook.md` - operational commands and technical action log.
5. `docs/final-report-ready.md` - final academic report source.
6. `docs/Smart_Dispatch_IA_Informe_Final.pdf` - final submitted PDF artifact.

## Current Shape

- Backend: Python 3.12.10, FastAPI, Pydantic v2, SQLAlchemy Core, Alembic, SQLite.
- Frontend: static vanilla HTML, CSS, and JavaScript under `frontend/`.
- Runtime: one FastAPI app serves both frontend and API.
- Local Docker demo: `http://127.0.0.1:8050`.
- Published demo: `https://smart-dispatch-q4xk.onrender.com`.
- GitHub repository: `https://github.com/rossanny25/smart-dispatch`.

## Critical Rules

- Preserve the hexagonal dependency direction:
  `api -> application -> domain`, with persistence and legacy adapters at the edge.
- Keep canonical API routes under `/api/v1`.
- Keep legacy compatibility routes under `/api` working for the current frontend demo.
- Only `DispatchOrchestrator` may advance dispatch run state.
- Hard constraints always run before scoring. Memory and priority must never bypass them.
- Objective score and recommendation confidence are separate concepts.
- Use `Decimal` for score/confidence arithmetic.
- Use Pydantic contracts with strict boundary validation.
- Do not move the project to React, Express, or another stack unless the user explicitly asks.
- Do not add login/admin just because production apps usually have it; this MVP intentionally documents them as out of scope.
- Do not remove seeds, screenshots, logs, or final-report files. They are grading evidence.
- Do not revert user changes or unrelated worktree changes.

## Common Commands

Docker course demo:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8050
```

Local development:

```bash
uv sync --frozen
uv run smart-dispatch
```

Tests:

```bash
uv run pytest
```

Focused docs/repo checks:

```bash
uv run pytest tests/unit/test_repository_hygiene.py tests/unit/test_project_metadata.py
```

Regenerate final PDF:

```bash
python3 tools/build_final_report_pdf.py
```

## Evidence Files

- `docs/evidence/01-dashboard-full.png`
- `docs/evidence/02-dispatch-result.png`
- `docs/evidence/03-recommendation-approved.png`
- `docs/evidence/04-learning-completed.png`
- `docs/evidence/api-technicians.json`
- `docs/evidence/api-orders-after-session.json`
- `docs/evidence/docker-session.log`

## Current Academic Delivery Status

The final-cycle delivery is functionally complete:

- App exists and runs.
- App is published.
- Docker works on port `8050`.
- GitHub repo is configured.
- Final Markdown report exists.
- Final PDF report exists and includes screenshots.
- README and runbook document how to evaluate the project.

Remaining work should be treated as polish unless the user asks for new product
features.

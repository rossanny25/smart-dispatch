# Smart Dispatch IA Runbook

This document is the operational guide for starting, verifying, stopping, and documenting technical work on the project.

## Recommended Demo Startup

Use Docker when the goal is to show the app to a teacher, record screenshots, or keep the local Python setup out of the way.

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8050
```

Published Render URL:

```text
https://smart-dispatch-q4xk.onrender.com
```

Render Free can sleep after inactivity, so the first request can take around 50 seconds or more.

The Compose service publishes container port `8050` to host port `8050`, so it should not collide with a different app already using `8000`.

## Local Development Startup

Use the local Python runtime when editing code and running tests frequently.

```bash
uv sync --frozen
uv run smart-dispatch
```

Open:

```text
http://127.0.0.1:8000
```

The legacy-compatible entry point starts the same FastAPI app:

```bash
uv run python3 server.py
```

## Useful Runtime Variables

| Variable | Default | Docker value | Purpose |
| --- | --- | --- | --- |
| `SMART_DISPATCH_HOST` | `127.0.0.1` | `0.0.0.0` | Interface where Uvicorn listens. |
| `SMART_DISPATCH_PORT` | `8000` | `8050` | HTTP port for the app. |
| `SMART_DISPATCH_DB_PATH` | `data/smart_dispatch.db` | `/app/runtime-data/smart_dispatch.db` | SQLite runtime database. |
| `SMART_DISPATCH_LEARNING_STORE_PATH` | `data/learning_store.runtime.json` | `/app/runtime-data/learning_store.runtime.json` | Runtime copy of brownfield learning memory. |

## Verify The App Is Running

Browser check:

```text
http://127.0.0.1:8050
```

API check:

```bash
curl http://127.0.0.1:8050/api/technicians
```

Container status:

```bash
docker compose ps
```

Container logs:

```bash
docker compose logs -f smart-dispatch
```

## Stop Or Reset The Demo

Stop containers and keep the named volume:

```bash
docker compose down
```

Stop containers and remove runtime demo data:

```bash
docker compose down -v
```

Rebuild from scratch:

```bash
docker compose build --no-cache
docker compose up
```

Reset the running demo from the seed files:

```bash
curl -X POST http://127.0.0.1:8050/api/reset
```

Edit seed data here:

```text
data/seeds/technicians.json
data/seeds/orders.json
```

For the repository and data-loading rationale, see `docs/repository-and-data-strategy.md`.

For public hosting options, see `docs/deployment-options.md`.

## Test Commands

Focused runtime and repository checks:

```bash
uv run pytest tests/unit/test_runtime.py tests/unit/test_repository_hygiene.py
```

Full suite:

```bash
uv run pytest
```

If the local `.venv` was moved from another folder and has broken shebangs, recreate it with:

```bash
uv sync --frozen
```

## Technical Action Log

Use this section as the running implementation log for the final report and project review.

### 2026-08-11 - Dockerized Course Demo On Port 8050

- Added container startup through `Dockerfile` and `docker-compose.yml`.
- Kept the local default runtime on `127.0.0.1:8000`.
- Added runtime overrides with `SMART_DISPATCH_HOST` and `SMART_DISPATCH_PORT`.
- Configured Docker to run on `0.0.0.0:8050`.
- Stored container runtime database and learning copy in the `smart_dispatch_data` Docker volume.
- Verified image build with `docker build -t smart-dispatch-ia:local .`.
- Verified container startup on `http://127.0.0.1:8050`.
- Verified legacy API data with `/api/technicians`.
- Added `docs/final-delivery-guide.md` for the teacher's final-cycle requirements.

### 2026-08-11 - Test Environment Notes

- The checked-in `.venv` was path-bound to an older folder and should be recreated locally before routine development.
- A temporary Python 3.12 venv was used for verification.
- `275` tests passed with `tests/integration/test_launch_process.py` excluded because the sandbox blocks process-level port binding checks.

### 2026-08-11 - Final Delivery Documentation Pack

- Added `docs/final-report.md` as the 10-20 page PDF source draft.
- Added `docs/final-architecture-diagrams.md` with architecture, state-machine, UML, and evidence-flow diagrams.
- Added `docs/usage-session-log.md` for real demo evidence.
- Added `docs/nielsen-ux-review.md` for the required UX/UI self-evaluation.
- Added `docs/cybersecurity-log.md` with risks, mitigations, and limitations.
- Added `docs/ai-cowork-log.md` documenting AI-assisted development.

### 2026-08-11 - Real Browser Evidence Captured

- Started the Docker Compose demo on `http://127.0.0.1:8050`.
- Captured dashboard, dispatch recommendation, approval modal, and completed-order screenshots under `docs/evidence/`.
- Exported `/api/technicians`, `/api/orders`, and Docker logs under `docs/evidence/`.
- Updated `docs/usage-session-log.md` and `docs/final-report.md` to reference the captured evidence.

### 2026-08-11 - Seed Data Strategy

- Moved legacy demo Technicians and Orders into `data/seeds/technicians.json` and `data/seeds/orders.json`.
- Updated the legacy FastAPI compatibility adapter to load demo data from seed JSON.
- Updated `/api/reset` to reload Technicians and Orders from seed files.
- Added `docs/repository-and-data-strategy.md` to explain monorepo publication and data loading without login/admin.

### 2026-08-11 - Deploy Configuration

- Added `/healthz` for hosting health checks.
- Runtime now accepts provider `PORT` when `SMART_DISPATCH_PORT` is not set.
- Added `render.yaml` as a Render Docker blueprint fallback.
- Added `docs/deployment-options.md` with Koyeb, Render, and GitHub/Docker fallback options.
- Published Render Free service at `https://smart-dispatch-q4xk.onrender.com`.

## Next Technical Actions

- Publish the repository to GitHub and put the URL on the first page of the report.
- Choose a live deployment target or document Docker/GitHub as the published runnable artifact.
- Capture frontend screenshots from the Docker app on port `8050`.
- Record one real usage session log using the visible app plus API evidence.
- Update the academic report with architecture diagram, UML, Nielsen UX review, cybersecurity log, and AI co-work section.

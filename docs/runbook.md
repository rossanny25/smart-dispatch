# Smart Dispatch IA Runbook

This document is the operational guide for starting, verifying, stopping, and documenting technical work on the project.

## Recommended Demo Startup

Use Docker when the goal is to show the app, record screenshots, or keep the
local Python setup out of the way.

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

Published Render URL:

```text
https://smart-dispatch-q4xk.onrender.com
```

Render Free can sleep after inactivity, so the first request can take around 50 seconds or more.
The blueprint in `render.yaml` currently targets the `changes` branch. If the
existing Render service still watches `main`, switch its branch to `changes`
for this work or merge the branch before redeploying.

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
| `SMART_DISPATCH_LOGIN_USER` | `admin` | unset | Initial admin login name. |
| `SMART_DISPATCH_LOGIN_PASSWORD` | `smart2026AI` | unset | Initial admin login password. |
| `SMART_DISPATCH_SESSION_SECRET` | local dev fallback | generated on Render | Secret used to sign session cookies; set this in hosted/shared environments. |
| `SMART_DISPATCH_COOKIE_SECURE` | unset | `true` | Sends session cookies as secure cookies when serving over HTTPS. |

## User Administration

The first runtime startup after migrations creates an active admin account:

```text
admin / smart2026AI
```

Admin users can manage accounts from the in-app "Administracion de Usuarios"
panel. Supported roles are:

- `admin`
- `tecnico`
- `dispatcher`

Passwords are stored as PBKDF2 hashes in SQLite. The app rejects attempts to
disable or demote the last active admin. Active sessions are revalidated
against SQLite, so disabled or demoted users lose access on the next request.

Create and update operations under `/api/v1/admin/users` require
`Idempotency-Key` through the canonical middleware. Repeating the same key with
the same payload replays the stored response; repeating it with a different
payload returns an idempotency conflict.

## Technician Administration

Technicians are SQLite-backed runtime records. On a fresh database, startup
seeds the roster from:

```text
data/seeds/technicians.json
```

After that, admin edits are stored in SQLite and immediately affect dispatch
eligibility, scoring, hard-rule evidence, and override options. Use the in-app
"Administracion de Tecnicos" panel as `admin / smart2026AI` to create or edit:

- status
- zone
- certifications
- shift start/end
- active workload
- rating
- PPE
- GPS lat/lng

## Verify The App Is Running

Browser check:

```text
http://127.0.0.1:8050
```

API check:

```bash
curl -i http://127.0.0.1:8050/login
```

Protected API routes should return `401` without a valid session cookie.

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

Editable technician runtime data should be changed from the admin UI. Seed data
remains here for reproducible bootstrap/reset:

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
- Added `docs/final-delivery-guide.md` for the final delivery requirements.

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
- Added `docs/repository-and-data-strategy.md` to explain monorepo publication and seed-based data loading without a public admin panel.

### 2026-08-11 - Deploy Configuration

- Added `/healthz` for hosting health checks.
- Runtime now accepts provider `PORT` when `SMART_DISPATCH_PORT` is not set.
- Added `render.yaml` as a Render Docker blueprint fallback.
- Added `docs/deployment-options.md` with Koyeb, Render, and GitHub/Docker fallback options.
- Published Render Free service at `https://smart-dispatch-q4xk.onrender.com`.

### 2026-08-11 - Guided Demo And Hard-Rule Evidence

- Added a `Demo Guiada` control in the header.
- Added an in-app guided review panel with reset, order selection, dispatch, evidence review, and approval steps.
- Extended legacy dispatch simulation to return all technicians with hard-rule pass/fail evidence.
- Preserved recommendation behavior: only approved candidates can be recommended.
- Added visible score and backend-provided confidence badges in the recommendation panel.
- Added hard-rule evidence cards with availability, certifications, shift, workload, driving limit, and EPP checks.
- Added no-feasible UI state that does not force a recommendation when all candidates are rejected.
- Verified API output for `order_001`: 5 candidates, 2 approved, 3 rejected, 6 checks per candidate, rejected candidates without score, and backend-provided confidence `0.79 alta`.
- Verified focused tests: `17 passed`.
- Verified Docker image build with `docker build -t smart-dispatch-ia:guided-demo .`.

### 2026-08-11 - Single-User Login

- Added a dedicated `/login` page and logout action in the main header.
- Protected browser and API routes with a signed `smart_dispatch_session` cookie.
- Kept `/healthz`, `/login`, `/auth/login`, and `/index.css` public.
- Added JSON and form login support without introducing extra multipart dependencies.
- Default demo credential: `admin` / `smart2026AI`.
- Added environment overrides for username, password, and session signing secret.
- Verified focused tests: `29 passed`.
- Verified Docker HTTP behavior on port `8050`: `/login` returned `200`,
  unauthenticated `/api/orders` returned `401`, JSON login returned `200`, and
  authenticated `/api/orders` returned `200`.

### 2026-08-18 - User And Role Administration

- Added SQLite `app_users` storage through Alembic revision `20260818_0008`.
- Added startup bootstrap for initial admin `admin` / `smart2026AI`.
- Replaced fixed credential validation with DB-backed password verification.
- Stored passwords with salted PBKDF2 hashes.
- Extended signed session cookies with user id, username, role, and expiry.
- Added `/api/v1/admin/users` list/create/update endpoints for admins.
- Added last-active-admin protection.
- Added a frontend "Administracion de Usuarios" panel visible to admins.
- Added a visible forgot-password action with manual recovery guidance.
- Revalidated active sessions against SQLite on every protected request.
- Added idempotency replay/conflict handling for admin create/update actions.
- Added Render session-secret generation and secure HTTPS cookies.
- Added login payload size protection.
- Verified focused tests: `65 passed`.
- Verified Docker HTTP behavior on port `8050`: `/login` returned `200`,
  unauthenticated `/api/v1/admin/users` returned `401`, admin login returned
  `200`, `/auth/session` returned `role=admin`, user list returned `200`, and
  creating a `tecnico` user returned `201`.
- Verified updated auth/admin/migration/runtime checks: `63 passed, 1
  deselected`; the deselected test is an existing timing-sensitive startup-lock
  assertion.

### 2026-08-18 - Technician Operations In SQLite

- Added SQLite `service_technicians` storage through Alembic revision
  `20260818_0009`.
- Startup now bootstraps technicians from `data/seeds/technicians.json` only
  when the table is empty.
- `/api/technicians` now reads runtime technician records from SQLite.
- Added admin-only create/update technician routes under `/api/technicians`.
- Dispatch simulation, confirmation, hard-rule evidence, and override options
  use the current SQLite roster.
- Added inline rejection for low-information service requests such as random
  text without a recognizable incident/address.
- Added visible UI explanations for hard rules, score/confidence, and semantic
  memory sources.
- Verified focused tests: `58 passed`.

### 2026-08-19 - Dashboard Navigation And Admin Window

- Added a top section bar for Nueva Solicitud, Cola de Ordenes, Recorrido
  Guiado, Consola y Recomendacion, Tecnicos, Memoria, and Administracion.
- Converted the main dashboard into one active operational view at a time to
  reduce visual load.
- Moved user administration and technician create/edit forms into a separate
  admin window with Usuarios and Tecnicos tabs.
- Kept technician edit actions on the field-service cards; selecting Editar
  opens the admin window directly on the technician form.

## Next Technical Actions

- Expand technician profile pages with contact fields and audit history.
- Add visit calendar views per technician.
- Add no-cost map visualization.
- Migrate demo work orders from compatibility storage into SQLite operational records.
- Add a dedicated seeded `NO_FEASIBLE_CANDIDATES` order.

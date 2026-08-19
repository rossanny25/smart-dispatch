# Smart Dispatch IA v2.1

Smart Dispatch IA is a local simulator for deterministic, auditable
field-service dispatch.

Live demo: [https://smart-dispatch-q4xk.onrender.com](https://smart-dispatch-q4xk.onrender.com)

The live demo runs on Render Free. If it was inactive, the first request can
take around 50 seconds or more while the instance wakes up.

## For AI agents

Start with [`AGENTS.md`](AGENTS.md), then read
[`docs/ai-project-status.md`](docs/ai-project-status.md) and
[`_bmad-output/project-context.md`](_bmad-output/project-context.md).
Those files explain the current project status, implementation rules, commands,
known limits, and next safe actions.

## Requirements

- Python 3.12.10
- uv 0.11.16

## Reproducible setup and launch

From the project root:

```bash
uv sync --frozen
uv run smart-dispatch
```

Open `http://127.0.0.1:8000`. The application is intentionally bound to
`127.0.0.1:8000` with one Uvicorn worker by default.

Default admin login:

- User: `admin`
- Password: `smart2026AI`

The initial admin credentials can be overridden with
`SMART_DISPATCH_LOGIN_USER` and `SMART_DISPATCH_LOGIN_PASSWORD`. Set
`SMART_DISPATCH_SESSION_SECRET` in any shared or hosted environment so session
cookies are signed with a private deployment secret.

The temporary compatibility entry point runs the same canonical launcher:

```bash
uv run python3 server.py
```

## Docker launch on port 8050

The project can also run as a containerized local demo:

```bash
docker compose up --build
```

Open `http://127.0.0.1:8050`.

The Compose service sets:

- `SMART_DISPATCH_HOST=0.0.0.0`
- `SMART_DISPATCH_PORT=8050`
- `SMART_DISPATCH_DB_PATH=/app/runtime-data/smart_dispatch.db`
- `SMART_DISPATCH_LEARNING_STORE_PATH=/app/runtime-data/learning_store.runtime.json`

Runtime evidence is kept in the named Docker volume `smart_dispatch_data`.
Stop the demo with:

```bash
docker compose down
```

## Optional local Ollama analyze adapter

The default `ANALYZE` stage remains deterministic. For local-only demos, you can
enable Ollama as an optional proposal adapter:

```bash
SMART_DISPATCH_ANALYZE_ADAPTER=ollama \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
OLLAMA_MODEL=llama3.1:8b \
uv run smart-dispatch
```

Docker users can start the optional Ollama service with:

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

For a local recording when Ollama is already running on the host with an
available model, point the Docker app to the host runtime:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434 \
OLLAMA_MODEL=qwen2.5:latest \
OLLAMA_TIMEOUT_SECONDS=60 \
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d
```

This is intentionally not configured in `render.yaml`; Render continues to use
the deterministic adapter unless environment variables are manually changed.
For the local video/demo flow, see
[`docs/ollama-local-demo.md`](docs/ollama-local-demo.md).
The quick verification command is:

```bash
SMART_DISPATCH_ANALYZE_ADAPTER=ollama uv run python tools/run_ollama_analyze_demo.py
```

## Verification

```bash
uv run pytest
```

The runtime uses `data/smart_dispatch.db`. Pending migrations run before HTTP
serving, and an existing database is backed up through SQLite's backup API
under `data/backups/` before upgrade. Runtime database and backup artifacts
are ignored.

Users, service technicians, service orders, and visit records are SQLite-backed.
A fresh database bootstraps technicians from `data/seeds/technicians.json` and
orders from `data/seeds/orders.json`, then admin edits and dispatch updates are
stored in SQLite and affect dispatch immediately. The compatibility API reads
`data/learning_store.json` as its initial evidence but writes changes to the
ignored `data/learning_store.runtime.json` working copy, so the tracked
evidence remains byte-preserved.
Confirmed dispatches and manually scheduled visits create SQLite-backed
`service_visits` records shown in the Calendario view. The Mapa view is a local
operational visualization over the same seeded/runtime records.

## Canonical Work Order capture

Story 1.2 adds the first canonical command:

```http
POST /api/v1/work-orders
Content-Type: application/json
Idempotency-Key: demo-work-order-1

{
  "incident_text": "Corte de energía en tablero principal",
  "address": "Av. Siempre Viva 123",
  "zone": "Belgrano",
  "context": {"source": "phone"}
}
```

The command accepts JSON bodies up to 1 MiB, rejects unknown top-level fields,
and atomically writes `work_orders` plus `idempotency_records` in SQLite.
Repeating the same route, key, and validated request returns the original
`201` response; changing the request with the same key returns `409`.

This slice captures only schema-valid raw input. Dispatch analysis, derived
requirements, recommendations, and browser migration belong to later stories,
so the current SPA continues to use the compatibility API.

This MVP is local-first and uses SQLite-backed users, roles, technician
operations, demo orders, manual visit scheduling, completed visit history, and a
local operational map. HTTPS termination, public self-registration, password
email delivery, external GIS/GPS integrations, and full canonical work-order
administration remain outside its current scope.

For the final delivery checklist, see
[`docs/final-delivery-guide.md`](docs/final-delivery-guide.md).

For the self-contained Markdown report with links, diagrams, screenshots, and
logs, see [`docs/final-report-ready.md`](docs/final-report-ready.md).

For the PDF version of the final report, see
[`docs/Smart_Dispatch_IA_Informe_Final.pdf`](docs/Smart_Dispatch_IA_Informe_Final.pdf).

For day-to-day startup, shutdown, verification, and technical action notes, see
[`docs/runbook.md`](docs/runbook.md).

For the publication layout and data-loading strategy, see
[`docs/repository-and-data-strategy.md`](docs/repository-and-data-strategy.md).

For free/low-cost deployment options and the Render blueprint fallback, see
[`docs/deployment-options.md`](docs/deployment-options.md).

Deployment note: `render.yaml` currently targets the `changes` branch. If the
production service is configured in Render to watch `main`, either switch the
service branch to `changes` before redeploying or merge this branch into
`main`.

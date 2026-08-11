# Smart Dispatch IA v2.1

Smart Dispatch IA is a local educational simulator for deterministic,
auditable field-service dispatch.

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

## Verification

```bash
uv run pytest
```

The runtime uses `data/smart_dispatch.db`. Pending migrations run before HTTP
serving, and an existing database is backed up through SQLite's backup API
under `data/backups/` before upgrade. Runtime database and backup artifacts
are ignored. The compatibility API reads `data/learning_store.json` as its
initial evidence but writes changes to the ignored
`data/learning_store.runtime.json` working copy, so the tracked evidence
remains byte-preserved.

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

This MVP is local-first. Authentication, HTTPS termination, multi-user
operation, and production deployment are intentionally outside its current
scope.

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

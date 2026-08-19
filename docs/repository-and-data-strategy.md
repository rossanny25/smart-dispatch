# Repository And Data Strategy

## Repository Decision

Use one public monorepo for the deployable product demo.

Recommended repository contents:

```text
app/                 FastAPI backend, application layer, domain, adapters
frontend/            Browser UI served by FastAPI
data/                Seed data and local evidence inputs
data/seeds/          Demo technicians and orders
docs/                Report, diagrams, runbook, evidence logs
spec/                Original conceptual specification
prompts/             Original agent prompts
Dockerfile           Container image
docker-compose.yml   One-command demo on port 8050
README.md            First evaluator entry point
```

Why not split backend and frontend now:

- The frontend is vanilla static HTML/CSS/JS and is served by FastAPI.
- A single repo gives reviewers one GitHub link, one README, and one
  `docker compose up --build`.
- Separate repos would require extra CORS/deploy/configuration explanation without improving the academic evaluation.
- The grading requirement prioritizes a working published app with valid links.

Splitting backend/frontend can be deferred until the project needs independent deployments, multi-user administration, a real frontend build pipeline, or a team workflow with separate ownership.

## Data Loading Decision

The prototype has SQLite-backed users and a basic admin panel for account and
role management, but no public data-import UI. Dispatch data is loaded through
reproducible seeds and local runtime persistence.

Current strategy:

- Demo technicians live in `data/seeds/technicians.json`.
- Demo orders live in `data/seeds/orders.json`.
- Legacy learning evidence starts from `data/learning_store.json`.
- Docker stores runtime database and learning-copy state in the `smart_dispatch_data` volume.
- Local Python stores SQLite state in `data/smart_dispatch.db`.
- Alembic is used for database structure, not for demo content.

This is enough for the current product scope because account administration now
exists, while dispatch-data management remains reproducible and controlled.

## How To Add Or Change Demo Data

Edit:

```text
data/seeds/technicians.json
data/seeds/orders.json
```

Then restart the Docker demo:

```bash
docker compose down -v
docker compose up --build
```

The `-v` flag removes the runtime volume, so the next startup begins from the versioned seed files.

To reset the running browser demo without rebuilding:

```bash
curl -X POST http://127.0.0.1:8050/api/reset
```

The reset route reloads technicians and orders from `data/seeds/` and keeps the
learning-store behavior compatible with the current demo.

## Why There Is No Public Import Endpoint

Even with single-user login, a public data-import endpoint would increase the
blast radius of a demo environment. It could allow accidental or unauthorized
replacement of scenario data if credentials are shared.

If future work needs data import, use one of these safer options:

- A local CLI command such as `smart-dispatch-import-seed`.
- A local-only endpoint protected by `SMART_DISPATCH_IMPORT_TOKEN`.
- A private admin UI with roles, audit log, and CSRF protection.

For the final report, state that public data management is intentionally out of scope for the MVP.

## What To Tell The Teacher

Smart Dispatch IA is a dispatch simulator with basic account administration. It
uses SQLite-backed login and roles for access control, seed files for
reproducible dispatch scenarios, SQLite for runtime persistence, and Alembic for
controlled schema evolution. The current admin panel manages users; technician
profiles, calendars, maps, and dispatch-data editing belong to later product
slices.

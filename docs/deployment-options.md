# Deployment Options

## Recommended Shape

Keep one monorepo and deploy the existing Dockerfile. FastAPI serves both the API and the static frontend, so no separate frontend hosting is required.

## Option A: Koyeb Free Web Service

Koyeb currently documents one free web service per organization with 512 MB RAM, 0.1 vCPU, and 2 GB SSD. This is enough for a classroom demo, not production.

Use:

- Repository: `https://github.com/rossanny25/smart-dispatch`
- Deployment method: Dockerfile
- Port: provider `PORT` environment variable or `8050` if configured manually
- Health path: `/healthz`

Suggested runtime variables:

```text
SMART_DISPATCH_HOST=0.0.0.0
SMART_DISPATCH_DB_PATH=/app/runtime-data/smart_dispatch.db
SMART_DISPATCH_LEARNING_STORE_PATH=/app/runtime-data/learning_store.runtime.json
```

Important limitation: unless persistent volumes are enabled in the chosen plan, SQLite runtime data is ephemeral. That is acceptable for the final demo because seed data is reproducible from `data/seeds/`.

## Option B: Render Docker Web Service

Render has a `render.yaml` in this repository:

```text
render.yaml
```

The service uses:

- Docker runtime
- Branch `main`
- Health check `/healthz`
- `SMART_DISPATCH_HOST=0.0.0.0`

Render injects `PORT`; the application now reads `PORT` when `SMART_DISPATCH_PORT` is absent.

## Option C: GitHub Only + Docker Local

If a live hosting provider blocks free deployment, the repository itself is still a published runnable artifact:

```bash
git clone https://github.com/rossanny25/smart-dispatch
cd smart-dispatch
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8050
```

This is weaker than a public live URL, but it is reproducible and documented.

## Why Not GitHub Pages

GitHub Pages can host static HTML/CSS/JS, but this project needs a Python FastAPI backend, SQLite migrations, and JSON endpoints. Publishing only the frontend would not demonstrate the real application behavior required by the teacher.

## Final Report Links

Use these fields on the first page:

| Resource | Link |
| --- | --- |
| GitHub repository | `https://github.com/rossanny25/smart-dispatch` |
| Live app | Add Koyeb/Render URL after deploy |
| Local Docker fallback | `http://127.0.0.1:8050` |

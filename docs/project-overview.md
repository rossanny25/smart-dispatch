# Smart Dispatch IA - Brownfield Project Overview

> Historical snapshot: this document captured the repository before the FastAPI,
> SQLite, Docker, deployment, guided demo, hard-rule evidence, and single-user
> login work. For current status, use `AGENTS.md` and
> `docs/ai-project-status.md`.

## Executive Summary

Smart Dispatch IA is an educational field-service dispatch prototype. It accepts work orders, classifies incidents, ranks technicians, validates assignments, records dispatcher decisions, and presents the simulated agent cycle in a browser.

The repository is a single deployable web prototype with two tightly coupled parts:

- A Python standard-library HTTP server that serves both the REST API and static files.
- A vanilla HTML/CSS/JavaScript single-page interface.

The current implementation demonstrates the intended experience, but it does not yet implement the deterministic state machine, hard-constraint-first selection, normalized objective function, SQLite episodic/semantic memory, uncertainty model, or KPI evidence required by the professor feedback.

## Current State

| Area | Implemented now | Required evolution |
|---|---|---|
| Orchestration | One synchronous request simulates five named agents | Explicit persisted state machine with guarded transitions and error routes |
| Feasibility | Skills filtered before ranking; daily-hours check after ranking | Availability, all certifications, shift, and maximum-day rules before ranking |
| Ranking | Ad hoc base/proximity/workload/memory score | Configurable normalized weighted objective with score breakdown |
| Memory | Shared JSON file containing semantic-like records | SQLite episodic and semantic stores with controlled promotion |
| Explainability | Narrative, score, candidates, alerts, agent logs | Constraint checks, component scores, confidence, freshness, uncertainty, discard reasons |
| Evaluation | Dispatcher confirmation and completion feedback | KPI capture and reproducible comparison scenarios |
| UI | Functional single-page simulator | State, confidence, score breakdown, warnings, alternatives, and KPIs |

## Technology Stack

| Category | Technology | Evidence |
|---|---|---|
| Backend | Python standard library (`http.server`, `socketserver`) | `server.py` |
| Frontend | HTML5, CSS, vanilla JavaScript | `frontend/` |
| Persistence | JSON file | `data/learning_store.json` |
| API | Same-origin JSON REST-like endpoints | `/api/*` routes in `server.py` |
| External UI assets | Font Awesome CDN | `frontend/index.html` |
| Tests and CI/CD | Not present | No test or pipeline files detected |

## Repository Classification

- **Structure:** multi-part monolith
- **Deployable unit:** one Python process
- **Primary entry point:** `server.py`
- **Architecture style:** synchronous request/response prototype with in-process domain data
- **Maturity:** demonstrable educational prototype, not production-ready

## Key Risks

- `server.py` currently calls `alerts.push(...)`; the module compiles, but that branch raises `AttributeError` at runtime because Python lists use `append`.
- Orders and technician workload live in process memory and are lost on restart.
- The reset route does not restore the seeded learning file when it already exists.
- The UI exposes simulated “thought” traces; product output should use concise decision evidence instead of private reasoning traces.
- At the time of this snapshot, request schema validation, authentication,
  concurrency control, migrations, automated tests, and deployment definition
  did not exist. Current implementation status is tracked in
  `docs/ai-project-status.md`.

## Detailed Documentation

- [Architecture](./architecture.md)
- [API Contracts](./api-contracts.md)
- [Data Models](./data-models.md)
- [Component Inventory](./component-inventory.md)
- [Source Tree](./source-tree-analysis.md)
- [Development Guide](./development-guide.md)

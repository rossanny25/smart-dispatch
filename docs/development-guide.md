# Development Guide

## Prerequisites

- Python 3.12.10
- uv 0.11.16
- A modern browser

The project metadata and dependency graph are authoritative in
`.python-version`, `pyproject.toml`, and `uv.lock`.

## Install and run

From a clean checkout:

```bash
uv sync --frozen
uv run smart-dispatch
```

Open `http://127.0.0.1:8000`. The launcher always uses IPv4 loopback, port
8000, and one Uvicorn worker. It does not silently select another interface,
port, or worker count.

The brownfield entry point delegates to the same launcher:

```bash
uv run python3 server.py
```

Project, frontend, migration, database, and backup paths are resolved from
the installed project location rather than the caller's current directory.
`SMART_DISPATCH_DB_PATH` may select a different local database path for tests
or explicit local data selection.

## Startup and migration safety

- The runtime database is `data/smart_dispatch.db`.
- Every connection enables foreign keys, WAL mode, and a 5000 ms busy timeout.
- SQLite 3.35.0 or newer is required.
- Alembic migration reaches head before HTTP serving begins.
- A per-database startup lock serializes concurrent launchers through backup,
  migration, verification, and recovery.
- If an existing database has pending revisions, a verified online backup is
  created under `data/backups/`.
- A migration failure is fail-closed: Uvicorn does not start, and the verified
  backup is restored when the failed revision changed the source database.
- A failed first migration removes only the database artifacts created by that
  failed attempt, allowing the next clean launch to start reproducibly.
- `data/learning_store.json` is immutable brownfield evidence. Compatibility
  routes read it as the initial seed and persist changes to the ignored
  `data/learning_store.runtime.json` working copy. Tests may override the
  working path with `SMART_DISPATCH_LEARNING_STORE_PATH`.

Runtime database, WAL/SHM/journal, startup-lock, compatibility working-copy,
backup, environment, and test artifacts are ignored by source control.

## Verification

Run the complete suite:

```bash
uv run pytest
```

The suite includes metadata, runtime, real file-backed SQLite, Alembic,
backup/restore, failure, canonical contract, idempotency, compatibility-route,
and process-level checks.
Playwright 1.60.0 is pinned for later browser stories, but its browser binary
is not installed or exercised by Story 1.2.

## Canonical Work Order API

`POST /api/v1/work-orders` is the first canonical command. It requires:

- `Content-Type: application/json` with an optional charset parameter;
- a nonblank, route-scoped `Idempotency-Key`;
- a received body of at most 1,048,576 bytes;
- nonblank string fields `incident_text`, `address`, and `zone`;
- optional `context` as a JSON object; and
- no unknown top-level fields.

Successful capture returns `201` in the versioned success envelope. Stable
error envelopes cover conflict (`409`), oversized body (`413`), unsupported
media (`415`), contract validation (`422`), and sanitized persistence failure
(`500`). The complete successful response is retained for byte-stable replay.

The `work_orders` table stores the captured semantic raw input and UTC creation
time. The generic `idempotency_records` table stores the route/key hash and
retained response. Both writes share one transaction. Story 1.2 does not
classify, prioritize, score, create Dispatch Runs, or alter the browser flow.

## Internal Analyze capability

Story 1.3 adds `AnalyzeWorkOrder`, an internal application command rather than
a public HTTP endpoint. It reads a captured Work Order and uses the local,
network-free `analysis-v1` registry to derive category, priority, SLA minutes,
canonical certification codes, and estimated service duration.

Each field carries `supplied`, `inferred`, or `defaulted` provenance. Explicit
values are recognized only under `context.dispatch_requirements`; deterministic
rules identify their version and rule ID; defaults and ambiguity produce
structured warnings without copying the incident, address, or supplied value.
The strict `AnalyzeInputV1` and `AnalyzeOutputV1` contracts reject unknown or
malformed content before persistence.

The immutable registry is stored in `configuration_versions` with its SHA-256
digest. Validated canonical results are stored once per Work Order and
configuration in `work_order_analyses`. A retry revalidates and returns the
retained result. Story 1.7 will invoke the same self-contained capability from
an immutable run snapshot and will own stage execution and State Transitions.

## Internal eligibility capability

Story 1.4 adds `DetermineTechnicianEligibility` and the pure
`EligibilityPolicy`. They evaluate every Technician against availability,
complete certification coverage, shift feasibility, the 480-minute workday,
the 240-minute driving limit, and required EPP before any score exists. All
six results are retained even when an earlier check fails. Priority, distance,
and Memory cannot restore an ineligible candidate.

`EligibilityInputV1` is a self-contained, UTC-captured snapshot and accepts
zero to 100 canonically ordered Technicians. `eligibility-v1` enables every
check and is persisted with the full immutable registry digest. Missing
driving or applicable EPP evidence fails closed with a structured warning.
Exact limits pass; one minute over fails.

Validated batches are append-only in `eligibility_evaluation_sets` and replay
only for the same analysis, configuration, and canonical input hash. These
rows are pre-run diagnostic evidence, not authoritative Dispatch Run state.
Story 1.5 must consume the same immutable Technician snapshots plus the
validated eligibility partition and must never reload mutable rows or score
an ineligible Technician. Story 1.7 owns authoritative PLAN evidence and State
Transitions.

## Internal deterministic scoring capability

Story 1.5 adds `ScoreEligibleTechnicians` and the pure `ScoringPolicy`. The
command revalidates the retained Analyze and eligibility evidence, derives SLA,
ETA, distance, and projected workload from those immutable sources, and accepts
only one optional canonical Decimal quality rating per Technician. Ineligible
Technicians retain their full six-check evidence and never receive scoring
fields.

`scoring-v1` calculates SLA, proximity, workload balance, quality, and neutral
Memory components with task-local Decimal arithmetic. It applies only the
versioned distance penalty, ranks on unrounded values through the full
tie-break chain, and exposes raw inputs, normalized values, weights,
contributions, penalties, and quality-fallback warnings. Binary floating-point
input and intermediate two-place presentation rounding are forbidden.

Validated batches are append-only in `scoring_evaluation_sets` and replay only
for the same eligibility set, configuration, and canonical input hash.
Configuration, source, JSON, hash, partition, rank, and top-summary evidence is
revalidated on every read. These rows remain pre-run diagnostic evidence.
Story 1.6 owns confidence/explanation, Story 1.7 owns authoritative PLAN and
recommendation state, and Story 3.2 owns a future explicitly versioned active
Semantic Pattern integration.

## Brownfield compatibility

The existing `/api/*` behavior is temporarily mounted through
`app/adapters/legacy/compatibility.py`. It is a preserved migration surface,
not the canonical `/api/v1` design. Story 1.4 corrected its isolated
priority-5 overtime defect: projected work over eight hours is rejected for
every priority without changing the legacy response shape.

## Security boundary

This is a local course prototype. Wildcard CORS is not enabled. Authentication,
authorization, HTTPS termination, retention policy, and non-loopback serving
must be designed before any external or production use.
## Internal recommendation confidence (Story 1.6)

The application now includes a deterministic internal `confidence-v1`
evaluation over retained Story 1.5 scoring evidence. It calculates data
quality, historical evidence, score margin, and condition certainty with
Decimal arithmetic; stores structured source warnings and a registry-owned
explanation template; and retains replay-safe evidence in
`confidence_evaluation_sets`.

This capability is intentionally not a public endpoint or Dispatch Run.
Story 1.7 will invoke the same policy from an authoritative run snapshot,
and Story 1.9 will display the separate Objective Score and Recommendation
Confidence values in the browser.

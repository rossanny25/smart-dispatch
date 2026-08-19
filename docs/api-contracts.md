# Current API Contracts

Base URL: same origin as the browser. Content type: JSON except for static assets.
API routes require a valid `smart_dispatch_session` cookie created by
`POST /auth/login`.

## GET `/api/technicians`

Returns the SQLite-backed runtime technician roster. The table is bootstrapped
from `data/seeds/technicians.json` only when empty.

## POST `/api/technicians`

Requires role `admin`. Creates a technician with name, status, zone,
certifications, shift, active workload, rating, PPE, and GPS coordinates.
Invalid payloads return `422`.

## PATCH `/api/technicians/{technician_id}`

Requires role `admin`. Updates technician operational fields. Changes affect
the next dispatch simulation immediately.

## GET `/api/orders`

Returns SQLite-backed operational demo orders bootstrapped from
`data/seeds/orders.json`.

## GET `/api/memory/learning`

Returns the JSON learning store. On read failure, returns an empty array with HTTP 200, so absence and failure are indistinguishable.

## POST `/api/orders`

Required body fields:

```json
{
  "raw_text": "string",
  "address": "string",
  "zone": "string"
}
```

Returns HTTP 201 with a heuristically classified order. Low-information text
without a recognizable service incident or usable numbered address returns
`422` with an actionable message.

## POST `/api/dispatch/simulate`

Request:

```json
{
  "order_id": "order_001",
  "environment": {
    "weather": "soleado",
    "traffic": "normal",
    "gps_signal": "online"
  }
}
```

Response includes `dispatch_state`, `recommended_assignment`, ranked
`candidates`, hard-rule checks, recommendation confidence, and `agent_logs`.
`dispatch_state` is `WAIT_FOR_DECISION` when a recommendation exists and
`NO_FEASIBLE_CANDIDATES` when every candidate is rejected. The compatibility
contract still lacks full canonical run state, data freshness, and a stable
error envelope.

## POST `/api/dispatch/confirm`

Accepts an order, selected technician, override flag/feedback, and optional
real duration. It updates SQLite-backed order state, increments the selected
technician workload in SQLite, may write learning records, and returns
the created `visit`. If the same order was already confirmed, it returns the
existing visit with `learnings_updated: []` and does not increment workload
again.

## GET `/api/visits`

Returns SQLite-backed service visits for the calendar view, including order,
technician, zone, time window, duration, feedback, and status. Technician names
are resolved from the current SQLite technician roster when available.

## POST `/api/visits`

Creates a manually scheduled visit with `technician_id`, client, address, zone,
scheduled start, duration, and optional category/comment. The default status is
`programada`.

## PATCH `/api/visits/{visit_id}`

Updates visit `status`. Supported values are `programada`, `en_curso`,
`completada`, and `cancelada`.

## POST `/api/reset`

Reloads runtime technicians and SQLite-backed demo orders from seeds, and
restores the learning runtime file from `data/learning_store.json`. It also
clears SQLite-backed service visits.

## GET `/api/v1/admin/users`

Requires role `admin`. Returns persisted application users without password
material.

## POST `/api/v1/admin/users`

Requires role `admin` and `Idempotency-Key`. Creates a user with `username`,
`display_name`, `role`, and `password`. Passwords are stored as PBKDF2 hashes.

## PATCH `/api/v1/admin/users/{user_id}`

Requires role `admin` and `Idempotency-Key`. Updates display name, role, active
state, and optionally password. The API rejects attempts to disable or demote
the last active admin.

## Required Contract Evolution

The PRD requires:

- a stable `run_id` and state on every dispatch response;
- schema-versioned request/response objects;
- structured `constraint_checks`;
- `score_total` plus normalized component values, weights, contributions, and penalties;
- `confidence` separate from score, with its factors;
- data-quality/freshness warnings;
- all alternatives with eligibility and discard reasons;
- structured errors, including `NO_FEASIBLE_CANDIDATES`;
- KPI and scenario-comparison endpoints or equivalent export.

# Current API Contracts

Base URL: same origin as the browser. Content type: JSON except for static assets.

## GET `/api/technicians`

Returns the in-memory technician array. No authentication, filtering, pagination, or error envelope.

## GET `/api/orders`

Returns the in-memory work-order array.

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

Returns HTTP 201 with a heuristically classified order. Validation covers only field presence.

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

Response includes `recommended_assignment`, ranked `candidates`, and `agent_logs`. The implemented contract lacks run state, per-component score breakdown, hard-rule evidence, recommendation confidence, data freshness, and structured discard reasons.

## POST `/api/dispatch/confirm`

Accepts an order, selected technician, override flag/feedback, and optional real duration. It mutates in-memory order/workload state and may write learning records to JSON.

## POST `/api/reset`

Resets in-memory workloads and order statuses. It does not reliably restore the learning file to its original seed because initialization only writes when the file is absent.

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


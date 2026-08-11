# Current and Required Data Models

## Current Models

### Technician

Fields include identifier, name, status, zone, certifications, shift, active workload hours, rating, and GPS coordinates. Records are hard-coded and mutable in memory.

### Work Order

Fields include identifier, client, address, zone, raw text, status, creation time, and heuristic structured data containing category, priority, and required skills.

### Candidate

Produced transiently during simulation. It contains technician identity, total score, estimated travel, distance, workload, memory bonus, GPS status, validation status, and alerts.

### Learning Record

Persisted in `data/learning_store.json`: key, type, free-form content/parameters, confidence, and update timestamp. Episodic evidence and semantic conclusions are not separated.

## Required SQLite Conceptual Model

| Entity | Purpose |
|---|---|
| `dispatch_runs` | One orchestration run, current/final state, start/end, duration, input snapshot, error |
| `agent_executions` | Stage-level input/output, schema version, timestamps, duration, status |
| `orders` | Durable operational order state |
| `technicians` | Durable technician profile, availability, shift, workload, quality |
| `candidate_evaluations` | Eligibility checks, normalized components, penalties, total score, confidence |
| `human_decisions` | Accept/override/no-assignment decision and reason |
| `service_outcomes` | Actual duration, completion, first-time fix, operational result |
| `episodic_events` | Immutable observations tied to run/order/decision/outcome |
| `semantic_patterns` | Aggregated preference/calibration, sample count, confidence, decay metadata |
| `kpi_events` | Inputs needed to compute prototype KPIs reproducibly |
| `configuration_versions` | Scoring weights, thresholds, SLA and learning policy used by each run |

## Integrity Requirements

- A semantic pattern references its supporting episodes.
- One observation cannot directly create a definitive semantic rule.
- Contradictory observations reduce confidence.
- Age decay is deterministic and configurable.
- Promotion requires a configured minimum sample count.
- Each candidate evaluation records the exact configuration version used.
- Run state transitions and decision/outcome writes are transactional.

## Migration

Existing technician/order seed data and `learning_store.json` should be imported through a repeatable migration. Existing learning items must be marked as seeded assumptions unless supporting episodes are also synthesized and clearly labeled.


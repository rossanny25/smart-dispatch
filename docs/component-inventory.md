# UI Component Inventory

The frontend is a single static page; components are semantic DOM regions rather than framework components.

| Area | Responsibility | Source |
|---|---|---|
| Order form | Captures raw issue, address, and zone | `frontend/index.html`, `main.js` |
| Environment controls | Selects weather, traffic, and GPS scenario | `frontend/index.html`, `main.js` |
| Order list | Shows pending/completed orders and dispatch action | `renderOrders()` |
| Technician grid | Shows availability, zone, workload, rating, certifications | `renderTechnicians()` |
| Agent timeline | Animates capture/analyze/plan/evaluate/learn | `startAgentSimulation()` |
| Agent details | Displays narrative “thought” and JSON output | `showAgentDetails()` |
| Recommendation card | Shows selected technician, narrative, and travel time | `startAgentSimulation()` |
| Override form | Allows human selection and feedback | confirmation handlers |
| Completion modal | Captures actual duration and feedback | completion handlers |
| Memory list | Shows persisted learning descriptions/confidence | `renderMemory()` |

## Required UI Additions

- Current orchestration state and run identifier.
- Per-stage duration and outcome.
- Hard-constraint checklist.
- Score component breakdown.
- Recommendation confidence and its factors.
- Freshness/quality warnings for GPS, weather, and traffic.
- Eligible and ineligible alternatives with discard reasons.
- Clear no-feasible-candidate state.
- KPI panel and memory-enabled versus memory-disabled comparison.

The “thought trace” panel should be reframed as decision evidence: structured inputs, checks, outputs, and explanations, without implying exposure of private chain-of-thought.


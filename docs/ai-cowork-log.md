# AI Co-Work Log

This document records how AI was used during development and what needed human judgment.

## Where AI Helped

| Area | Contribution |
| --- | --- |
| Professor feedback analysis | Converted conceptual critique into implementable priorities: deterministic orchestration, objective function, memory policy, metrics, confidence, and explainability. |
| PRD and architecture | Helped structure product requirements, architecture decisions, and BMad implementation stories. |
| Code implementation | Assisted with FastAPI contracts, domain policies, persistence patterns, migrations, and tests. |
| Dockerization | Added Dockerfile, Compose service, runtime port variables, and verification notes for port `8050`. |
| Documentation | Drafted runbook, final delivery guide, diagrams, UX review, cybersecurity log, and report skeleton. |

## What AI Got Wrong Or Needed Correction

- Some generated or inherited documentation still described an older `http.server`/JSON-only state while the project had already moved toward FastAPI/SQLite.
- Local verification was affected by a moved `.venv` with broken absolute paths; the environment needed diagnosis rather than blind test repetition.
- Publishing strategy cannot be invented by AI; the team must decide GitHub visibility and deployment target.
- AI can draft diagrams and report text, but screenshots and live links must come from the real running project.

## What Was Surprising

- The professor's abstract feedback mapped cleanly to concrete engineering artifacts: state machine, immutable snapshots, confidence policy, and persisted evidence.
- Dockerization was small once runtime host/port became configurable.
- The project can now support both local-safe execution on `8000` and container demo execution on `8050`.

## Responsible AI Boundary

The proposed future LLM/SLM role is limited to optional text interpretation in ANALYZE. The model must not:

- Advance State Transitions.
- Override hard constraints.
- Score ineligible technicians.
- Invent private reasoning as evidence.
- Bypass strict JSON contract validation.

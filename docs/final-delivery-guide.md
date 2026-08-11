# Final Delivery Guide

This guide maps the teacher's final-cycle feedback to concrete project evidence.

## Required Links For Page 1

- Live app URL: `https://smart-dispatch-q4xk.onrender.com`
- GitHub repository URL: `https://github.com/rossanny25/smart-dispatch`
- Docker/local demo URL: `http://127.0.0.1:8050` after running `docker compose up --build`.

The teacher evaluates the published working project first, so these links must appear on the first page of the final PDF.

Render Free note: the live app can take approximately 50 seconds or more to wake up after inactivity.

## Evidence To Capture

- Architecture diagram: use the current state-machine and hexagonal architecture from `docs/architecture.md`.
- UML diagram: include the Dispatch Run, StageExecution, StateTransition, WorkOrder, Technician, and Memory entities.
- Technology table: Python 3.12, FastAPI, Pydantic, SQLAlchemy Core, Alembic, SQLite, vanilla HTML/CSS/JS, Docker.
- Frontend screenshots: home page, work-order list, dispatch simulation result, recommendation evidence.
- Real usage log: one end-to-end session showing app startup, work order capture or simulation, recommendation, alternatives, and state evidence.
- UX/UI self-evaluation: Nielsen heuristic review focused on dispatcher users.
- Cybersecurity log: at least four risks and mitigations, including local-only binding defaults, 1 MiB JSON limit, structured error envelopes, no raw GPS/address logging, dependency pinning, and SQLite backup before migrations.
- AI co-work section: describe where AI helped with specs, tests, Dockerization, state-machine design, and where it needed correction.

## LLM/SLM Reflection

Recommended architecture role:

- Keep deterministic rules, scoring, confidence, and state transitions authoritative.
- Use a local LLM/SLM only as an optional Analyze adapter that converts incident text into structured fields validated by the same Pydantic contracts.
- Record provider/model metadata and never allow the model to advance state or override hard constraints.

What it adds:

- Better natural-language incident interpretation.
- Dispatcher-facing summaries and clearer explanation templates.
- Professional insight into ambiguous service descriptions and missing operational data.

Limits versus cloud APIs:

- Lower accuracy on specialized Spanish operational text unless carefully tested.
- More local hardware and latency constraints.
- Harder model lifecycle management.
- Better privacy and offline demonstration value.

Optional demo:

- Run Ollama locally and ask a project question, then include the screenshot as non-authoritative evidence.

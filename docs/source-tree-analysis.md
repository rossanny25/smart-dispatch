# Source Tree Analysis

> Historical snapshot: this file describes the first brownfield prototype. The
> current source tree and delivery status live in `AGENTS.md` and
> `docs/ai-project-status.md`.

```text
smart-dispatch-ia-spec-v2/
├── server.py                 # Python entry point, API, orchestration simulation, persistence
├── frontend/
│   ├── index.html            # Dashboard structure
│   ├── index.css             # Complete visual system and responsive layout
│   └── main.js               # Browser state, rendering, API calls, simulated timeline
├── data/
│   └── learning_store.json   # Current persistent learning store
├── prompts/                  # Five agent role/output prompt specifications
├── spec/                     # Existing distributed product/system specification
├── docs/
│   ├── CONTEXT.md
│   ├── TASKS.md
│   └── PLAN_FEEDBACK_PROFESOR.md
└── _bmad/                    # BMad workflow configuration and utilities
```

## Critical Entry Points

- Runtime: `server.py`
- Browser document: `frontend/index.html`
- Browser behavior: `frontend/main.js`
- Product feedback change signal: `docs/PLAN_FEEDBACK_PROFESOR.md`
- Existing requirements corpus: `spec/`

## Integration Points

The original frontend used same-origin `fetch` calls to `/api/*`, and the first
server version read/wrote `data/learning_store.json`. The current application is
served by FastAPI, uses SQLite for runtime persistence, and includes
single-user login. There are still no external model, map, traffic, or weather
integrations.

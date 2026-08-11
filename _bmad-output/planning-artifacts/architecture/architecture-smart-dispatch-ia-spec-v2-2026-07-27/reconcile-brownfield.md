# Brownfield Reconciliation — Smart Dispatch IA v2.1

## Scope

This reconciliation compares `docs/index.md` and the linked brownfield documentation with:

- `ARCHITECTURE-SPINE.md`
- `ACADEMIC-ARCHITECTURE.md`

It is a review artifact only. It does not amend either architecture deliverable.

## Executive Result

The proposed architecture is directionally consistent with the documented target: it correctly replaces the synchronous, state-less prototype with a deterministic orchestrator; separates hard constraints from scoring; moves volatile/JSON state to SQLite; keeps the existing vanilla JavaScript UI; and treats optional LLM stages as replaceable adapters.

It is not yet safe to hand directly to story generation without resolving four load-bearing contradictions:

1. the named `PLAN`/`EVALUATE` stages still permit two incompatible implementations of “constraints before ranking”;
2. the state machine cannot represent a decision recorded before its later service outcome;
3. the promised incremental migration lacks a compatibility contract for the existing browser API;
4. the target runtime is Python 3.14.6 while the inspected project runtime is Python 3.9.6 and the repository has no dependency manifest.

The remaining findings are migration and operating-envelope omissions that should become explicit architecture rules, deferred items, or acceptance criteria.

## What Landed Correctly

| Brownfield fact or required evolution | Architecture coverage | Assessment |
| --- | --- | --- |
| One Python process serves API and static SPA | AD-1, AD-9, AD-13; local deployment diagram | Preserved as a modular monolith rather than rewritten into distributed services. |
| Current inline handler owns routing, orchestration, policy, and persistence | AD-1, structural seed | Correctly decomposed behind application/domain/adapter boundaries. |
| No explicit run/state/transition persistence | AD-2, state diagram, `dispatch_runs` and `state_transitions` | Correct target invariant. |
| Skills filtered before ranking but other feasibility checks happen afterward | AD-3 | Correctly requires all enabled hard constraints before scoring. |
| Ad hoc capped score and no recommendation confidence | AD-4 and academic sections 7 and 13 | Correctly separates pure normalized score from confidence and defers rounding to presentation. |
| Operational state is process-local; learning is one JSON file | AD-5, AD-6, AD-13 and data model | Correctly establishes transactional SQLite ownership and episodic/semantic separation. |
| Agent outputs have no schemas | AD-7 | Correctly establishes strict versioned boundary contracts. |
| Browser animation presents already-computed work as agent progress | AD-2 and AD-9 | Correctly makes the persisted backend state authoritative. |
| UI exposes simulated “thought” text | AD-11 | Correctly replaces private reasoning claims with structured evidence. |
| No external model integrations exist | AD-12 | Correctly keeps deterministic local stages as the demonstration baseline. |
| No tests or deployment definition exist | AD-15 and academic section 13 | Correctly supplies a layered verification target. |
| Current `alerts.push(...)` defect | Academic migration step 1 | Explicitly acknowledged before behavioral migration. |
| CORS is unrestricted and there is no authentication | Deferred section and academic operations section | Appropriately constrained to local MVP use, though local binding still needs correction below. |

## Blocking Reconciliation Findings

### B1 — `PLAN` and `EVALUATE` have contradictory ownership

**Evidence**

- The current code and prompts generate/rank candidates in Planning, then reject excessive-workday candidates in Evaluation.
- AD-3 says every hard constraint must run before `ScoringPolicy`.
- The spine state diagram says `ANALYZE -> PLAN -> EVALUATE`, with the candidate set persisted on `PLAN -> EVALUATE`.
- The academic sequence bypasses a Planning component label: after Analyze, the orchestrator evaluates hard constraints and then scores, while the component model still lists separate eligibility, scoring, and stage adapters.

**Risk**

Two story teams could implement incompatible flows: one could preserve the current “rank then validate” semantics because the stage names and transition order imply it, while another could implement “eligibility then rank” as AD-3 requires.

**Required resolution**

Bind stage semantics, not just their order. One safe interpretation is:

- `CAPTURE`: normalize request;
- `ANALYZE`: classify priority, requirements, and durations;
- `PLAN`: evaluate all hard constraints, then score only eligible candidates and persist all candidate evidence;
- `EVALUATE`: validate completeness/consistency of the recommendation, calculate confidence/warnings, and produce the explanation without changing eligibility or rank.

Alternatively rename the states to the domain operations. Whichever choice is made must be identical in the state diagram, stage contracts, prompt/adaptor responsibilities, and academic sequence.

### B2 — Decision and outcome lifecycle is not representable

**Evidence**

- The spine transitions only from `WAIT_FOR_DECISION` to `LEARN` when “decision and outcome complete.”
- The academic API has separate decision and outcome endpoints.
- AD-5 defines one transaction per command, while academic section 8 says “recording a Human Decision and outcome is atomic.”
- The current browser captures assignment confirmation and service duration together, but the new API explicitly permits them to occur separately.

**Risk**

A decision may be persisted while the run remains misleadingly in `WAIT_FOR_DECISION`; or an implementation may incorrectly require a service outcome at dispatch time. Retry and idempotency behavior also becomes ambiguous across two resources.

**Required resolution**

Choose and encode one lifecycle:

- for the realistic separated flow, add `WAIT_FOR_OUTCOME` (`WAIT_FOR_DECISION -> WAIT_FOR_OUTCOME -> LEARN`), make each command independently atomic/idempotent, and define whether declines complete without an outcome; or
- deliberately keep the course UI’s combined command and remove the separate endpoints.

The first option better supports KPI evidence and future UI evolution.

### B3 — “Every migration step leaves a runnable system” lacks an API compatibility rule

**Evidence**

- The existing SPA consumes unversioned endpoints and bare arrays/objects:
  `/api/technicians`, `/api/orders`, `/api/memory/learning`,
  `/api/dispatch/simulate`, `/api/dispatch/confirm`, and `/api/reset`.
- AD-8 requires `/api/v1` envelopes and idempotency keys.
- AD-9 says the existing SPA is migrated to `/api/v1`.
- The structural seed calls `server.py` a temporary compatibility launcher, but a launcher alone does not preserve legacy routes or response shapes.

**Risk**

Introducing FastAPI, envelopes, or strict idempotency before the browser migration immediately breaks the only demonstrable user journey. Conversely, retaining both APIs without one authoritative application layer permits behavioral drift.

**Required resolution**

Add a migration invariant: legacy `/api/*` routes remain a thin compatibility adapter over the same application use cases until the SPA cutover is complete. Define a removal gate (all UJ smoke tests green against `/api/v1`) and prohibit duplicate business logic. The migration plan should identify the cutover order for reads, simulate/run creation, decision/outcome, memory display, and reset.

### B4 — Selected runtime is unavailable in the inspected environment

**Evidence**

- The target stack binds Python 3.14.6 and exact package versions.
- The current project reports Python 3.9.6.
- Brownfield documentation records no third-party dependencies, lockfile, `pyproject.toml`, requirements file, build step, CI, or container.

**Risk**

Implementation cannot begin reproducibly on the current course environment, and Python/package incompatibilities may be discovered only after stories are underway.

**Required resolution**

Either:

- lower the supported Python baseline to a version available to the course environment and verify every selected dependency against it; or
- add an explicit runtime provisioning mechanism and evaluator setup instructions.

The architecture also needs to bind the dependency/lock mechanism and executable development command. Exact dependency versions without a manifest are documentation, not a reproducible stack.

## High-Priority Migration and Integration Findings

### H1 — Existing identifiers conflict with the UUID convention

Current records and all browser flows use stable human-readable IDs such as `tech_01` and `order_001`; seeded learning records reference those technician IDs. The spine declares all IDs opaque UUID strings but does not define mapping.

Changing primary identifiers during import can orphan learning parameters and break fixtures, UI references, and academic comparisons. Preserve legacy identifiers as immutable external/business keys and use separate UUID primary keys, or explicitly retain the legacy string IDs for the MVP. The import must verify referential integrity.

### H2 — The JSON learning import needs provenance and activation semantics

The academic document correctly says existing JSON learning items are imported as “seeded assumptions” without invented episodes. It does not say whether those assumptions are active scoring inputs. Today they immediately add a memory bonus; AD-6 says semantic patterns require linked episodes and controlled promotion.

Define imported records as one of:

- inactive seed hypotheses, excluded from authoritative memory score until evidence threshold is met; or
- explicitly synthetic fixture patterns, active only in named academic demo fixtures and never presented as learned operational truth.

The import should be checksum/version guarded, preserve the source JSON as an audit artifact or backup, and be safe to rerun without duplicates.

### H3 — Operational seed migration and reset semantics are incomplete

Technicians and two initial orders are Python module constants created with process-local timestamps; new order IDs are derived from the last four timestamp digits and can collide. Reset changes workload/status only and does not actually restore the learning file.

Define:

- canonical versioned fixture files for technicians, orders, zone distances, and learning assumptions;
- deterministic IDs and timestamps for comparable scenarios;
- whether migration imports only seed state or also any in-memory session state (normally impossible after shutdown);
- transactional reset scope, including whether it deletes user-created orders, runs, evidence, idempotency records, and semantic/episodic data;
- backup/export before destructive reset and an explicit UI confirmation contract.

### H4 — Legacy timestamp conversion is unspecified

Current `datetime.now().isoformat()` values are naive local timestamps, while the target requires UTC timestamps ending in `Z`. Importing them as UTC would shift evidence in the Buenos Aires environment.

The migration must interpret legacy naive timestamps using the documented source timezone, convert to UTC, and record migration provenance. Synthetic fixture timestamps should be fixed rather than regenerated on every seed/reset.

### H5 — Hard-rule corpus is not completely assigned

The linked business rules include:

- maximum four accumulated driving hours;
- EPP for priority 4 and 5;
- maximum shift/day;
- a priority-5 overtime exception requiring technician acceptance;
- a 50 km radius that is a recommendation rule unless the only critically certified technician is farther away.

The spine names availability, certifications, shift, maximum workday, and “enabled safety constraints,” but it does not decide the status of driving hours, EPP, emergency overtime, or the 50 km rule. The professor feedback describes maximum-day rules as hard constraints that cannot be overridden by learning, which conflicts with the older emergency-overtime exception.

Classify each legacy rule explicitly as adopted, superseded, configurable, hard, soft penalty, or deferred. Do not let “enabled constraints” turn safety policy into an implementation default. In particular, reconcile emergency overtime with the updated professor-feedback rule before stories are generated.

### H6 — Override eligibility is not bound

The legacy UI allows selecting every technician in the override dropdown, including technicians that can be ineligible. The proposed API names `INELIGIBLE_OVERRIDE`, but neither deliverable states whether ineligible overrides are always rejected or whether any exception workflow exists.

Bind that human overrides may select only eligible alternatives unless a separately modeled, auditable exception policy exists. Memory must never promote an override that violated eligibility.

### H7 — Static serving and browser asset migration are omitted

The current Python server serves `/`, `/index.html`, `/index.css`, and `/main.js`; the architecture does not assign static-file ownership in FastAPI or define browser fallback behavior. `frontend/index.html` also depends on the Font Awesome CDN, so the UI is not fully offline even though the deterministic demo is intended to work without network access.

Add a static-file adapter decision or development/deployment convention, preserve same-origin operation, and either vendor essential icons or document graceful no-network rendering.

### H8 — Localhost claim conflicts with current network binding

The existing server binds to `""` (all interfaces), while the academic architecture repeatedly describes a localhost-only MVP. Open CORS plus all-interface binding is broader than the stated operating envelope.

The target launcher should default explicitly to `127.0.0.1`; any non-loopback bind must be opt-in and must trigger the deferred security requirements.

### H9 — Single process does not fully define concurrency

FastAPI/Uvicorn can overlap requests even with one process. Decision, outcome, reset, and run advancement can race unless the application defines optimistic locking or a per-run serialization rule. WAL and busy timeout address SQLite lock contention, not duplicate state transitions.

Add a run-version/revision precondition or equivalent compare-and-swap transition update, uniqueness constraints for one decision/outcome per run where applicable, and conflict semantics (`409 CONFLICT`). Reset must not race with active commands.

### H10 — Migration failure and rollback behavior is missing

“Alembic migrations run before serving” is sound but incomplete for a course demo. Define startup failure as fail-closed with a clear message, take a SQLite backup before destructive/schema-changing migration, and document restoration. Do not automatically recreate an unreadable database and lose evidence.

## Medium-Priority Contract and Operational Findings

### M1 — Idempotency scope is inconsistent

AD-8 lists run, decision, outcome, replay, and reset commands, but omits `POST /work-orders` and scenario comparison; the academic document says all mutating commands use a key. Bind the rule once: every externally invoked mutating command requires idempotency, with key scope, request-hash conflict behavior, retention period, and persisted response semantics.

### M2 — API surface omits memory inspection despite preserving the UI

The existing UI renders the semantic-memory list. The minimum `/api/v1` table has no semantic-pattern query. Either add a read endpoint/view for evidence-backed patterns or explicitly remove/redesign that UI region. The browser should show provenance, sample count, status, confidence, and decay rather than the old free-form record alone.

### M3 — Request limits and malformed-content behavior remain undefined

The current server accepts unbounded `Content-Length`, does not require JSON content type, and has inconsistent HTML/JSON errors. Pydantic fixes shape validation but not body-size limits, timeouts, or malformed transport behavior. Define a local-MVP payload limit and stable `413`, `415`, and validation responses.

### M4 — Structured logging needs a usable destination and retention rule

AD conventions define JSON fields and privacy exclusions, but do not state stdout versus file, rotation/retention, log level, or how the evaluator obtains evidence. For a local course project, stdout plus explicit evidence export may be sufficient; make that choice clear and keep authoritative evidence in SQLite rather than logs.

### M5 — Address/GPS privacy is narrower than actual browser and database handling

The architecture prohibits raw address/exact GPS in structured logs and semantic patterns, which is good. The operational snapshots and current UI still contain them. State that the academic fixtures use synthetic data, and identify which SQLite evidence fields may contain address/GPS. Real-data retention is deferred, but accidental use should be guarded by documentation and fixture labeling.

### M6 — Error paths in the state machine are partial

Only CAPTURE through EVALUATE have arrows to `FAILED`. Decision, outcome, learning, evidence export, and reset can also fail. Decide whether failures after `WAIT_FOR_DECISION` leave the run retryable in place, transition to a typed terminal state, or create command-level failures without changing run state. This is necessary for idempotent recovery.

### M7 — “Persist each stage before the next begins” and one transaction per command need command boundaries

If starting a run executes the entire pipeline as one HTTP command, AD-2 appears to require durable commits between stages while AD-5 says one transaction per command. A single transaction cannot both commit each transition durably and roll back every write from the command.

Define whether each stage is its own internal command/transaction, or whether “persisted” means flushed within a single transaction. For crash-resumable evidence, stage-level transactions plus an orchestrator retry policy are preferable.

### M8 — Seed paths and working-directory dependence should be eliminated

Current `data/` and `frontend/` paths resolve from the caller’s working directory, and the port is hard-coded. The new composition root should resolve project-relative paths from the installed/application location; environment variables may select database path, bind host, port, and fixture set without changing business configuration.

### M9 — Browser compatibility should include failure states, not only happy-path smoke tests

The current JavaScript marks timeline steps completed even if the API request fails, ignores non-2xx response bodies, and uses an alert for no feasible candidates. Migration acceptance should cover typed API errors, retry/idempotency, stale run polling, `NO_FEASIBLE_CANDIDATES`, and partial decision/outcome lifecycle.

### M10 — Existing DOM rendering creates an avoidable local injection path

User-entered and API-returned values are interpolated into `innerHTML` in multiple lists/cards. Even for a local prototype, a crafted order or technician value can become executable markup. The browser migration should use `textContent` or escaping for untrusted fields; this need not expand into a full production-security program.

## Documentation Contradictions to Mark as Superseded

The linked older context, backlog, and specification describe Node.js/Express, React/Vite, vector memory, PostgreSQL/pgvector, autonomous/cyclic agents, and exposed thought traces. The brownfield scan proves the implementation is Python standard library plus vanilla JavaScript and JSON.

The architecture correctly chooses Python/FastAPI, vanilla JavaScript, SQLite, deterministic stages, statistical semantic patterns, and structured evidence. To prevent future implementers from treating the old documents as parallel requirements, the architecture package or documentation index should label these older technology and trace descriptions as historical/superseded. Their business intent remains useful; their stack and “chain-of-thought” presentation do not.

## Proposed Brownfield Migration Gates

These gates make the academic section’s “each step remains runnable” claim verifiable.

| Gate | Exit condition |
| --- | --- |
| G0 — Characterize | Legacy happy paths and the no-candidate/error paths have executable characterization tests; `alerts.push` regression is captured and fixed. |
| G1 — Reproducible runtime | Supported Python version, locked dependencies, setup command, host/port configuration, and offline/static-asset behavior work on the evaluator environment. |
| G2 — Application seam | Legacy routes call application use cases through a compatibility adapter; no business rule remains duplicated in HTTP handlers. |
| G3 — Durable seed | Alembic schema applies to a blank DB; versioned fixtures import deterministically; JSON learning import is idempotent, provenance-labeled, and backed up. |
| G4 — Policy correctness | All adopted hard constraints execute before scoring; stage ownership is unambiguous; pure policy tests pass. |
| G5 — Durable orchestration | State transitions, stage transactions, retry/conflict behavior, and decision/outcome lifecycle pass crash/retry integration tests. |
| G6 — `/api/v1` cutover | SPA consumes versioned envelopes and idempotent commands; semantic-memory UI has a supported query; legacy contract tests still pass. |
| G7 — Remove compatibility | UJ-1–UJ-3, no-feasible, error/retry, reset, KPI, comparison, and evidence flows pass exclusively through `/api/v1`; only then remove legacy routes and `server.py`. |

## Recommended Architecture Amendments

Before finalization, amend the architecture artifacts or memlog to bind:

1. exact ownership/semantics of PLAN and EVALUATE;
2. the decision-to-outcome intermediate state;
3. a legacy API compatibility adapter and removal gate;
4. supported Python baseline plus dependency lock/provisioning;
5. identifier preservation/mapping and timestamp conversion;
6. seeded-learning activation and migration provenance;
7. explicit disposition of driving-hours, EPP, emergency-overtime, and 50 km rules;
8. ineligible-override policy;
9. loopback binding, static asset ownership, and offline behavior;
10. per-run concurrency and stage transaction boundaries.

Once these are resolved, the spine will be a reliable substrate for epics and stories rather than a target design that still allows incompatible migration implementations.

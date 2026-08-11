# Adversarial Seam Review — Architecture Spine

**Artifact reviewed:** `ARCHITECTURE-SPINE.md`  
**Lens:** independently implemented epics that obey every current AD but still disagree at integration seams  
**Verdict:** **Changes required before epic decomposition.** The spine is directionally strong and fixes the main business invariants, but it leaves several cross-epic protocols and owners underdetermined. Two compliant teams can produce incompatible behavior around stage commits, learning completion, snapshots, KPI derivation, replay/reset, and the HTTP contract.

## Severity summary

| Severity | Count |
| --- | ---: |
| Critical | 2 |
| High | 5 |
| Medium | 4 |
| Low | 1 |

## Critical findings

### C-1 — Stage execution and transition persistence do not define one crash-safe protocol

**Current rules involved:** AD-2, AD-5, AD-7, AD-18, AD-20.

**Independent compliant builds**

- **Epic A — Orchestration:** opens a stage transaction, writes a `StageExecution(status="started")`, calls the stage adapter outside that transaction, then opens a second transaction that writes the output, appends the transition, and increments `dispatch_runs.revision`.
- **Epic B — Persistence:** interprets “each stage advancement is an internal command with its own transaction” as one transaction after the stage returns, and therefore writes `StageExecution(status="completed")`, output snapshot, transition, and revision together. It never persists `started`.
- **Epic C — Recovery:** sees a run whose current state is `ANALYZE` and latest execution is `started`; it retries the stage. Another compliant implementation treats this as a terminal typed failure because AD-2 says each execution is persisted before the next stage.

All three respect one transaction per command, optimistic concurrency, validation before transition, and recorded stage execution. They disagree after a process crash, timeout, or adapter exception. The result can be a permanently stranded run, duplicate stage attempts, or two different transition histories for the same request.

**Why this is critical:** State mutation is the center of the system. This ambiguity affects determinism, evidence integrity, retry safety, and the meaning of `dispatch_runs.revision`.

**Required architectural decision**

Define a single stage-attempt protocol, including:

1. whether `started` is durable;
2. the transaction boundaries before and after adapter invocation;
3. attempt identity and uniqueness;
4. which record owns current state;
5. the atomic set written on success;
6. the atomic set written on validation or execution failure;
7. recovery behavior for an interrupted attempt;
8. whether local deterministic stages may be retried automatically;
9. when and how revision is compared and incremented.

**Recommended rule:** A stage has an immutable `stage_attempt_id`. Persist `started` without advancing state; invoke the adapter; then atomically persist the validated output reference, terminal attempt status, transition, and compare-and-swap revision. On restart, a non-terminal attempt is deterministically marked `interrupted`; a new attempt may be created only under an explicit retry command and uniqueness guard. The transition log, not `StageExecution`, is the authority for current state, while `dispatch_runs.current_state` is a transactionally maintained projection.

**Disposition:** Autofix by strengthening AD-2/AD-20 or adding a dedicated stage-attempt AD.

### C-2 — `RecordOutcome → LEARN → COMPLETED` has no owner or exactly-once completion protocol

**Current rules involved:** AD-5, AD-6, AD-17, AD-18, AD-20.

**Independent compliant builds**

- **Epic A — Outcome capture:** `RecordOutcome` persists the outcome and moves the run to `LEARN`, then returns immediately because AD-17 says the command is atomic and separate from later learning.
- **Epic B — Learning:** expects an explicit `RunLearning` API command to invoke `LearningService`.
- **Epic C — Orchestration:** invokes learning synchronously after `RecordOutcome` commits and moves the run to `COMPLETED`.
- **Epic D — Recovery:** scans `LEARN` runs on startup and replays learning, potentially applying the same episode twice if Epic C updated Semantic Patterns before crashing but did not persist the final transition.

Each implementation can claim compliance: learning starts only after the outcome, only `LearningService` writes Semantic Patterns, and commands have independent transactions. Yet the integrated system can leave runs forever in `LEARN`, update patterns twice, or expose `COMPLETED` before learning evidence exists.

**Why this is critical:** It threatens the central academic claim that repeated evidence changes recommendations conservatively and reproducibly.

**Required architectural decision**

Name the application owner of the post-outcome workflow and define exactly-once semantics at the episode-to-pattern seam.

**Recommended rule:** `RecordOutcome` atomically appends the outcome, creates exactly one immutable episode with a unique `source_outcome_id`, and transitions to `LEARN`. The orchestrator then issues an idempotent `ApplyLearning(run_id, episode_id)` command. Learning derives/recomputes affected patterns from linked canonical episodes or records a unique application keyed by `(pattern_key, episode_id)`. Only the successful learning command may transition `LEARN → COMPLETED`. Startup recovery resumes runs in `LEARN` through the same idempotent command.

**Disposition:** Autofix with a new workflow/ownership AD and reflect it in the state diagram.

## High findings

### H-1 — Snapshot ownership is unclear: reference, deep copy, or event projection

**Current rules involved:** AD-4, AD-10, AD-14, AD-16; Structural Seed ER diagram.

**Independent compliant builds**

- **Work-order epic:** persists a mutable `work_orders` row and stores its ID in `dispatch_runs`.
- **Run epic:** copies Work Order fields into a JSON run snapshot but keeps Technician IDs pointing to mutable roster rows.
- **Scenario epic:** treats the immutable `scenario_fixtures` row as the snapshot and resolves current relational entities when replaying.

Every implementation “captures” the inputs and configuration, but later technician edits, fixture changes, or migration corrections produce different replays. The ER diagram reinforces references while AD-10 requires immutability without deciding how it is achieved.

**Required architectural decision**

Designate a canonical immutable `RunSnapshot` aggregate and state whether all computation reads its stored value payload or may dereference operational tables. Define ownership of raw input, normalized Work Order, roster, environment, time, configuration, memory mode, and snapshot hash. Clarify that operational tables are source inputs only and never computation dependencies after run creation.

**Disposition:** Autofix by strengthening AD-10 and adding `RUN_SNAPSHOTS` to the structural seed/ER diagram.

### H-2 — The API convention is not an API contract

**Current rules involved:** AD-7, AD-8, AD-19, AD-20; Consistency Conventions.

**Independent compliant builds**

- **Backend epic:** exposes `POST /api/v1/runs`, `POST /runs/{id}/decision`, and returns `202` while stages continue.
- **Frontend epic:** expects `POST /api/v1/scenarios/{id}/simulate`, a completed result in one `200` response, and uses `POST /runs/{id}/outcomes`.
- **Replay epic:** models replay as `POST /runs/{id}/replay`; another models it as creation with `replay_of`.

All use `/api/v1`, Pydantic, envelopes, stable errors, and idempotency. They remain incompatible on route shape, synchronous/asynchronous behavior, resource representation, allowed state per command, status codes, revision preconditions, and polling.

**Required architectural decision**

Bind the epics to one checked-in OpenAPI contract (or a terse route/command registry) before decomposition. It must define, at minimum, create/start/retrieve run, record decision, record outcome, retry, replay, comparison, KPI query/report, reset, fixture retrieval, and error/status semantics. Decide whether a run command completes the deterministic pipeline synchronously or returns an operation resource.

**Disposition:** Discuss only if synchronous versus operation-resource behavior is genuinely open; otherwise autofix as an API-contract ownership AD.

### H-3 — KPI facts and persisted `KPI_EVENTS` have competing source-of-truth interpretations

**Current rules involved:** AD-5, AD-14, AD-16; ER diagram and capability map.

**Independent compliant builds**

- **Metrics epic:** computes every KPI on demand from decisions, outcomes, stage executions, and run snapshots.
- **Evidence epic:** writes `KPI_EVENTS` at each command and queries those immutable facts.
- **Reporting epic:** materializes KPI results per window/configuration and reads the materialization for the academic report.

Each can meet the PRD formulas, but late outcomes, corrected timestamps, replay lineage, reset, and unavailable optional fields lead to different numerators and denominators. No current AD states whether `KPI_EVENTS` are canonical facts, projections, or cached results, nor who writes/invalidate/rebuilds them.

**Required architectural decision**

Choose one canonical evidence model. Recommended: domain events/operational records are the facts; KPI values are pure query results parameterized by explicit window and configuration version; any persisted KPI rows are rebuildable projections with a definition-version and never authoritative. Remove or relabel `KPI_EVENTS` in the seed if it is not canonical.

**Disposition:** Autofix with a KPI source-of-truth AD.

### H-4 — Replay and comparison lineage semantics are underdefined

**Current rules involved:** AD-8, AD-10, AD-14, AD-20.

**Independent compliant builds**

- **Replay epic:** resets the original run to `CAPTURE` and advances it again.
- **Run epic:** creates a new run with a copied snapshot and `replay_of_run_id`.
- **Comparison epic:** creates a pair from a fixture and compares any two run IDs later.
- **Memory epic:** reads the latest active Semantic Patterns at replay time; another freezes the original pattern set except for the on/off switch.

All can claim to replay the same snapshot and configuration. They differ in evidence preservation, identity, memory version, run history, and what “differ only by Memory Experiment Mode” means.

**Required architectural decision**

Replay must create a new immutable run, never mutate the source run. Add lineage (`source_run_id`, `fixture_id`, `comparison_group_id`) and define exactly which snapshot components are copied. For controlled comparison, both runs must share the same frozen semantic-pattern snapshot/version, with only reads/neutral memory contribution toggled; Episodic writes from one member must not affect the other before both results are complete.

**Disposition:** Autofix by strengthening AD-14 and AD-20.

### H-5 — `reset` is a destructive command with no bounded target or ownership rule

**Current rules involved:** AD-8, AD-20, AD-22; Deferred retention/deletion.

**Independent compliant builds**

- **Administration epic:** resets the whole database to seeded fixtures.
- **Scenario epic:** deletes runs belonging to one fixture.
- **Run epic:** resets one failed run to `CAPTURE`.
- **Learning epic:** preserves Semantic Patterns across reset; another deletes them to make a clean experiment.

All can require an idempotency key, a backup, and revision guards. The word `reset` still means four incompatible and materially destructive operations. Deferring retention/deletion does not safely defer this because reset is currently listed as a required mutating command.

**Required architectural decision**

Replace generic reset with bounded commands: e.g. `RetryFailedStage` (non-destructive, same run), `CreateReplay` (new run), and `RestoreSeedDataset` (explicit administrative operation that backs up and atomically replaces a named local dataset). State whether episodic evidence and Semantic Patterns are included. Do not expose an ambiguous `/reset`.

**Disposition:** Autofix; this is unsafe to leave to stories.

## Medium findings

### M-1 — Candidate evidence has no aggregate writer after PLAN

`PLAN` writes eligibility and scores; `EVALUATE` adds confidence, warnings, and explanation. One implementation updates the same `candidate_evaluations` rows, another appends evaluation versions, and another stores run-level recommendation evidence separately. All comply with AD-18. Define whether candidate evaluation records are immutable stage outputs, who assembles the recommendation snapshot, and which immutable artifact is captured by `RecordDecision`.

**Recommended disposition:** Add a recommendation/evidence aggregate owner: stage outputs are append-only; `EVALUATE` creates one immutable `RecommendationSnapshot` referencing PLAN evidence; the Human Decision references that snapshot.

### M-2 — Semantic Pattern identity and recomputation boundaries are not fixed

AD-6 names the only writer but not the pattern key, uniqueness, update strategy, or the relationship between active/inactive historical versions. Two learning implementations can group evidence by technician+service type versus skill+zone and both satisfy the PRD language. The PRD registry may define formulas and thresholds, but independently built persistence and learning epics still need a shared identity/version rule.

**Recommended disposition:** Bind a versioned pattern key/schema in the contract registry; make pattern versions immutable or define a single optimistic-update protocol; specify deterministic ordering and decay reference time.

### M-3 — Public identity conflicts with legacy identity rules

The conventions say “IDs are opaque UUID strings,” while AD-21 requires legacy string external IDs beside UUID primary keys. API, fixture, and migration epics can expose different IDs or accept both. Define UUID as the sole API resource ID and expose `external_id` only as labeled provenance, or explicitly define lookup behavior and collision scope.

**Recommended disposition:** Strengthen the identity convention and add uniqueness scopes.

### M-4 — Failure recovery is visible but not commandable

The state diagram makes `FAILED` terminal, while FR-3 calls errors recoverable and the conventions mention no retry contract. A UI may offer retry of the same run; the backend may require replay/new run. Decide whether `FAILED` is truly terminal and recovery always creates a new run, or add an explicit guarded retry transition/protocol. This must align with C-1 and the API contract.

**Recommended disposition:** Decide in the stage-attempt protocol; expose only the chosen recovery model.

## Low finding

### L-1 — Query freshness and ordering are unstated

Queries are side-effect free, but stable ordering for transitions, candidate alternatives, episodes, and KPI windows is not specified. SQLite iteration order can make otherwise deterministic outputs differ.

**Recommended disposition:** Add a convention requiring explicit total ordering and deterministic tie-breakers for every collection exposed by API or used in calculations.

## Adversarial integration scenarios

These scenarios should become architecture conformance tests before feature tests:

1. **Crash after stage adapter success but before transition commit:** restart and prove one deterministic recovery outcome, no duplicate completed attempt, and no unreferenced output.
2. **Crash after Semantic Pattern update but before `LEARN → COMPLETED`:** restart and prove the episode affects every pattern exactly once.
3. **Edit Technician and configuration after run creation:** retrieve/replay and prove the original result still reads only its immutable snapshot.
4. **Launch paired Memory on/off comparison:** prove both use the same frozen pattern version and neither run's episodic write contaminates its pair.
5. **Repeat an identical outcome command:** prove the same response is returned and no duplicate outcome, episode, learning application, or transition is created.
6. **Issue same idempotency key with a changed body:** prove `409`; issue a stale revision with a new key and prove the same stable conflict class.
7. **Restore seed dataset:** prove scope is explicit, backup succeeds first, no half-reset database is served, and the response identifies the new dataset generation.
8. **Compute KPI report before and after optional outcome fields arrive:** prove canonical facts and definition version yield one predictable availability/result change.
9. **Return tied candidate scores:** prove rank, alternative order, recommendation, and replay output use one stable tie-breaker.
10. **Submit outcome for accepted, overridden, declined, failed, and no-feasible runs:** prove one state guard table controls every accepted/rejected command.

## Minimum changes before epics

The smallest architecture patch that closes the dangerous seams is:

1. Add a crash-safe **stage-attempt and transition commit protocol**.
2. Add an idempotent **outcome-to-learning completion protocol** and recovery owner.
3. Make **RunSnapshot** the canonical immutable computation input.
4. Declare **OpenAPI/command registry ownership** and synchronous versus operation behavior.
5. Declare the **KPI source of truth** and role of persisted projections.
6. Define **replay/comparison lineage and memory snapshot isolation**.
7. Replace generic **reset** with explicitly scoped commands.
8. Define immutable **RecommendationSnapshot** ownership, public ID policy, and total ordering.

With those decisions fixed, the remaining issues are suitable for epic/story-level design.

## Re-review

**Updated artifact reviewed:** spine containing AD-24 through AD-27, the expanded state diagram, pinned runtime contract, immutable snapshot ownership, exactly-once learning, generated OpenAPI ownership, KPI ownership, replay isolation, and bounded reset behavior.

**Final verdict:** **PASS — ready for epic decomposition, with minor story-level contract details remaining.**

### Resolution of prior critical and high findings

| Prior finding | Resolution | Re-review result |
| --- | --- | --- |
| C-1 stage/transition crash protocol | AD-20 and AD-25 establish per-stage commands, optimistic revision checks, unique attempts, resume from last committed state, and no recomputation of committed stages. | Resolved at spine altitude. Exact attempt timestamps/status fields belong in persistence stories and contract tests. |
| C-2 outcome-to-learning ownership/exactly-once | `WAIT_FOR_OUTCOME`, `LEARN`, `LEARN_FAILED`, AD-17, and AD-25 now define the handoff, transactional episode/pattern ledger/transition, and idempotent retry. | Resolved. |
| H-1 snapshot ownership | AD-27 assigns immutable copied JSON in `run_snapshots` as the sole calculation input. | Resolved. |
| H-2 API interoperability | AD-27 makes generated OpenAPI from `contracts/` authoritative; AD-7/AD-8 retain boundary schemas, envelope, versioning, and idempotency rules. | Resolved at spine altitude. OpenAPI must be produced before frontend/backend epics proceed independently. |
| H-3 KPI source of truth | AD-27 assigns KPI ownership to `kpi_events` plus configuration version; AD-16 and AD-24 bind definitions/calculation semantics. | Resolved for MVP. |
| H-4 replay/comparison lineage | AD-27 requires a new run with `source_run_id` and an isolated Memory read snapshot; AD-14 fixes all non-memory inputs. | Resolved. |
| H-5 destructive reset ambiguity | AD-27 fixes rejection conditions, backup, cleared data classes, fixture reload transaction, and exported-report preservation. | Resolved. |

### Remaining non-blocking details

The former medium findings are now implementable as contract/story acceptance criteria rather than new architectural decisions:

- define the exact immutable recommendation/evidence schema referenced by `HumanDecision`;
- define Semantic Pattern key columns and deterministic ordering inside calculation/configuration contract v1;
- expose UUID as the API identity and legacy IDs as provenance according to AD-21;
- enumerate route/status/revision details in generated OpenAPI before parallel frontend work;
- require explicit total ordering for every returned collection and every tied result.

These details should be assigned to the contracts/persistence foundation epic and completed before dependent UI, metrics, and learning stories integrate. They no longer permit incompatible ownership, state mutation, or operational models under the updated spine.

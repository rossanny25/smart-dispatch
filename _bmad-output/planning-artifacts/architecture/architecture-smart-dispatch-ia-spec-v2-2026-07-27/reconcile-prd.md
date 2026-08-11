# PRD → Architecture Reconciliation

**Date:** 2026-07-27  
**Inputs:** `prd.md`, `addendum.md`  
**Targets reviewed:** `ARCHITECTURE-SPINE.md`, `ACADEMIC-ARCHITECTURE.md`  
**Method:** preservation review of product requirements, testable consequences, non-functional constraints, qualitative intent, and brownfield direction. Merely listing `FR-1..FR-21` in metadata is not counted as architectural landing unless a decision, boundary, data concept, API surface, test obligation, or explicit incorporation-by-reference preserves the behavior.

## Executive result

The architecture preserves the core product thesis and all load-bearing safety decisions: deterministic orchestration, hard constraints before ranking, score/confidence separation, human authority, episodic/semantic separation, SQLite, reproducible scenario fixtures, structured evidence, and a local deterministic baseline. There is no conflict with the central intent of the PRD or addendum.

However, the documents are not yet a complete implementation substrate for every testable PRD consequence. Two material gaps should be closed before epic/story generation:

1. FR-20 has no explicit replay-by-run/snapshot API operation even though replay by identifier is required.
2. The academic document describes Human Decision and outcome as one atomic write, while its API exposes them as separate commands and the PRD permits outcome capture after the decision.

Several other requirements are only named or left implicit, especially exact configuration defaults, capture provenance, warning semantics, result-shape obligations, KPI contracts, accessibility criteria, and the performance acceptance threshold. These do not invalidate the selected architecture, but they must be made binding by explicit incorporation or companion contracts.

## Traceability and preservation matrix

| PRD area | Landing in architecture | Status | Reconciliation finding |
| --- | --- | --- | --- |
| Product thesis; decision support, not autonomous assignment | Academic §§1–2, 5–7; AD-2, AD-3, AD-9 | Preserved | Deterministic control and dispatcher authority are explicit. |
| UJ-1 safety-critical dispatch | AD-2–AD-4, AD-9, AD-15; Academic §§6–7, 13 | Preserved | Eligibility, explanation, warnings, alternatives, and no-feasible outcome are represented, although UI result-shape detail is incomplete. |
| UJ-2 override and learning | AD-5, AD-6; Academic §§6, 8–9 | Preserved with ambiguity | Eligible override and conservative learning land. Decision/outcome transaction wording conflicts internally; see C-1. |
| UJ-3 reproducible academic demonstration | AD-10, AD-14, AD-15; Academic §§13–14 | Preserved | Fixtures, comparison, logs, KPIs, and report evidence are represented. |
| FR-1 explicit state machine | AD-2 state diagram; Academic §6 | Preserved | Terminal states are valid architectural resolution of addendum choice. Invalid-transition behavior is mentioned in testing/API error codes. |
| FR-2 stage execution/audit | AD-2, AD-7, AD-10, AD-11; data model | Partial | Stage records and snapshots land, but required fields (start/end/duration/status/schema/input/output/error), resolvability, retention window, and location redaction of retained snapshots are not made explicit as a schema/data rule. |
| FR-3 terminal/error outcomes | AD-2, AD-7; Academic §§6, 11, 13 | Partial | Typed failure and `NO_FEASIBLE_CANDIDATES` land. The explicit response invariant “no recommendation” and recoverable UI treatment are not stated. |
| FR-4 Work Order capture | AD-7, AD-12; Academic API §11 | Partial | Validation and structured contracts land. Preservation of raw input, structured-output schema version, and field-level validation errors are not explicit. |
| FR-5 derived requirements and provenance | AD-7, AD-12; Academic §§5–6 | Partial | Analyze stage lands. Per-field `supplied`/`inferred`/`defaulted` provenance and ambiguity-warning obligations do not. |
| FR-6–FR-9 hard constraints | AD-3; Academic §7 | Mostly preserved | Availability, certifications, shift, maximum workday, and enabled safety rules land. Per-rule pass/fail evidence lands generally. Explicit behavior for disabled/unavailable safety checks—visible configuration/warning, never implicit pass—is not stated. |
| FR-10 normalized score components | AD-4; Academic §7 | Preserved | Components, normalized range, inputs, weights, contributions, and versioning land. |
| FR-11 objective function | Academic §7; AD-4 | Preserved | Exact default weights and penalties structure land; bounded result is not stated in architecture but remains in source PRD. |
| FR-12 ranking and alternatives | AD-3, AD-4, AD-9; Academic §§7, 13 | Partial | Explanation and testing of tie-break land. Exact tie-break order, ordering obligation, separation of ineligible candidates, full evaluated-Technician response, and no score for ineligible candidates are not specified in the architecture. |
| FR-13 confidence | AD-4; Academic §7; tests §13 | Partial | Independence and deterministic ownership land. Exact factor weights, score-margin normalization, single/no-candidate behavior, factor contributions, and low/medium/high thresholds do not. |
| FR-14 warnings/freshness | AD-4, AD-10; Academic §13 | Partial | Snapshot freshness and uncertainty scenarios land. Exact freshness windows, 25/50-point reductions, fallback behavior, warning fields, and impact disclosure do not. |
| FR-15 Human Decision | AD-5, AD-9; Academic §§6, 11 | Mostly preserved | Accept/override/decline and ineligible-override error land. Required override reason and immutable record of alternatives/evidence visible at decision time are not explicit. |
| FR-16 Episodic Memory | AD-6; Academic §§8–10 | Mostly preserved | Append-only/immutable evidence and linkage land. Required outcome fields, explicit unknown values, and predicted-versus-actual duration are not fully enumerated. |
| FR-17 Semantic Patterns | AD-6; Academic §9; tests §13 | Partial | Conservative promotion, contradiction, decay, episode linkage, and no eligibility influence land. Exact grouping/consistency rule, sample threshold, confidence formulas, half-life, active/inactive thresholds, and required exposed pattern metadata do not. |
| FR-18 KPIs | `domain/metrics`; Academic §§5, 11, 13 | Partial | KPI capability and evidence testing land. The eight formulas, numerator/denominator/exclusions/window/unit contract, and “unavailable rather than zero” rule are absent. |
| FR-19 Memory comparison | AD-6, AD-14; Academic §§9, 13 | Mostly preserved | Same fixtures and only Memory Mode differing land. Neutral Memory component when off, continued Episodic Memory writes, comparison output fields, and explicit hard-constraint identity assertion are not all stated. |
| FR-20 simulation and replay API | AD-7, AD-8, AD-14; Academic §11 | Gap | Versioned local API and scenario comparison land, but no endpoint/command explicitly replays a persisted request/configuration snapshot by identifier with selected Memory Mode. `GET /dispatch-runs/{id}` retrieves evidence; it does not replay it. |
| FR-21 academic package | AD-11, AD-14; Academic §§10, 11, 13 | Preserved | Run IDs, versions, results, KPI definitions, comparison, limitations, alternatives, and risks land. Statistical—not fine-tuning—nature is explained in alternatives/memory sections. |
| NFR-1 performance | AD-12, AD-13, AD-15; Academic §13 | Partial | Benchmark shape (100 warm runs, dataset bounds) lands. Required p95 `< 3 s`, exclusion of animation/optional LLM time, and hardware/runtime recording do not. |
| NFR-2 determinism | AD-4, AD-10, AD-12; Academic §2 | Preserved | Identical snapshots/configuration determinism is a central invariant. |
| NFR-3 transactional integrity | AD-5, AD-13; Academic §8 | Preserved with conflict | Per-command Unit of Work satisfies the PRD. Academic wording incorrectly combines decision and outcome; see C-1. |
| NFR-4 explainability/no chain-of-thought | AD-11; Academic §§2, 5, 7 | Preserved | Structured evidence is explicit. |
| NFR-5 privacy | AD-13 conventions/deferred; Academic §§12, 16 | Mostly preserved | Zone-level/no exact location in Semantic Patterns and logs lands. HTTPS before non-local use lands as deferred gate. Snapshot redaction/retention boundary remains under-specified. |
| NFR-6 accessibility | AD-9, AD-15; Academic §13 | Partial | Keyboard browser smoke tests land. Visible focus, semantic labels, non-color text alternatives, and applicable WCAG 2.2 AA scope are absent. |
| NFR-7 auditability | AD-2, AD-5, AD-7, AD-10, AD-11; data model | Mostly preserved | Core evidence and reproduction model land. Exact retained artifacts and retrieval obligations should be reflected in schemas. |
| MVP scope/non-goals | AD-12–AD-15; Deferred; Academic §§12, 15–16 | Preserved | Local educational scope, optional LLM, no fine-tuning/vector DB/real integrations/production claims all land. |
| Success metrics and counter-metrics | AD bindings; Academic §13 | Partial | Test layers cover their substance, but the ten success criteria and three counter-metrics are not preserved as an acceptance matrix. Particularly absent are the explicit 100% criteria and mandatory seeded scenario demonstrations. |
| PRD open questions/assumptions | Academic §16 | Partial | Retention and external-pilot gates land. The assumptions index is not carried into a decision/configuration registry, and accessibility scope is silently narrowed to keyboard testing. |
| Addendum brownfield baseline | Academic §§3, 14–15 | Preserved | Python/vanilla baseline, migration path, SQLite, JSON import, and `alerts.push` defect all land. |
| Addendum JSON contracts | AD-7, Academic §§5–6 | Preserved | Validation before transitions and authoritative deterministic services land. |
| Addendum learning policy | AD-6, Academic §9 | Preserved at policy level | Exact defaults remain absent, consistent with their PRD assumption status, but stories need a source of truth. |

## Conflicts and material gaps

### C-1 — Human Decision and service outcome transaction semantics conflict

**Severity:** High  
**Sources:** PRD FR-15, FR-16, NFR-3; Architecture Spine AD-5 and AD-8; Academic §§6, 8, 11.

The Spine correctly specifies one transaction per command. The API correctly exposes:

- `POST .../decisions`
- `POST .../outcomes`

But Academic §8 states that “recording a Human Decision and outcome is atomic,” and the sequence diagram compresses them into one dispatcher/API action. In the user journey, the outcome occurs after service completion and may be recorded much later. A database transaction cannot remain open across that interval.

**Required resolution:** Make each command independently atomic. A decision transaction persists the decision and advances/holds the run in an explicit outcome-pending condition. A later outcome transaction appends the service outcome and enables `LEARN`. If the design intentionally requires both in one command for seeded simulation, define that as a separate composite scenario command without replacing the real two-step flow.

### G-1 — Replay by persisted identifier is absent

**Severity:** High  
**Source:** FR-20.

The API can start a run, retrieve a run, and compare a scenario fixture, but it cannot explicitly replay a prior run/request snapshot by identifier with a chosen Memory Experiment Mode. This prevents direct acceptance of the PRD consequence “same request snapshot and configuration can be replayed by identifier.”

**Required resolution:** Add an application command and endpoint such as `POST /api/v1/dispatch-runs/{run_id}/replays` with selected Memory Experiment Mode. The new run must reference the source run/snapshot and reuse its Work Order, Technician, environment, clock, and non-memory configuration.

### G-2 — Architecture does not bind the exact PRD formulas/defaults

**Severity:** Medium  
**Sources:** FR-12–FR-14, FR-17, KPI contracts.

The documents name configuration/versioning and test categories but omit many exact PRD defaults. This leaves parallel implementers free to choose incompatible formulas and thresholds.

**Required resolution:** Either:

- state explicitly that the PRD’s formulas, thresholds, tie-break, freshness behavior, learning parameters, and KPI contracts are incorporated unchanged into configuration version `v1`; or
- add a binding configuration/contract companion referenced from the Spine.

The defaults may remain `[ASSUMPTION]`, but their implementation value must not be ambiguous.

### G-3 — Capture provenance and audit schemas are under-specified

**Severity:** Medium  
**Sources:** FR-2, FR-4, FR-5, NFR-7.

Versioned Pydantic boundaries alone do not ensure stored raw input, per-field derivation provenance, complete stage timings/status/error, or resolvable snapshots.

**Required resolution:** Define minimum persisted schemas for `WorkOrder`, `StageExecution`, and snapshot references, including redaction policy and prototype evidence retention behavior.

### G-4 — API/UI result invariants are not explicit

**Severity:** Medium  
**Sources:** FR-3, FR-9, FR-12, FR-14, FR-15.

The architecture does not explicitly bind:

- no recommendation on `NO_FEASIBLE_CANDIDATES`;
- every Technician represented with eligibility evidence;
- scores only for eligible candidates;
- ineligible candidates separated from ranking;
- warning field/quality/fallback/impact structure;
- disabled/unavailable safety rule never treated as implicit pass;
- override reason required;
- decision-time alternatives/evidence frozen.

**Required resolution:** Add these to API contract invariants or a candidate-evaluation/evidence schema.

### G-5 — KPI semantics are too abstract

**Severity:** Medium  
**Sources:** FR-18, PRD §11.

`domain/metrics` identifies an owner but not the eight calculations. Without exact numerator, denominator, exclusions, units, UTC windows, and unavailable semantics, two implementations can both conform structurally while producing incompatible evidence.

**Required resolution:** Incorporate PRD §11 as the binding KPI registry and require its configuration version in every KPI response/report.

### G-6 — Accessibility acceptance is narrowed

**Severity:** Medium  
**Sources:** NFR-6, PRD Open Question 3.

Keyboard browser smoke tests are necessary but do not preserve visible focus, semantic labels, text alternatives for color/icon state, or the provisional WCAG 2.2 AA target across the named flows.

**Required resolution:** Carry the whole NFR-6 into the browser adapter contract and test plan, explicitly retaining its `[ASSUMPTION]` status until the scope question is decided.

### G-7 — Performance acceptance threshold is missing

**Severity:** Medium  
**Source:** NFR-1.

The benchmark procedure lands, but the architecture omits the p95 `< 3 seconds` pass/fail threshold, exclusions, and environment recording.

**Required resolution:** Add the threshold and measurement conditions to AD-15 or Academic §13.

### G-8 — Success metrics are not an explicit acceptance registry

**Severity:** Low/Medium  
**Source:** PRD §9.

The test strategy is directionally aligned, but it does not preserve explicit 100% invariants or required demonstration scenarios such as high score/low confidence, one observation versus promotion, changed ordering and unchanged ordering, or complete academic evidence linkage.

**Required resolution:** Add a PRD success-metric-to-test/evidence matrix before implementation readiness review.

## Qualitative intent review

| Intent | Result |
| --- | --- |
| Reduce dispatcher cognitive load without hiding constraints | Preserved through structured evidence and browser-as-adapter boundary. |
| Human remains accountable | Preserved; autonomous assignment is not introduced. |
| Learning changes recommendations in a controlled, explainable way | Preserved architecturally through separate episodic/semantic stores and score-only memory influence. |
| Prototype is demonstrable, not merely descriptive “multi-agent” prose | Strongly preserved through deterministic stages, contracts, SQLite evidence, tests, and report adapter. |
| Synthetic evidence must not be presented as production efficacy | Preserved in academic evidence requirements and limitations. |
| Existing implementation should evolve incrementally | Preserved by the ten-step brownfield migration. |
| Educational simplicity without false production-readiness | Preserved by modular-monolith selection and explicit pre-pilot gates. |

## Recommended disposition

**Conditional pass for architecture quality; not yet a clean pass for story generation.**

The architecture paradigm and load-bearing decisions are sound. Before creating epics and stories, resolve C-1 and G-1 and make the PRD’s exact behavior binding through explicit incorporation or companion contracts. G-2 through G-8 can be closed without changing the paradigm or module boundaries.

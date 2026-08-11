---
title: Smart Dispatch IA v2.1
status: final
created: 2026-07-27
updated: 2026-07-27
---

# PRD: Smart Dispatch IA v2.1

## 0. Document Purpose

This PRD is the product contract for turning the current Smart Dispatch IA simulator into a technically demonstrable educational prototype. It reconciles the existing `spec/` corpus, the implemented brownfield system documented in `docs/index.md`, and the priorities in `docs/PLAN_FEEDBACK_PROFESOR.md`. It defines product behavior and testable outcomes; implementation mechanisms are preserved in `addendum.md`.

## 1. Product Thesis and Vision

Field-service dispatchers make time-sensitive assignments using fragmented data about incidents, skills, availability, workload, location, and prior outcomes. A useful assistant must reduce this cognitive load without concealing constraints or taking irreversible control away from the dispatcher.

Smart Dispatch IA recommends a technician through a deterministic, observable pipeline. Hard operational rules define who is eligible; a configurable objective ranks only eligible candidates; a separate confidence model communicates uncertainty; and every human decision and service result becomes auditable evidence. The prototype succeeds when it can demonstrate that memory changes recommendations in a controlled, explainable way without overriding safety rules.

The product is decision support, not autonomous workforce management. The dispatcher remains accountable for accepting or overriding a recommendation.

## 2. Target User and Journeys

### 2.1 Primary User

The primary user is a field-service dispatcher or coordinator operating the educational simulator.

### 2.2 Jobs To Be Done

- Turn an unstructured service request into a prioritized, skill-aware Work Order.
- Identify which Technicians are eligible before comparing them.
- Understand why one eligible Technician ranks above another.
- Recognize when a recommendation is uncertain or based on stale data.
- Accept or override the recommendation and preserve the reason.
- Review operational evidence showing whether the system improves over time.

### 2.3 Key User Journeys

- **UJ-1. Laura dispatches a safety-critical order.**
  - **Persona + context:** Laura is coordinating several active incidents when a gas-leak report arrives.
  - **Entry state:** The local simulator is open with seeded Technicians and current environment conditions.
  - **Path:** Laura creates the Work Order; the Dispatch Run advances through its visible states; the system excludes ineligible Technicians; Laura inspects score components, confidence, warnings, alternatives, and discard reasons.
  - **Climax:** Laura accepts an eligible recommendation knowing every Hard Constraint passed.
  - **Resolution:** The Human Decision and selected Technician are recorded for later outcome capture.
  - **Edge case:** If no Technician is eligible, Laura receives a `NO_FEASIBLE_CANDIDATES` outcome and no recommendation.

- **UJ-2. Martín overrides a recommendation and teaches the system.**
  - **Persona + context:** Martín knows an operational fact that is not represented in the current data.
  - **Entry state:** A Dispatch Run is waiting for a Human Decision.
  - **Path:** Martín compares alternatives, selects another eligible Technician, and records a reason; after service completion, he records actual duration and result.
  - **Climax:** The system stores the decision and outcome as Episodic Memory without immediately turning one observation into a rule.
  - **Resolution:** Repeated consistent evidence can later promote a Semantic Pattern; contradictory evidence reduces confidence.

- **UJ-3. Rossy demonstrates academic evidence.**
  - **Persona + context:** Rossy must show that the prototype is controlled, measurable, and not merely a descriptive multi-agent concept.
  - **Entry state:** The simulator contains reproducible scenarios and historical episodes.
  - **Path:** Rossy runs scenarios with Memory enabled and disabled, reviews State Transition logs and KPIs, and inspects cases with stale GPS or close candidate scores.
  - **Climax:** The comparison shows what changed, why it changed, and whether Hard Constraints remained invariant.
  - **Resolution:** Results can be cited in the academic deliverable with limitations and configuration recorded.

## 3. Glossary

- **Work Order** — A service request containing location, priority, SLA, required certifications, and estimated duration.
- **Technician** — A field worker with availability, certifications, shift, workload, quality history, and location data.
- **Dispatch Run** — One persisted execution of the State Machine for one Work Order and one input/configuration snapshot.
- **State Machine** — The deterministic controller with states `CAPTURE`, `ANALYZE`, `PLAN`, `EVALUATE`, `WAIT_FOR_DECISION`, and `LEARN`.
- **Agent Stage** — A bounded processing step that consumes and produces schema-valid JSON; an Agent Stage does not control State Transitions.
- **State Transition** — A permitted move between State Machine states, recorded with timestamps and outcome.
- **Hard Constraint** — A non-negotiable eligibility rule applied before ranking and never overridden by Memory.
- **Eligible Candidate** — A Technician who passes every Hard Constraint for a Work Order.
- **Objective Score** — A 0–100 ranking value calculated only for an Eligible Candidate from normalized components and penalties.
- **Recommendation Confidence** — A 0–100 measure of evidence quality and decision separation; it is independent of Objective Score.
- **Memory Score Component** — The normalized 0–100 Objective Score component derived only from active Semantic Patterns.
- **Memory Experiment Mode** — A run configuration that enables or disables reads from Semantic Patterns while continuing to record Episodic Memory.
- **Data Quality Warning** — A structured notice about missing, stale, estimated, or unreliable input.
- **Human Decision** — Acceptance, eligible override, or no-assignment decision by the dispatcher.
- **Episodic Memory** — Immutable evidence from Dispatch Runs, Human Decisions, outcomes, and events.
- **Semantic Pattern** — An aggregated preference or calibration promoted from sufficient Episodic Memory.
- **KPI** — A reproducibly computed measure of dispatch performance or system behavior.

## 4. Features and Functional Requirements

### 4.1 Deterministic Orchestration

**Description:** The State Machine controls every Dispatch Run. Agent Stages cannot skip Hard Constraints, change transition order, or write a final assignment directly. Realizes UJ-1 and UJ-3.

#### FR-1: Execute the explicit State Machine

The system shall execute `CAPTURE -> ANALYZE -> PLAN -> EVALUATE -> WAIT_FOR_DECISION -> LEARN`.

**Consequences (testable):**

- Every Dispatch Run has one current state and a recorded history of State Transitions.
- Only configured transitions are accepted; an invalid transition returns a structured error and does not mutate state.
- `LEARN` begins only after a Human Decision and the required outcome data are recorded.
- Every Agent Stage boundary validates versioned JSON input and output before its State Transition; validation failure prevents transition and is persisted as a typed error.

#### FR-2: Record stage execution

The system shall record each Agent Stage's start, end, duration, status, schema version, input snapshot reference, output snapshot reference, and error.

**Consequences (testable):**

- A completed Dispatch Run exposes a chronologically ordered stage log.
- A failed Agent Stage identifies the failing state and preserves prior completed records.
- Logs expose decision evidence and structured outputs, not private chain-of-thought.
- Every stage snapshot reference resolves to retrievable, schema-versioned content retained for the prototype evidence window, subject to location-data redaction.

#### FR-3: Handle terminal and error outcomes

The system shall model invalid input, invalid Agent Stage output, stage failure, and no feasible candidates as explicit outcomes.

**Consequences (testable):**

- When no Technician passes all Hard Constraints, the run returns `NO_FEASIBLE_CANDIDATES`, contains the rejection reasons, and contains no recommended Technician.
- The UI presents a recoverable error or no-candidate state without fabricating a recommendation.

### 4.2 Work Order Capture and Analysis

**Description:** The dispatcher provides a natural-language incident plus operational context. Capture and analysis produce schema-valid Work Order data for deterministic downstream processing. Realizes UJ-1.

#### FR-4: Capture and validate a Work Order

The dispatcher can create a Work Order with incident text, address, zone, and available context.

**Consequences (testable):**

- Missing required fields return field-level validation errors.
- The stored Work Order preserves the raw input and the schema version of structured output.

#### FR-5: Derive dispatch requirements

The analysis stage shall derive category, priority, SLA target, required certifications, and estimated service duration.

**Consequences (testable):**

- Every derived field records whether it was supplied, inferred, or defaulted.
- Unsupported or ambiguous classifications produce a Data Quality Warning.

### 4.3 Feasibility Before Ranking

**Description:** The feasibility engine evaluates every Technician against immutable rules before any Objective Score is calculated. Realizes UJ-1.

#### FR-6: Enforce availability

A Technician is ineligible when unavailable.

**Consequences (testable):**

- An unavailable Technician never receives an Objective Score.
- The candidate record contains the failed availability check.

#### FR-7: Enforce all required certifications

A Technician is eligible only when possessing every certification required by the Work Order.

**Consequences (testable):**

- Matching only a subset of required certifications causes rejection.
- Memory and priority cannot restore eligibility.

#### FR-8: Enforce shift and maximum-day limits

A Technician is ineligible when outside the scheduled shift or when travel plus service would exceed the configured maximum workday.

**Consequences (testable):**

- The check uses the same time snapshot and estimated durations recorded in the Dispatch Run.
- Emergency priority does not silently bypass the rule; any future exception requires a separately modeled, explicit authorization flow and is out of MVP scope.

#### FR-9: Preserve additional safety constraints

The feasibility engine shall support configured driving-hour and required-equipment checks from the existing business rules.

**Consequences (testable):**

- Each enabled safety rule produces a pass/fail record.
- Disabled or unavailable checks produce a visible configuration or Data Quality Warning, not an implicit pass.

### 4.4 Explainable Ranking

**Description:** Only Eligible Candidates receive an Objective Score. The system exposes the exact components used in ranking. Realizes UJ-1 and UJ-3.

#### FR-10: Normalize scoring components

For every Eligible Candidate, the system shall calculate `SLA`, `proximity`, `workload_balance`, `quality`, and `memory` components on a 0–100 scale.

**Consequences (testable):**

- The response includes each raw input, normalized value, configured weight, and weighted contribution.
- Identical inputs and configuration produce identical component values.

#### FR-11: Apply the configurable objective function

The default Objective Score shall be:

`0.35 × SLA + 0.25 × proximity + 0.20 × workload_balance + 0.10 × quality + 0.10 × memory − penalties`

**Consequences (testable):**

- Default weights total 1.00 and are stored as versioned configuration.
- The final Objective Score is bounded to 0–100 after penalties.
- A Dispatch Run records the configuration version used.

#### FR-12: Rank and explain alternatives

The system shall return all evaluated Technicians with eligibility, Objective Score where applicable, component breakdown, warnings, and discard reasons.

**Consequences (testable):**

- Eligible Candidates are ordered by Objective Score with a deterministic tie-break.
- Ties are resolved by higher `SLA`, then higher `quality`, then lower estimated travel time, then lexicographically ascending Technician identifier. [ASSUMPTION: This is the MVP tie-break order.]
- Ineligible Technicians are listed separately and never interleaved into the ranking.
- The recommendation explanation can be reconstructed from structured fields.

### 4.5 Confidence and Uncertainty

**Description:** Recommendation Confidence communicates how trustworthy the recommendation is, independently from how well the leading Technician scores. Realizes UJ-1 and UJ-3.

#### FR-13: Calculate Recommendation Confidence

The system shall calculate Recommendation Confidence from data availability/freshness, historical evidence quantity, score margin between the first and second Eligible Candidates, and uncertain conditions.

**Consequences (testable):**

- The response exposes each confidence factor and its contribution.
- A high Objective Score can coexist with low Recommendation Confidence.
- [ASSUMPTION: The MVP formula is `0.35 × data_quality + 0.25 × historical_evidence + 0.25 × score_margin + 0.15 × condition_certainty`, with every factor normalized to 0–100.]
- [ASSUMPTION: `score_margin = min(100, 10 × (first_score − second_score))`; with one Eligible Candidate it is 50, and with none Recommendation Confidence is not available.]
- Confidence labels are `low` for 0–49, `medium` for 50–74, and `high` for 75–100.

#### FR-14: Surface Data Quality Warnings

The system shall warn about missing, stale, estimated, or unavailable GPS, traffic, weather, and historical evidence.

**Consequences (testable):**

- Every warning identifies the affected field, observed freshness/quality, fallback used, and recommendation impact.
- Offline GPS uses the last known zone only when available and marks the result as estimated.
- [ASSUMPTION: GPS is current through 5 minutes, stale through 30 minutes, and unavailable afterward; traffic and weather are current through 15 minutes, stale through 60 minutes, and unavailable afterward.]
- Stale data reduces its corresponding confidence factor by 25 points. Unavailable data reduces it by 50 points and uses the documented seeded/default scenario value.

### 4.6 Human Decision and Controlled Learning

**Description:** The dispatcher decides; the system records evidence and updates learning conservatively. Realizes UJ-2.

#### FR-15: Record the Human Decision

The dispatcher can accept the recommendation, override it with another Eligible Candidate, or decline assignment.

**Consequences (testable):**

- An override requires a reason.
- The system rejects an override to an ineligible Technician.
- The decision records the alternatives and evidence visible at decision time.

#### FR-16: Record service outcomes as Episodic Memory

The system shall persist the selected Technician, predicted duration, actual duration, completion status, First-Time Fix result when supplied, and dispatcher feedback.

**Consequences (testable):**

- A new observation appends an Episodic Memory record and never overwrites prior evidence.
- Missing optional outcome fields remain explicitly unknown.
- The recommendation, alternatives, and evidence visible at decision time are immutable Episodic Memory linked to the Human Decision.

#### FR-17: Promote Semantic Patterns conservatively

The learning stage shall aggregate consistent observations, reduce confidence for contradictions, apply age decay, and promote a Semantic Pattern only after a configured minimum sample count.

**Consequences (testable):**

- One new observation cannot create an active Semantic Pattern.
- Every Semantic Pattern exposes sample count, confidence, update time, decay parameters, and supporting episode identifiers.
- Hard Constraints never consume Memory as an override signal.
- [ASSUMPTION: The MVP promotes after at least three consistent episodes; observations are consistent when they share pattern type and grouping keys and their numeric direction agrees.]
- [ASSUMPTION: A consistent episode adds `0.20 × (1 − confidence)`; a contradictory episode multiplies confidence by 0.70; inactive confidence decays with a 90-day half-life.]
- A Semantic Pattern becomes inactive below 0.50 confidence and becomes active after promotion only at or above 0.60 confidence.

### 4.7 KPI Evidence and Scenario Comparison

**Description:** The prototype demonstrates operational and system behavior with reproducible measures. Realizes UJ-3.

#### FR-18: Compute prototype KPIs

The system shall compute time to assignment, SLA compliance, manual reassignment rate, mean absolute estimated-time error, workload balance, recommendation acceptance, total/stage latency, and First-Time Fix Rate when outcome data exist.

**Consequences (testable):**

- Every KPI defines numerator, denominator, excluded records, time window, and unit.
- A KPI with insufficient data is marked unavailable rather than reported as zero.

#### FR-19: Compare Memory enabled and disabled

The system shall run or replay the same scenario with Memory enabled and disabled.

**Consequences (testable):**

- Both runs share the same Work Order, Technician, environment, and non-memory configuration snapshots.
- The comparison identifies changed ranks, score contributions, recommendation, confidence, and KPI inputs.
- Hard Constraint results are identical between both runs.
- Memory Experiment Mode disables Semantic Pattern reads and sets the Memory Score Component to its neutral value; it does not disable Episodic Memory writes.

#### FR-20: Expose a local simulation and replay API

The prototype shall expose a versioned local API that starts or replays a scenario with a selected Memory Experiment Mode and returns the Dispatch Run, eligibility results, Objective Score breakdown, Recommendation Confidence, warnings, alternatives, and State Transition log.

**Consequences (testable):**

- The same request snapshot and configuration can be replayed by identifier.
- API responses validate against a versioned schema.
- The API is local prototype surface, not a public compatibility commitment.

#### FR-21: Produce the academic evidence package

The system shall produce a reproducible report for selected scenarios.

**Consequences (testable):**

- The report identifies configuration version, scenario inputs, linked Dispatch Run identifiers, results, Memory Experiment Mode comparison, and KPI values.
- The report states synthetic-data limitations, rejected alternatives, known risks, and the statistical—not fine-tuning—nature of learning.
- Every reported result links to retrievable structured evidence.

## 5. Cross-Cutting Non-Functional Requirements

### NFR-1: Performance

The deterministic synchronous recommendation path shall finish within 3 seconds at the 95th percentile across 100 warm runs on the seeded classroom dataset of up to 100 Technicians and 100 open Work Orders, excluding deliberate UI animation and optional external LLM latency. The benchmark records hardware and runtime versions.

### NFR-2: Determinism

Given identical persisted inputs and configuration, feasibility, scoring, confidence, and KPI calculations shall produce identical outputs.

### NFR-3: Reliability and Integrity

State Transition, Human Decision, outcome, and learning writes shall be transactional. A failed write shall not leave a partially advanced Dispatch Run.

### NFR-4: Explainability

All user-facing explanations shall be derivable from stored structured evidence. The product shall not display or claim access to private model chain-of-thought.

### NFR-5: Privacy

Transport shall use HTTPS outside local development. Long-term Semantic Patterns shall use zone-level location, not exact historical coordinates.

### NFR-6: Accessibility

The order creation, dispatch review, Human Decision, outcome capture, and KPI comparison flows shall support keyboard-only operation, visible focus, semantic labels, and text alternatives for status conveyed by color or icons. [ASSUMPTION: The MVP acceptance target is the applicable WCAG 2.2 AA success criteria for these flows.]

### NFR-7: Auditability

Every Dispatch Run shall retain the input snapshot, configuration version, state history, candidate evidence, Human Decision, and linked outcomes required to reproduce its result.

## 6. Constraints and Guardrails

- The MVP remains a local educational prototype with seeded or simulated data.
- Hard Constraints are deterministic code, not learned prompt behavior.
- SQLite is the shared persistence layer for the MVP.
- LLM integration is optional and limited to Capture/Analysis assistance behind schema validation.
- The existing Python and vanilla JavaScript prototype may be refactored; adopting a production framework is not a product requirement.
- Exact GPS history is not retained in long-term Semantic Patterns.

## 7. Non-Goals

- Autonomous assignment without a Human Decision.
- Production workforce scheduling, route optimization, payroll, or labor-agreement management.
- Real-time integrations with GPS, traffic, weather, ERP, CRM, or ticketing systems.
- Fine-tuning or online training of an ML model.
- Vector databases or production-scale semantic search.
- A technician mobile application.
- Production deployment or multi-tenant security.

## 8. MVP Scope

### 8.1 In Scope

- Start cleanly and complete the seeded create–simulate–decide–outcome flow without a known unhandled runtime error.
- Deterministic State Machine and execution log.
- Hard-constraint-first eligibility.
- Configurable normalized Objective Score and breakdown.
- Recommendation Confidence and Data Quality Warnings.
- SQLite Episodic Memory and Semantic Patterns with migration from JSON.
- Human acceptance/eligible override/outcome capture.
- KPI panel and Memory on/off comparison.
- Automated tests for rules, uncertainty, learning, contracts, and representative flows.
- Academic decision/limitations evidence.

### 8.2 Out of Scope for MVP

The Non-Goals in §7 remain out of scope. In addition, exact production KPI targets are not asserted from synthetic data; the prototype demonstrates correct measurement and reports observed values.

## 9. Success Metrics

**Primary**

- **SM-1:** 100% of automated hard-rule scenarios reject every ineligible Technician before ranking. Validates FR-6–FR-9.
- **SM-2:** 100% of scored candidates expose reproducible component arithmetic matching the recorded configuration. Validates FR-10–FR-12.
- **SM-3:** 100% of completed Dispatch Runs have a valid State Transition history with required timing and evidence fields. Validates FR-1–FR-3 and FR-20.
- **SM-4:** Memory on/off comparisons never change Hard Constraint outcomes. Validates FR-17 and FR-19.

**Secondary**

- **SM-5:** The system reports KPI-1 through KPI-8 using the contracts below; unavailable values are explicitly marked. Validates FR-18.
- **SM-6:** At least one seeded scenario demonstrates low Recommendation Confidence despite a high leading Objective Score. Validates FR-13–FR-14.
- **SM-7:** At least one repeated-evidence scenario promotes a Semantic Pattern, while a single-observation scenario does not. Validates FR-16–FR-17.
- **SM-8:** The synchronous recommendation path meets NFR-1 for the seeded dataset.
- **SM-9:** At least one reproducible Memory on/off scenario changes Eligible Candidate ordering through a visible Memory Score Component, and at least one scenario correctly produces no ranking change. Validates FR-17 and FR-19.
- **SM-10:** Every selected academic scenario appears in an evidence package with resolvable run IDs, configuration, results, limitations, and risks. Validates FR-21.

**Counter-metrics**

- **SM-C1:** Recommendation acceptance is not optimized by hiding alternatives, warnings, or uncertainty.
- **SM-C2:** SLA compliance is not improved by violating Hard Constraints or silently extending shifts.
- **SM-C3:** Memory influence is not increased by lowering promotion thresholds below the configured evidence minimum.

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| “Multi-agent” framing hides deterministic business logic | Unsafe or irreproducible decisions | State Machine owns control; Hard Constraints and scoring are deterministic services |
| Synthetic data overstates operational value | Weak academic claims | Separate observed prototype behavior from real-world efficacy claims |
| Sparse feedback creates unstable preferences | Biased recommendations | Minimum samples, contradiction handling, decay, and visible confidence |
| Score and confidence are confused | False certainty | Separate fields, formulas, explanations, and UI treatments |
| Brownfield implementation diverges from specs | Rework and misleading demos | Treat `docs/index.md` as current-state evidence and this PRD as target contract |

## 11. KPI Contracts

| ID | KPI | Definition |
|---|---|---|
| KPI-1 | Time to assignment | Median and p95 seconds from Dispatch Run start to Human Decision; exclude abandoned runs and report them separately |
| KPI-2 | SLA compliance | Work Orders assigned within SLA divided by eligible completed assignment decisions in the selected window |
| KPI-3 | Manual reassignment rate | Eligible overrides divided by Human Decisions containing a recommendation |
| KPI-4 | Estimated-time MAE | Mean absolute difference in minutes between predicted and actual service duration for outcomes containing both |
| KPI-5 | Workload balance | [ASSUMPTION: Population standard deviation of assigned workload hours across available Technicians at end of window; lower is more balanced.] |
| KPI-6 | Recommendation acceptance | Accepted recommendations divided by Human Decisions containing a recommendation |
| KPI-7 | Latency | Median and p95 milliseconds for total deterministic path and each Agent Stage |
| KPI-8 | First-Time Fix Rate | First-Time Fix outcomes divided by completed outcomes where First-Time Fix is known |

Each KPI reports its UTC time window, numerator, denominator, exclusions, unit, and configuration version. [ASSUMPTION: First-Time Fix remains optional for ad hoc use but is required in seeded academic evaluation scenarios.]

## 12. Open Questions

1. Should the working defaults marked `[ASSUMPTION]` be approved unchanged after the first reproducible scenario suite?
2. What retention duration and deletion behavior should apply to Dispatch Runs and Episodic Memory beyond the classroom prototype?
3. Should accessibility target WCAG 2.2 AA for the complete dashboard or a documented MVP flow subset?

Open Question 1 does not block architecture but must be resolved before the affected stories are accepted as complete. Questions 2 and 3 may use documented prototype defaults and must be revisited before any external pilot.

## 13. Assumptions Index

- §4.4 FR-12 — tie-break order.
- §4.5 FR-13 — confidence factor weights.
- §4.5 FR-13 — score-margin normalization and single-candidate behavior.
- §4.5 FR-14 — GPS, traffic, and weather freshness thresholds.
- §4.6 FR-17 — consistency predicate and promotion threshold.
- §4.6 FR-17 — confidence update rules and decay half-life.
- §5 NFR-6 — WCAG 2.2 AA applied to the named MVP flows.
- §9 SM-5 / §11 KPI-5 — population standard deviation as the workload-balance measure.
- §11 KPI-8 — First-Time Fix optional in ad hoc use and required in academic scenarios.

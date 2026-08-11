# Reconciliation: `PLAN_FEEDBACK_PROFESOR.md`

## Scope and method

This extract compares `docs/PLAN_FEEDBACK_PROFESOR.md` with the current
`prd.md` and `addendum.md` in the same PRD workspace. It is an input
reconciliation, not a review of implementation status. An item is:

- **Covered** when the requested behavior is present as a product requirement,
  success measure, constraint, or deliberately preserved technical direction.
- **Partially covered** when the intent appears but some requested behavior is
  not contractual or testable.
- **Deferred appropriately** when it belongs to architecture, stories, or
  delivery planning rather than the PRD.
- **Conflict resolved** when the PRD explicitly chooses between inconsistent
  source directions.

## Overall verdict

The professor's plan is substantially preserved. All three priorities and all
eight prototype KPIs appear in the PRD, and the addendum carries the principal
implementation direction that the PRD intentionally excludes. The remaining
gaps are narrow but meaningful:

1. the feedback's explicit simulation API is not a requirement;
2. the universal contract that every Agent Stage consumes and produces
   validated JSON lives mainly in the addendum, not as a complete PRD
   acceptance contract;
3. stage logging records snapshot references rather than explicitly requiring
   the input/output payloads themselves to be retrievable;
4. the academic decision/limitations/risk document is named in scope and the
   addendum, but its required content and acceptance criteria are not defined;
5. the delivery sequence and downstream BMAD workflow order are intentionally
   absent from the product contract and still need execution outside the PRD.

No central product idea from the feedback was silently discarded. A few
qualitative emphases are implicit rather than stated with the same force; these
are identified below.

## Detailed coverage matrix

| Feedback item | Status | Evidence in PRD/addendum | Reconciliation note |
|---|---|---|---|
| Convert a descriptive proposal into a technically demonstrable specification | **Covered** | PRD §0, §1, UJ-3, §8; addendum “Academic Evidence” | Demonstrability is the document's organizing purpose and is backed by reproducible scenarios and success metrics. |
| Preserve educational-prototype scope | **Covered** | PRD §6 and §8; Non-Goals | Local, seeded/simulated, non-production scope is explicit. |
| Sequential deterministic state machine | **Covered** | PRD FR-1; glossary; addendum “Deterministic Control” | The English state names map one-to-one to the Spanish source sequence. |
| Agent stages must not bypass business restrictions | **Covered** | PRD §4.1 description, FR-1, FR-6–FR-9, FR-17 | State control and hard-rule precedence are explicit and testable. |
| Record start, end, duration, input, and output of every agent | **Partially covered** | PRD FR-2 | Start, end, duration, and input/output **snapshot references** are required. The requirement does not explicitly say the referenced payloads must be retained and retrievable for every stage, although NFR-7 strongly implies this at run level. |
| Define error routes | **Covered** | PRD FR-3; addendum terminal/error-state note | Invalid input/output, stage failure, and recoverable UI behavior are covered. Architecture retains freedom over states versus typed outcomes. |
| Explicit no-feasible-candidate case | **Covered** | UJ-1 edge case; FR-3; addendum | It is terminal, contains rejection reasons, and cannot fabricate a recommendation. |
| Exclude unavailable technicians | **Covered** | FR-6; SM-1 | Excluded before scoring. |
| Require all certifications | **Covered** | FR-7; SM-1 | Partial certification matches fail; Memory cannot restore eligibility. |
| Exclude technicians outside shift | **Covered** | FR-8; SM-1 | Explicit hard rule. |
| Exclude assignments beyond maximum workday | **Covered** | FR-8; SM-1 | Uses travel plus service duration and a recorded time snapshot. |
| Learning cannot override hard rules | **Covered** | FR-7, FR-17, SM-4, counter-metric SM-C3 | This invariant is repeated across requirements and metrics. |
| Normalized objective function with exact default weights | **Covered** | FR-10 and FR-11 | Formula, 0–100 normalization, penalty application, bounded result, and configuration version are required. |
| Weights configurable for scenario testing | **Covered** | FR-11; UJ-3 | Versioned configuration is persisted per run; reproducible scenarios are part of the evidence journey. |
| Expose scoring breakdown | **Covered** | FR-10–FR-12; SM-2 | Raw inputs, normalized values, weights, contributions, warnings, and discard reasons are required. |
| SQLite as shared memory | **Covered** | PRD §6, §8; addendum “SQLite” | SQLite is mandatory for MVP persistence. The addendum specifies separation of operational, audit, episodic, and semantic records. |
| Separate episodic and semantic memory | **Covered** | Glossary; FR-16–FR-17; addendum “SQLite” | Both forms have distinct semantics and evidence rules. |
| Persist orders, proposals, human decisions, outcomes, events as episodes | **Mostly covered** | Dispatch Run and Work Order records in FR-1–FR-5; Human Decision in FR-15; outcomes in FR-16; auditability in NFR-7 | “Proposal” is represented by candidate evidence/recommendation rather than named as a separate Episodic Memory record. The observable information is retained, but the storage classification should be made explicit in architecture/data contracts. |
| Semantic preferences/calibrations derived from multiple episodes | **Covered** | FR-17; addendum “Learning Policy” | Promotion requires a minimum sample count and linked supporting episodes. |
| New observation increases evidence but cannot immediately become a rule | **Covered** | FR-16–FR-17; SM-7 | Append-only episodes and single-observation non-promotion are testable. |
| Confidence grows with consistency | **Covered** | FR-17; addendum | Exact formula remains an open configuration decision, appropriately. |
| Contradictions reduce confidence | **Covered** | FR-17; addendum | Explicit. |
| Age decay | **Covered** | FR-17; Open Question 1; addendum | Policy is required; half-life/default remains open. |
| Minimum samples before promotion | **Covered** | FR-17; SM-7; Open Question 1 | Required and measurable. |
| Statistical incremental learning, not fine-tuning | **Covered** | PRD thesis, §6, Non-Goals; addendum | Fine-tuning and online training are explicitly excluded. |
| Explain total score and each criterion | **Covered** | FR-10–FR-12 | Fully testable. |
| Explain checked restrictions | **Covered** | FR-6–FR-9, FR-12 | Each rule yields pass/fail evidence. |
| Report a confidence level distinct from score | **Covered** | Glossary; FR-13; risk table | The distinction is central and includes a scenario proving high score/low confidence. |
| Report data quality/freshness | **Covered** | FR-13–FR-14 | Factors and warnings are structured and expose fallback and impact. |
| Warn about GPS, weather, and traffic | **Covered** | FR-14 | Missing, stale, estimated, and unavailable cases are included. |
| Show alternatives and reasons for discard | **Covered** | FR-12 | Eligible and ineligible candidates are separated; reasons are reconstructable. |
| Confidence uses availability/freshness, evidence quantity, top-two gap, and uncertain conditions | **Covered** | FR-13; Open Questions 3–4 | Required factors are present; exact formula and freshness thresholds remain deliberately open. |
| Mean time to assignment KPI | **Covered** | FR-18; SM-5 | Named as “time to assignment,” with definition metadata required. |
| SLA compliance KPI | **Covered** | FR-18; SM-5 | Covered. |
| Manual reassignment rate KPI | **Covered** | FR-18; SM-5 | Covered. |
| Mean absolute estimated-time error KPI | **Covered** | FR-18; SM-5 | Covered. |
| Workload balance KPI | **Covered** | FR-18; SM-5; Open Question 5 | Measure choice remains open, not omitted. |
| Recommendation acceptance KPI | **Covered** | FR-18; SM-5 | Counter-metric prevents gaming acceptance. |
| Total and per-agent latency KPI | **Covered** | FR-2, FR-18; NFR-1 | Per-stage timing is contractual; “Agent Stage” is the PRD term. |
| First-Time Fix Rate when outcomes exist | **Covered** | FR-16, FR-18; Open Question 6 | Optionality is preserved exactly. |
| Update PRD | **Covered by current artifact** | Entire PRD | This reconciliation is part of finalization, not evidence that implementation exists. |
| Define architecture and JSON contracts | **Deferred appropriately / partial contract gap** | Addendum “JSON Contracts”; PRD FR-2–FR-5; next-step routing implied by plan | Architecture belongs downstream. However, the PRD could still state more directly that **every** Agent Stage input and output must validate against a versioned schema before transition. |
| Create epics/stories with acceptance criteria | **Deferred appropriately** | Outside PRD scope | The PRD has testable consequences ready for decomposition, but epics/stories are not generated here. |
| Implement orchestrator, constraints, scoring | **Deferred appropriately** | FR-1–FR-12; MVP scope | Product requirements are complete enough to authorize implementation; implementation status is not claimed. |
| Migrate JSON data into SQLite | **Covered as scope/direction** | PRD §8; addendum “SQLite” | Importing seed records without fabricating historical evidence is a useful preserved nuance. |
| Simulation API exposing breakdown and confidence | **Gap** | No explicit API requirement; response fields appear in FR-10–FR-14 | The behavior of a response is defined, but an API surface is not. If the API is part of the academic demonstration, add a functional requirement or explicitly defer it to architecture. |
| KPI panel | **Covered** | FR-18; §8 | The PRD requires a panel and reproducible definitions. |
| Hard-rule and uncertainty tests | **Covered** | §8, SM-1, SM-6; addendum “Academic Evidence” | Representative automated testing is in MVP scope. |
| Compare assignments with and without Memory | **Covered** | FR-19; SM-4; UJ-3 | Same-snapshot comparison and invariant hard constraints are explicit. |
| Decision, limits, and risks document | **Partially covered** | PRD §8 “Academic decision/limitations evidence”; §10; addendum “Academic Evidence” | Risks exist in the PRD, but the distinct deliverable has no required outline, ownership, export format, or acceptance test. This should become a story/deliverable criterion. |
| Run BMAD flows in the stated order and in clean tasks | **Deferred appropriately** | Not a product requirement | This is process guidance for the project team. It should remain in planning/task orchestration rather than the PRD. |

## Conflicts and their resolution

### Maximum-day overtime exception

- **Earlier source direction:** existing rules allowed a priority-5 overtime
  exception.
- **Professor feedback:** exceeding the maximum workday is a hard exclusion.
- **Resolution:** PRD FR-8 adopts the professor's stricter rule and explicitly
  states that emergency priority cannot silently bypass it. A future authorized
  exception workflow is out of MVP scope. The addendum records the conflict.
- **Assessment:** resolved transparently; no silent behavior change.

### “Thought traces” versus explainability

- **Earlier source direction:** some UI/spec language requested exposed thought
  traces.
- **Professor feedback:** requires explainability through score components,
  restrictions, confidence, data warnings, alternatives, and discard reasons.
- **Resolution:** PRD NFR-4 and FR-10–FR-14 require structured, reproducible
  evidence while explicitly excluding private chain-of-thought.
- **Assessment:** the professor's explainability goal is preserved with a safer
  and more testable mechanism.

### Existing technology direction versus SQLite MVP

- **Earlier source direction:** prior specifications referenced Express/React
  and a later PostgreSQL/pgvector roadmap; the brownfield implementation is
  Python/vanilla JavaScript with JSON persistence.
- **Professor feedback:** requires SQLite and statistical incremental learning.
- **Resolution:** PRD §6 mandates SQLite for MVP and avoids prescribing a web
  framework; Non-Goals exclude vector databases and model fine-tuning. The
  addendum preserves the brownfield facts.
- **Assessment:** resolved in favor of the professor's prototype scope without
  unnecessary framework churn.

## Gaps requiring a deliberate disposition

### G1 — Simulation API is not contractual

The feedback explicitly asks for an “API de simulación con desglose y
confianza.” The PRD specifies response content but not the existence, consumer,
or minimum operations of an API.

**Recommended disposition:** either add an MVP functional requirement for a
local simulation/replay API, with schema-valid response and Memory on/off
control, or record explicitly that architecture may satisfy the demonstration
through an internal service/UI boundary rather than a public API.

### G2 — Universal JSON contract is weaker in the PRD than in the addendum

FR-2 records a schema version, FR-3 handles invalid stage output, and FR-4/FR-5
cover structured Work Order output. The stronger statement—every Agent Stage
consumes and emits versioned, schema-valid JSON and validation precedes every
transition—appears only in the addendum.

**Recommended disposition:** promote the observable portion to FR-1 or FR-2:
every stage boundary validates its versioned input/output contract; validation
failure prevents transition and is persisted as a typed error. Schema
technology and exact definitions can remain in architecture.

### G3 — Stage payload retention/retrieval is ambiguous

FR-2 requires input/output snapshot references, while NFR-7 requires a run-level
input snapshot and candidate evidence. This is probably intended to make each
stage reproducible, but retrievability and retention of every referenced stage
payload are not stated.

**Recommended disposition:** clarify that each snapshot reference resolves to
persisted, schema-versioned content retained for the prototype's evidence
window, with redaction where needed.

### G4 — Academic narrative deliverable lacks acceptance criteria

The decision/limitations/risk document is in scope but underdefined. The current
risk table is product content, not necessarily the requested academic evidence
package.

**Recommended disposition:** leave the PRD concise and create an epic/story
criterion requiring a reproducible report that identifies configuration,
scenario inputs, results, limitations of synthetic data, rejected alternatives,
known risks, and links to supporting run IDs.

### G5 — “Proposal” is not explicitly classified as Episodic Memory

Candidate evidence and the recommendation are retained for audit, but FR-16
lists only the selected technician and service outcome fields as Episodic
Memory. The feedback explicitly lists proposals among episodic records.

**Recommended disposition:** clarify in the data model or FR-16 that the
recommendation/proposal snapshot and alternatives visible at decision time are
immutable episodic evidence linked to the Human Decision.

## Qualitative ideas at risk of being silently weakened

These ideas are present in substance, but their original rhetorical emphasis
could disappear during decomposition:

1. **“Demonstrable, not descriptive.”** The PRD carries this through UJ-3,
   reproducible runs, KPIs, tests, and configuration snapshots. Stories should
   preserve visible evidence rather than treating logging as backend-only work.
2. **“Controlled” learning.** The mechanics are covered, but the important
   product feel is conservative: one surprising dispatch must never appear to
   have “trained the AI.” UI copy and the academic report should distinguish an
   observation, accumulated evidence, and an active Semantic Pattern.
3. **No inflated AI claim.** Fine-tuning is excluded, yet the PRD does not
   explicitly require user-facing or academic language to call the mechanism
   incremental statistics rather than model training. This should be preserved
   in UX/content and the evidence report.
4. **Confidence is not score.** This is strongly covered in requirements but is
   vulnerable to visual collapse into a single badge or ranking number. UX
   specifications should keep them visually and semantically separate.
5. **The orchestrator is authoritative.** The PRD says Agent Stages cannot
   control transitions or bypass rules. Architecture and stories should retain
   this as a system invariant, not reinterpret the pipeline as autonomous agents
   coordinating among themselves.
6. **All-agent shared memory.** SQLite shared persistence is mandated, but the
   precise phrase “shared by all agents” is not reflected as an access and
   consistency contract. Architecture should define which stages read/write
   which records while keeping a single authoritative store.

## Items correctly left outside the PRD

- Exact state persistence schema and transition-table implementation.
- JSON Schema/OpenAPI technology and transport decisions.
- SQLite table design and migration mechanics.
- Exact confidence formula, freshness thresholds, decay half-life, minimum
  promotion sample count, tie-break rule, and workload-balance statistic; these
  are visible Open Questions and can use documented, tested defaults.
- Framework selection.
- Epic/story structure, sprint sequence, and task isolation for BMAD runs.

## Recommended update set

For the smallest faithful PRD revision:

1. Add the universal stage-boundary validation behavior to FR-2 or FR-3.
2. Clarify persisted/retrievable stage snapshots and episodic recommendation
   evidence.
3. Decide whether the simulation API is an MVP product requirement or an
   architecture-level implementation option, and record that decision.
4. Keep the academic report in MVP scope but define its acceptance criteria in
   epics/stories rather than expanding the core PRD.
5. Preserve the qualitative language around conservative statistical learning,
   non-inflated AI claims, and the visual distinction between score and
   confidence during UX and story decomposition.


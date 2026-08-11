# PRD Quality Review — Smart Dispatch IA v2.1

## Overall verdict

The PRD is structurally strong and unusually disciplined for an educational brownfield prototype: it has a specific thesis, coherent scope, stable requirements, explicit non-goals, measurable success criteria, and a clean separation between eligibility, ranking, confidence, and learning. It is not yet fully decision-ready for implementation, however, because several unresolved questions define core observable behavior—confidence calculation, semantic-pattern promotion and decay, freshness thresholds, and tie-breaking—while §11 simultaneously claims that none blocks architecture or story decomposition.

The document is ready to guide architecture at a conceptual level, but should pass one more product-decision round before being treated as a build contract. The central remediation is not more prose; it is to convert behavioral unknowns into approved defaults, bounded rules, or explicitly owned deferred decisions with acceptance consequences.

## Decision-readiness — thin

The product stance is decisive: the assistant is decision support rather than autonomous workforce management (§1); Hard Constraints precede ranking (§4.3); Memory cannot restore eligibility (§4.3, §4.6); and implementation mechanisms are intentionally separated into the addendum. The addendum's Reconciliation Notes also records three meaningful choices against earlier material: Python/vanilla JavaScript is the brownfield baseline without becoming a product mandate, the stricter maximum-day exclusion wins over the former priority-5 exception, and structured evidence replaces “thought traces.”

The weakness is that some of the most consequential runtime choices remain open in §11. These are not merely tuning questions: they determine which Technician is recommended, when confidence is low, and when learning affects future scores. The statement that all six questions “do not block architecture or story decomposition” is too broad and conceals differing levels of impact. The PRD also has no explicit owner, deadline, or approval criterion for these decisions.

### Findings

- **high** Core behavioral contracts are still undecided (§11 questions 1–4) — Minimum sample count and decay, deterministic tie-breaking, confidence aggregation, and data-freshness thresholds materially determine outputs required by FR-12, FR-13, FR-14, and FR-17. Calling all of them non-blocking risks stories being authored around incompatible assumptions. *Fix:* Resolve them to approved MVP defaults before story acceptance criteria are finalized, or mark each with owner, decision deadline, allowed range, and the stories it blocks.
- **medium** The PRD records choices but not their trade-offs in the main decision narrative (§1, §6; addendum “Reconciliation Notes”) — The chosen approach is clear, but the costs accepted—such as reduced realism from seeded data, limited learning expressiveness, and no emergency overtime path—are scattered or implicit. *Fix:* Add a concise “Key product decisions and trade-offs” subsection that states choice, rejected alternative, benefit, and accepted cost, while keeping technical rationale in the addendum.
- **medium** Deferred decisions lack governance (§11) — Open Questions have neither accountable owner nor revisit condition, and no distinction is made between demo configuration choices and product semantics. *Fix:* Add owner, required-by milestone, default-if-unresolved, and affected FR/NFR to every open question.

## Substance over theater — strong

The content is earned. The three journeys each drive concrete behavior: UJ-1 supports eligibility and explanation, UJ-2 supports override and learning, and UJ-3 supports the academic evidence objective. They are few, named, and product-specific. The vision is not category-generic; its separation of Hard Constraints, Objective Score, Recommendation Confidence, and auditable evidence is the document's operative thesis.

The NFRs are also mostly product-specific and bounded. Performance names a percentile, threshold, and dataset context; determinism identifies the input boundary; integrity describes atomicity; privacy restricts long-term location granularity; and auditability names retained evidence. The addendum appropriately contains solution direction rather than inflating the PRD with architecture theater.

### Findings

- **low** Accessibility remains less testable than the other NFRs (§5, NFR-6) — “Support keyboard operation, visible focus, semantic labels, and text alternatives” is relevant, but it lacks a conformance target or explicit screen/flow coverage. *Fix:* Name the MVP flows to be checked and either adopt a suitable WCAG level or define a compact, testable accessibility checklist.

## Strategic coherence — strong

The PRD has a clear thesis: safe recommendations require deterministic eligibility, explainable ranking, separate uncertainty, conservative learning, and human accountability (§1). The feature sequence follows that thesis from orchestration and capture through feasibility, ranking, confidence, decision, learning, and evidence (§4.1–§4.7). MVP scope (§8) is a coherent demonstrable-prototype scope rather than an arbitrary feature backlog.

Success Metrics validate the thesis rather than usage volume. SM-1 through SM-4 test invariants, SM-6 tests the distinction between score and confidence, and SM-7 tests conservative promotion. The counter-metrics directly guard against gaming acceptance, SLA compliance, and memory influence. This is one of the strongest parts of the PRD.

### Findings

- **medium** The product-level demonstration outcome lacks an explicit pass criterion (§1, §9) — The thesis says the prototype succeeds when Memory changes recommendations “in a controlled, explainable way,” but the metrics require a Memory on/off comparison without requiring a seeded case where Memory legitimately changes rank or recommendation. *Fix:* Add a metric requiring at least one reproducible scenario in which eligible-candidate ordering changes because of a visible Memory contribution while all Hard Constraints remain invariant, plus one scenario in which Memory correctly makes no change.
- **low** “Repair the current simulator so it runs reliably” is scope language without a strategic acceptance boundary (§8.1) — It is neither tied to a specific user journey nor defined by a success metric. *Fix:* Replace it with a verifiable baseline such as clean startup, successful seeded end-to-end run, and absence of known compile/runtime blockers.

## Done-ness clarity — thin

Most FRs are exemplary: each carries concrete consequences, failure behavior, and observable evidence. FR-6 through FR-12 are particularly suitable for downstream test generation, and KPI handling in FR-18 avoids the common ambiguity between unavailable and zero. The NFRs are concise and mostly testable.

The rating is nevertheless thin because the unresolved formulas and thresholds sit inside central requirements. “Configured” does not by itself define done when no valid bounds, defaults, or normative reference exist. Engineers could satisfy the prose with materially different products.

### Findings

- **high** Recommendation Confidence has inputs but no normative behavior (§4.5 FR-13; §11 question 3) — The PRD requires factor contributions and deterministic handling for fewer than two candidates, but neither aggregation, bounds per factor, nor the low/medium/high interpretation is defined. *Fix:* Specify the MVP formula or a bounded configuration contract with default weights, normalization, missing-factor behavior, and threshold labels, then add example vectors with expected confidence.
- **high** Semantic Pattern promotion is not acceptance-test complete (§4.6 FR-17; §11 question 1) — “Consistent,” “contradictions,” “age decay,” and “configured minimum sample count” are not operationally defined. The addendum repeats the policy but does not close the contract. *Fix:* Define consistency and contradiction predicates, promotion/deactivation conditions, MVP minimum count, confidence update rule, and decay time basis with representative expected outcomes.
- **high** Data freshness behavior is under-specified (§4.5 FR-14; §11 question 4) — Warnings must identify freshness and fallback impact, yet the current/stale/unavailable thresholds and behavior by source are unresolved. *Fix:* Add a table per data source with age bands, fallback, confidence effect, and whether dispatch may proceed.
- **medium** Deterministic ranking is incomplete without its tie-break (§4.4 FR-12; §11 question 2) — Identical score inputs can still produce different recommendations across implementations. *Fix:* Declare a stable ordered tie-break, including the final stable key.
- **medium** KPI correctness is asserted without definitions in the artifact (§4.7 FR-18; §11 questions 5–6) — FR-18 says every KPI defines numerator, denominator, exclusions, window, and unit, but those definitions are not present in the PRD or addendum. *Fix:* Add a KPI contract table, including workload-balance statistic and First-Time Fix completeness policy.
- **medium** Performance measurement conditions are incomplete (§5 NFR-1) — The 3-second p95 target names the seeded dataset but not workload size, warm/cold state, run count, hardware envelope, or whether optional LLM assistance is enabled. *Fix:* Define a reproducible benchmark profile and separately bound deterministic-only versus LLM-assisted paths if both are demonstrable.

## Scope honesty — adequate

The PRD is candid about being a local educational prototype with synthetic or seeded data (§6), explicitly excludes production integrations and deployment (§7), and avoids claiming real-world KPI improvement from synthetic results (§8.2). The maximum-day emergency exception is clearly deferred in FR-8 and the addendum explains the prior-rule conflict. The distinction between unknown KPI data and zero is also honest.

However, the Assumptions Index says there are no silent product assumptions while several defaults may be introduced during implementation (§11–§12). That mechanism would turn unresolved product behavior into implementation assumptions without an audit trail. For a chain-top PRD, the open-item density is manageable in count but high in consequence.

### Findings

- **high** The Assumptions Index conflicts with the proposed defaulting strategy (§11–§12) — “No silent product assumptions” is immediately weakened by allowing implementation to choose documented configuration defaults for all Open Questions. Documentation after an implementer chooses a default is not equivalent to product confirmation. *Fix:* Either approve and record defaults in the PRD, or add explicit `[ASSUMPTION: …]` entries inline and round-trip them through the Assumptions Index with owner and validation plan.
- **medium** Some omissions are framed as future possibilities without a complete MVP boundary (§4.3 FR-8) — The emergency exception is out of scope, but the expected MVP behavior when no candidate is feasible during a safety-critical order is only “no recommendation”; escalation or operator recovery is not specified. *Fix:* State the MVP recovery behavior and make clear that it does not authorize an ineligible assignment.
- **low** Retention scope is incomplete (§5 NFR-5, NFR-7; §7) — The PRD says what is retained for audit and restricts coordinates in Semantic Patterns, but not retention duration or deletion behavior for Dispatch Runs and Episodic Memory. *Fix:* Declare an educational-prototype retention rule or explicitly mark retention lifecycle as a non-goal.

## Downstream usability — adequate

The artifact is highly extractable: FR IDs are unique and contiguous; the three journeys are named and linked to feature groups; Success Metrics reference the FRs they validate; the glossary defines most domain nouns; and requirements use stable terminology. The addendum contains brownfield facts and implementation direction that architecture can consume without polluting the product contract.

The principal usability risk is that downstream workflows must invent acceptance details for the central algorithms. There are also a few terms whose overloaded or undefined use could cause schema and UI drift.

### Findings

- **high** Architecture and story creation cannot source-extract several acceptance contracts without invention (§4.5, §4.6, §11) — Confidence, learning, freshness, and tie-breaking all require downstream authors to make product choices. *Fix:* Close the core defaults before story generation and cross-reference the resulting tables from the affected FRs.
- **medium** “Memory” is overloaded across the document (§1, §4.4 FR-10, §4.6, §4.7 FR-19, §9) — It can mean Episodic Memory, Semantic Patterns, the scoring component, or the enabled/disabled experiment condition. This ambiguity matters for the on/off comparison and for what data the score may consume. *Fix:* Add distinct glossary terms such as `Memory Score Component` and `Memory Experiment Mode`, and specify exactly which reads/writes are disabled in the off condition.
- **medium** Success-metric traceability is one-way and occasionally incomplete (§9) — SM-8 points to NFR-1 only implicitly, while FR-18's eight KPIs are treated as “reported” without metric IDs or definitions. *Fix:* Give KPI definitions stable identifiers and explicitly name the target requirement(s) for SM-5 and SM-8.
- **low** “Agent Stage” schema validity is required without a discoverable contract location (§3, §4.1 FR-2, addendum “JSON Contracts”) — Architecture knows schemas are needed, but downstream readers cannot tell whether their fields are product-required or architectural detail. *Fix:* Identify the minimum product-required envelope fields and leave payload schema design to architecture.

## Shape fit — strong

The shape fits a multi-stakeholder educational brownfield prototype that feeds architecture and story creation. Three compact journeys carry meaningful context without persona theater; feature groups correspond to the deterministic pipeline; NFRs and guardrails isolate cross-cutting concerns; and the technical addendum preserves brownfield and professor-feedback mechanisms outside the PRD. The document is formal enough for its academic and downstream role without becoming a solution-design transcript.

The existing and target states are clearly distinguished in the addendum, and brownfield divergences are named rather than silently normalized. No major shape mismatch was found.

### Findings

- **low** Brownfield repair is represented mainly in the addendum, but the transition from current to target lacks a product-visible compatibility statement (§0, §8; addendum “Brownfield Baseline”) — It is unclear whether existing seeded scenarios, data files, or UI flows must remain compatible. *Fix:* State which current assets or user flows must be preserved, migrated, or may be replaced.

## Mechanical notes

- **ID continuity:** UJ-1–UJ-3 and FR-1–FR-19 are contiguous and unique. SM-1–SM-8 are contiguous; SM-C1–SM-C3 form a clear separate counter-metric namespace.
- **Cross-references:** Feature-group references to UJ-1–UJ-3 resolve. Success Metrics reference valid FR IDs. The section reference from §8.2 to §7 resolves.
- **Glossary drift:** Capitalized domain terms are generally stable. The main ambiguity is `Memory`, which spans the broad subsystem, Episodic Memory, Semantic Patterns, the objective-score component, and the experiment toggle. `First-Time Fix Rate` appears in FR-18 but is not defined in the glossary.
- **Assumptions Index roundtrip:** There are no inline `[ASSUMPTION: …]` tags and the index says none were introduced, so the mechanical roundtrip is internally complete. Semantically, this is weakened by the permission in §11 to choose configuration defaults during implementation.
- **UJ protagonist naming:** All journeys have named protagonists—Laura, Martín, and Rossy—and include context inline.
- **Required shape:** Vision/thesis, users and journeys, glossary, grouped FRs, NFRs, constraints, non-goals, MVP scope, success and counter-metrics, risks, open questions, and assumptions are present. The missing material is behavioral resolution, not section furniture.
- **Status:** Frontmatter remains `draft`, which is appropriate given the unresolved high-impact product decisions.

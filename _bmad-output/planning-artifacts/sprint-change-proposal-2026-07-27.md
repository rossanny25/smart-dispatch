---
project: smart-dispatch-ia-spec-v2
date: 2026-07-27
status: approved
implementation_status: applied
mode: batch
change_scope: moderate
trigger:
  - CQ-1
  - MQ-1
  - MQ-2
  - MQ-3
source_report: implementation-readiness-report-2026-07-27.md
---

# Sprint Change Proposal — Implementation Readiness Corrections

## 1. Issue Summary

The Implementation Readiness assessment found that the approved product scope is fully covered but the story structure is not yet safe for sprint execution:

1. Epic 2 advances an outcome to `LEARN` but requires future Epic 3 behavior to append Episodic Memory and complete the run.
2. Stories 1.7, 1.9, and 4.3 combine too many independently testable responsibilities for one development-agent context.

The trigger is a planning-quality defect discovered before implementation, not a new product requirement or architecture limitation.

## 2. Change Navigation Checklist

### Trigger and Context

- [x] **1.1 Trigger identified:** Readiness findings CQ-1 and MQ-1 through MQ-3; affected stories 1.7, 1.9, 2.2/3.1, and 4.3.
- [x] **1.2 Core problem:** Original requirements were understood correctly, but decomposition placed completion behavior in a future epic and oversized three stories.
- [x] **1.3 Evidence:** `implementation-readiness-report-2026-07-27.md`, FR16, Architecture AD-17/AD-25, and current story acceptance criteria.

### Epic Impact

- [x] **2.1:** All current epics remain viable after story-level correction.
- [x] **2.2:** Epic 2 must complete baseline Episodic Learning before Epic 3.
- [x] **2.3:** Epics 1 and 4 require story splits; Epic 3 changes from creating the first episode to consuming completed episodes for Semantic Pattern policy.
- [N/A] **2.4:** No epic is obsolete and no new epic is required.
- [x] **2.5:** Epic order remains unchanged.

### Artifact Impact

- [x] **3.1 PRD:** No requirement, MVP, metric, or non-goal change.
- [x] **3.2 Architecture:** No Architecture Decision changes; corrections improve conformance to AD-17 and AD-25.
- [N/A] **3.3 UX contract:** No independent UX artifact exists; embedded browser behavior is preserved.
- [x] **3.4 Other artifacts:** Update `epics.md`; regenerate readiness report; generate sprint status only after READY. `project-context.md` remains valid.

### Path Evaluation

- [x] **4.1 Direct Adjustment — Viable:** Medium restructuring effort, low product/technical risk.
- [N/A] **4.2 Rollback — Not viable/needed:** No implementation sprint has begun.
- [N/A] **4.3 MVP Review — Not needed:** MVP remains achievable without scope reduction.
- [x] **4.4 Selected path:** Direct Adjustment. It preserves product scope, architecture, epic order, and FR coverage while restoring independence and agent-sized units.

### Proposal and Handoff

- [x] **5.1–5.4:** Issue, impacts, chosen path, MVP impact, and action sequence are documented below.
- [x] **5.5 Handoff:** Product Owner/Developer backlog correction, followed by readiness validation and Sprint Planning.
- [x] **6.1–6.2:** Checklist and proposal reviewed for consistency.
- [x] **6.3:** Approved by the user on 2026-07-27.
- [N/A] **6.4:** No `sprint-status.yaml` exists yet.
- [x] **6.5:** Handoff activated for backlog correction, readiness revalidation, and conditional Sprint Planning.

## 3. Impact Analysis

### Epic Impact

- **Epic 1:** Remains the safe recommendation increment; increases from 9 to 11 smaller stories.
- **Epic 2:** Remains Human Decision and Service Outcome; increases from 3 to 4 stories and becomes independently complete.
- **Epic 3:** Still owns controlled Semantic Pattern learning and Memory experiments; it consumes existing episodes rather than completing FR16 retroactively.
- **Epic 4:** Remains operational/academic evidence; increases from 3 to 4 stories.

### Story Impact

- Split Story 1.7 into auditable orchestration and recovery/concurrency/performance.
- Renumber the browser story from 1.8 to 1.9.
- Split Story 1.9 into migration/compatibility (1.10) and first-increment verification (1.11).
- Add baseline Episodic Learning as Story 2.3 and renumber the browser flow to 2.4.
- Refocus Story 3.1 on aggregation/promotion from already persisted episodes.
- Split Story 4.3 into report/export (4.3) and course-delivery verification/cutover (4.4).

### Artifact and Technical Impact

- PRD and Architecture Spine remain unchanged.
- FR coverage remains 100%.
- Persistence responsibilities become clearer: Outcome remains a separate command; baseline LEARN atomically appends the episode, records its ledger result, and completes the run.
- No code rollback, infrastructure change, or UX redesign is required.

## 4. Recommended Approach

**Direct Adjustment — Moderate backlog reorganization**

- **Effort:** Medium
- **Risk:** Low
- **Scope impact:** None
- **Architecture impact:** Improved conformance
- **Rationale:** The defects are decomposition problems and can be corrected entirely inside `epics.md`.

## 5. Detailed Change Proposals

### Change A — Split Story 1.7

**OLD**

`Story 1.7: Execute and Recover an Auditable Dispatch Run` combines orchestration, snapshots, stage evidence, concurrency, failure handling, resume, evidence retrieval, idempotency, and performance.

**NEW**

- `Story 1.7: Execute an Auditable Dispatch Run` — immutable snapshot, orchestrated CAPTURE/ANALYZE/PLAN/EVALUATE, stage validation/evidence, `WAIT_FOR_DECISION`, typed failure, and `NO_FEASIBLE_CANDIDATES`.
- `Story 1.8: Recover, Protect, and Benchmark Dispatch Runs` — optimistic concurrency, crash resume, idempotency, evidence retrieval/redaction, and NFR1 benchmark.

**Rationale:** Two independently testable application outcomes with a one-way dependency.

### Change B — Split Story 1.9 and remove future-story wording

**OLD**

`Story 1.9: Preserve Brownfield Compatibility and Verify the First Increment` combines legacy adapters, migration/provenance, fixtures, rollback, all Epic 1 suites, and cutover gating; it names future Story 3.1.

**NEW**

- Renumber the approved browser story to `Story 1.9`.
- `Story 1.10: Migrate the Brownfield Prototype Safely` — legacy translation adapters, IDs/timestamps, deterministic learning import manifest, fixtures, backup/rollback.
- `Story 1.11: Verify the First Safe Dispatch Increment` — complete Epic 1 unit/integration/contract/browser/determinism/performance gate and retention of legacy surfaces.
- Replace the numbered future-story reference with “until Semantic Pattern persistence is introduced by a later approved learning story.”

**Rationale:** Separates migration risk from acceptance evidence and removes explicit forward coupling.

### Change C — Complete Epic 2 independently

**OLD**

Story 2.2 advances to `LEARN`; Story 3.1 later appends the episode and reaches `COMPLETED`.

**NEW**

- Keep `Story 2.2: Record the Service Outcome for Episodic Learning` as the separate Outcome command that advances to `LEARN`.
- Add `Story 2.3: Complete Baseline Episodic Learning`:
  - append one immutable episode from the persisted outcome;
  - record `(outcome_id, learning_policy_version)` exactly once;
  - allow only an inactive, non-influential pattern result from a single observation;
  - atomically persist episode/ledger/result and transition to `COMPLETED`;
  - use `LEARN_FAILED` and idempotent retry on failure.
- Renumber the browser story to `Story 2.4`.
- Refocus Story 3.1 to aggregate existing episodes, apply contradiction/decay/promotion, and process each episode/policy version exactly once without appending duplicate episodes.

**Rationale:** Epic 2 becomes a complete decision/outcome/evidence flow while Epic 3 adds controlled semantic value.

### Change D — Split Story 4.3

**OLD**

`Story 4.3: Generate the Course-Ready Academic Evidence Package` includes report generation, reproducibility, accessible browser export, complete program acceptance, and legacy cutover.

**NEW**

- `Story 4.3: Generate and Export the Academic Evidence Package` — report/manifest content, limitations, unavailable evidence, reproducibility, and accessible export.
- `Story 4.4: Verify the Course-Ready System and Complete API Cutover` — UJ-1 through UJ-3, FR/NFR/SM evidence gate, `/api/v1`-only journey/error tests, and conditional legacy removal.

**Rationale:** Separates a user-facing reporting capability from the final system-wide release gate.

### Change E — Update Traceability Metadata

**OLD**

FR16 is listed as Epic 2 ownership but completed across Epic 2 and Epic 3.

**NEW**

- Epic 2 Stories 2.2–2.4 fully own FR16.
- Epic 3 Story 3.1 references FR17 and consumes existing FR16 evidence.
- Update story counts and all renumbered cross-references while preserving the FR Coverage Map.

## 6. Implementation Handoff

**Classification:** Moderate

**Recipients and responsibilities:**

- **Product Owner / specification editor:** Apply the approved story splits, renumbering, and traceability updates to `epics.md`.
- **Readiness validator:** Re-run Implementation Readiness and confirm CQ-1/MQ-1–MQ-3 are closed.
- **Sprint planner:** Generate `sprint-status.yaml` only after readiness returns READY.
- **Developer agents:** Implement the resulting stories sequentially using `project-context.md`.

### Success Criteria

- Epic 2 reaches `COMPLETED` without Epic 3.
- No story requires a future story to function.
- Stories 1.7/1.8, 1.10/1.11, and 4.3/4.4 each fit a single development-agent context.
- FR1–FR21 and NFR1–NFR7 remain fully traceable.
- Re-run readiness status is READY.

## 7. Approval and Execution Log

- **Approved by:** Rossy
- **Approval date:** 2026-07-27
- **Change scope:** Moderate
- **Artifact modified:** `_bmad-output/planning-artifacts/epics.md`
- **Resulting story counts:** Epic 1 — 11; Epic 2 — 4; Epic 3 — 3; Epic 4 — 4
- **Total stories:** 22
- **Sprint status update:** Not applicable; Sprint Planning has not yet created `sprint-status.yaml`.
- **Handoff:** Re-run Implementation Readiness; if READY, hand off to Sprint Planning.

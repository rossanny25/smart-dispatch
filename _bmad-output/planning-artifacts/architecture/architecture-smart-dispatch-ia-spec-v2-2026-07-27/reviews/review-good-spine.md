# Good-Spine Rubric Review

**Artifact:** `ARCHITECTURE-SPINE.md`  
**Review lens:** Good-spine checklist from `bmad-architecture/references/reviewer-gate.md`  
**Verdict:** **NEEDS REVISION** — the spine is structurally strong and brownfield-aware, but it leaves core recommendation behavior open to incompatible implementations and omits an executable serving choice and a required failure transition.

## Gate Summary

| Checklist dimension | Result | Notes |
| --- | --- | --- |
| Real divergence points fixed | Partial | Boundaries, ownership, persistence, migration, state ownership, and evidence are strong. Core score/confidence normalization remains underdetermined. |
| AD rules enforceable and preventive | Partial | Most rules are testable; AD-16 claims a complete behavioral registry that its referenced PRD does not actually contain. |
| Deferred items safe for lower-level work | Pass | Deferred items have suitable revisit conditions and do not block the local classroom MVP, except that the unbound serving/runtime choice is not listed there. |
| Named technology verified-current | Partial | All named releases exist, but several pins are already superseded and no compatibility/intent note supports the selected coherent set. The ASGI server is absent entirely. |
| Brownfield ratified, not contradicted | Pass | The migration adapter, legacy ID strategy, Python/vanilla-JS direction, local-only posture, and vendoring requirement respond directly to the inspected codebase. |
| PRD capabilities covered | Partial | The capability map covers FR-1–FR-21 at a module level, but FR-3 failure behavior and the calculation semantics behind FR-10/FR-13 remain incomplete. |
| Parent spine compatibility | Not applicable | No parent spine is declared. |
| All feature-altitude dimensions addressed | Partial | Runtime/deployment, persistence, security boundary, migration, testing, data ownership, and API conventions are addressed; the concrete ASGI runtime and crash/resume behavior are not fully closed. |

## Findings

### HIGH — AD-16 binds a behavioral registry that does not define the core normalization algorithms

**Evidence:** AD-4 requires pure score and confidence calculations, while AD-16 incorporates PRD §§4, 5, 9, 11, and 13 as contract/configuration version `v1`. The PRD supplies aggregate weights, tie-breaking, freshness thresholds, and learning defaults, but it does not define how raw inputs become the five 0–100 score components (`SLA`, `proximity`, `workload_balance`, `quality`, `memory`) or the four confidence factors (`data_quality`, `historical_evidence`, `score_margin`, `condition_certainty`). It also leaves `penalties` operationally undefined. AD-23 makes the 50 km rule a soft penalty but does not specify its magnitude or whether the “only certified eligible Technician” case waives that penalty.

**Why this fails the rubric:** Two scoring or confidence stories can comply with every stated AD and still produce different rankings and confidence values from the same snapshot. This is the primary product behavior and directly undermines AD-4, NFR-2, SM-2, and the Memory on/off experiment.

**Disposition:** **Autofix before handoff.** Either bind explicit `v1` formulas/defaults in the behavioral registry or name one canonical versioned policy artifact, with complete input-to-component algorithms and penalty rules, that AD-16 makes authoritative. Preserve provisional values as approved-or-assumed configuration, but do not leave the algorithm shape open.

### HIGH — The state machine has no failure transition from `LEARN`

**Evidence:** The diagram permits typed failure from `CAPTURE`, `ANALYZE`, `PLAN`, and `EVALUATE`, but `LEARN` can only transition to `COMPLETED`. AD-18 explicitly treats `LEARN` as a stage, and FR-3 requires stage failure to be modeled as an explicit outcome. AD-5 guarantees rollback for the command but does not define the run outcome after a learning failure.

**Why this fails the rubric:** Independent implementations can leave the run in `LEARN`, mark it `FAILED`, or mark it `COMPLETED` with a warning. All three interpretations fit the present rules, producing incompatible audit histories and recovery behavior.

**Disposition:** **Autofix before handoff.** Add `LEARN --> FAILED: typed failure` or define a distinct recoverable learning-failure state and its permitted retry. If the intended policy is that operational completion succeeds while learning failure is non-fatal, encode that explicitly instead of using generic stage-failure semantics.

### HIGH — The operational serving runtime is incomplete

**Evidence:** AD-13 says the MVP runs as “one FastAPI process,” AD-22 fixes the bind address, and the Stack pins FastAPI, but FastAPI is an ASGI application framework rather than the serving process. No ASGI server, version, or canonical launch contract is selected. The structural seed removes the existing `http.server` launcher after cutover.

**Why this fails the rubric:** Builders can independently choose Uvicorn, Hypercorn, FastAPI CLI defaults, or a custom process with different worker, reload, logging, and bind behavior. This leaves the operational/environmental envelope incomplete and may invalidate the single-process/SQLite assumptions.

**Disposition:** **Autofix before handoff.** Pin one ASGI server and bind a canonical launch rule: one worker, `127.0.0.1`, migrations before serving, no reload in benchmarks/evidence runs, and an explicit composition-root target.

### MEDIUM — “Verified stable stack” is not a reproducible compatibility assertion

**Evidence:** The versions exist, but by the review date FastAPI 0.138.2 has been superseded by 0.139.2, coverage.py 7.13.5 by 7.15.2, and Python 3.12.10 by 3.12.13. Python 3.12.10 has a defensible installer-availability reason in the memlog, but the spine does not state the compatibility intent for the complete pinned set. SQLite is described only as the version bundled with CPython rather than an observed numeric version/platform constraint.

**Why this matters:** “Pinned” and “verified-current” are different claims. A lockfile will make Python packages reproducible, but it does not establish that the combination was tested or that the bundled SQLite capabilities are invariant across supported evaluator platforms.

**Disposition:** **Autofix or discuss.** Record the tested compatibility set and evaluator platform, update superseded pins where safe, and pin/verify the SQLite minimum required feature level. If older stable pins are intentional, state the reason rather than implying they are the current releases.

### MEDIUM — Crash recovery and command resumption are not bound

**Evidence:** AD-20 safely commits each stage with optimistic concurrency, but no rule states what happens when the process restarts with a run left in an active stage or waiting state. AD-13 requires migrations before serving, but not run reconciliation. FR-2 requires preserved prior completed records, and replay exists, yet replay is not clearly distinguished from resume.

**Why this matters:** A stage runner can automatically retry, mark stale work failed, or require explicit replay. Those choices change duplicate side-effect risk and audit semantics.

**Disposition:** **Defer explicitly or autofix.** For this single-process MVP, the lean rule can be: on startup, do not auto-execute active runs; mark an interrupted in-progress stage as typed failure and require an idempotent explicit retry/replay that creates or records the correct lineage.

### LOW — The browser smoke-test tool is left open

**Evidence:** AD-15 mandates browser smoke tests and the Stack does not name a browser automation tool.

**Why this matters:** This is unlikely to alter product semantics, but stories may create incompatible test harnesses and duplicate setup.

**Disposition:** **Defer or seed.** Select one tool when the first browser-test story is created, or list the choice under Deferred with that revisit trigger.

## Strengths

- The named paradigm and inward dependency direction are clear and appropriately terse.
- State ownership, hard-constraint precedence, immutable snapshots, command transactionality, optimistic concurrency, and Memory separation are genuine architecture invariants.
- Brownfield migration is unusually well handled: legacy routes are translation-only, legacy IDs retain provenance, JSON learnings do not masquerade as observations, and the current SPA remains usable during cutover.
- The local-only security posture, backup-before-destructive-change rule, DOM safety rule, and no-chain-of-thought evidence contract are well aligned to an academic prototype.
- The capability map makes omissions discoverable and gives downstream epic/story work stable AD references.

## Mechanical Check

The deterministic lint script reported **0 findings** when executed directly with Python. The documented `uv run` invocation could not run because `uv` is not installed in the reviewer environment; this is an environment/tooling limitation, not a spine lint failure.

## Recommended Gate Decision

Do not mark the spine `final` until the three **HIGH** findings are resolved. The medium findings may be fixed now or moved into `Deferred` with explicit revisit conditions. After changes, rerun deterministic lint and this rubric lens.

## Re-review

**Verdict:** **PASS WITH MINOR FIXES.**

AD-24 closes the calculation-registry gap; AD-25 plus the revised state machine close learning failure and crash/resume semantics; AD-26 fixes the ASGI launch and browser-test contracts; AD-27 closes snapshot, replay, KPI, API, and reset ownership. Deterministic lint again reports zero findings. No high-severity finding remains.

Before polish, remove the duplicated `Accessibility` convention row and clarify whether AD-23's “only certified eligible Technician” case waives the AD-24 distance penalty or merely permits the candidate to remain rankable with the penalty. These are editorial/medium consistency fixes and do not require another architecture decision if the intended behavior is stated explicitly.

# Nielsen UX/UI Heuristic Review

Target user: field-service dispatcher or course evaluator using the simulator to understand a dispatch recommendation.

## Summary

The interface is adequate for an academic prototype because it exposes orders, technicians, memory, and simulated dispatch output in one place. Its main UX gap is that some authoritative `/api/v1` evidence is stronger in the backend than in the current browser presentation.

## Heuristic Evaluation

| Heuristic | Current Evidence | Rating | Improvement |
| --- | --- | --- | --- |
| Visibility of system status | The UI shows dispatch stages and recommendation areas. | Good | Add explicit canonical run state and revision from `/api/v1`. |
| Match between system and real world | Uses dispatcher concepts: orders, technicians, zones, priority, recommendation. | Good | Add clearer labels for SLA, hard constraints, and confidence. |
| User control and freedom | Dispatcher can simulate and confirm/override in legacy flow. | Medium | Add undo/reset messaging and canonical decision flow. |
| Consistency and standards | Cards, lists, and status panels are visually consistent. | Good | Align all API errors to the same frontend presentation. |
| Error prevention | Backend validates canonical JSON and idempotency. | Medium | Surface validation before submit in the UI. |
| Recognition rather than recall | Seeded technicians/orders are visible. | Good | Keep selected order and environment visible during the full run. |
| Flexibility and efficiency | Simple single-page flow is fast for demo. | Medium | Add direct scenario buttons for academic evidence. |
| Aesthetic and minimalist design | The dashboard is suitable for demonstration. | Medium | Reduce decorative elements if they compete with evidence review. |
| Help users recognize and recover from errors | API has typed errors; UI needs fuller mapping. | Medium | Show safe error messages, retry action, and no-feasible explanation. |
| Help and documentation | README and runbook explain startup. | Good | Add a short in-app "about this scenario" panel for evaluators. |

## Audience Fit

Dispatchers need fast comparison, clear rejection reasons, confidence, and warnings. The backend now supports that direction; the frontend should increasingly prioritize operational evidence over animation.

## Action Items

- Show `DispatchRun` state transitions in the browser.
- Display hard-constraint pass/fail results before score.
- Show objective score and confidence as separate values.
- Add no-feasible candidate screen.
- Improve keyboard focus and semantic labels before final accessibility claims.

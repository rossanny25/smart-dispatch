# Nielsen UX/UI Heuristic Review

Target user: field-service dispatcher, operations supervisor, or technical reviewer using the simulator to understand a dispatch recommendation.

## Summary

The interface is adequate for the current MVP because it exposes orders, technicians, memory, simulated dispatch output, hard-rule evidence, canonical flow states, a local operational map, and visit calendar views. Its main UX gap is that the visible canonical flow is still partly driven by the compatibility UI rather than by persisted `/api/v1` run transitions.

## Heuristic Evaluation

| Heuristic | Current Evidence | Rating | Improvement |
| --- | --- | --- | --- |
| Visibility of system status | The UI shows dispatch stages, recommendation areas, and canonical state chips. | Good | Add persisted run revision and transition detail from `/api/v1`. |
| Match between system and real world | Uses dispatcher concepts: orders, technicians, zones, priority, recommendation, map, and visits. | Good | Keep SLA, hard constraints, and confidence labels visible in compact views. |
| User control and freedom | Dispatcher can simulate, confirm/override, reset the demo, and manage operational records. | Good | Add canonical decision flow and clearer undo/reset messaging. |
| Consistency and standards | Cards, lists, and status panels are visually consistent. | Good | Align all API errors to the same frontend presentation. |
| Error prevention | Backend validates canonical JSON and idempotency. | Medium | Surface validation before submit in the UI. |
| Recognition rather than recall | Seeded technicians/orders are visible. | Good | Keep selected order and environment visible during the full run. |
| Flexibility and efficiency | Single-page flow includes guided demo, map, calendar, and explicit no-feasible scenario. | Good | Add direct shortcuts for repeated evaluator scenarios. |
| Aesthetic and minimalist design | The dashboard is suitable for demonstration. | Medium | Reduce decorative elements if they compete with evidence review. |
| Help users recognize and recover from errors | API has typed errors and the UI shows a no-feasible explanation. | Medium | Improve form-level validation messages and retry actions. |
| Help and documentation | README and runbook explain startup. | Good | Add a short in-app "about this scenario" panel for evaluators. |

## Audience Fit

Dispatchers need fast comparison, clear rejection reasons, confidence, warnings, and visit context. The current frontend now surfaces those core signals; the next UX step is reducing duplication and tying each visible state back to the persisted canonical run.

## Action Items

- Connect visible canonical state chips to persisted `DispatchRun` transitions and revision.
- Keep objective score and confidence visually separate in compact layouts.
- Improve validation messages on admin/user forms before submit.
- Improve keyboard focus and semantic labels before final accessibility claims.

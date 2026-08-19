# Real Usage Session Log

Use this log as evidence for the final PDF. The screenshots and API/log excerpts below were captured from the Dockerized app running on port `8050`.

## Session Metadata

| Field | Value |
| --- | --- |
| Date | 2026-08-19 |
| Runtime | Docker Compose |
| URL | `http://127.0.0.1:8050` |
| Command | `docker compose up --build` |
| Purpose | Demonstrate the current Smart Dispatch IA UI with canonical states, hard-rule evidence, calendar, operational map, admin technician profiles, and no-feasible scenario. |

## Steps

1. Started the Dockerized application.

   ```bash
   docker compose up --build
   ```

2. Opened the frontend.

   ```text
   http://127.0.0.1:8050
   ```

   Evidence:

   - `docs/evidence/01-dashboard-full.png`

3. Verified the technicians API.

   ```bash
   curl http://127.0.0.1:8050/api/technicians
   ```

   Observed result: JSON array with seeded technicians such as Carlos Rodriguez, Sofia Torres, Juan Perez, Ana Gomez, and Diego Diaz.

   Evidence:

   - `docs/evidence/api-technicians.json`

4. Verified the app returned browser HTML.

   ```bash
   curl http://127.0.0.1:8050
   ```

   Observed result: HTML document for Smart Dispatch IA frontend.

5. Ran a real dispatch simulation from the browser.

   Action:

   - Selected the first seeded Work Order: Cafeteria Martinez Belgrano, Belgrano.
   - Clicked `Despachar`.

   Observed result:

   - The agent cycle completed.
   - The app recommended Juan Perez.
   - Recommendation evidence shown by the UI: score `98`, travel time `8` minutes, estimated duration `90` minutes.

   Evidence:

   - `docs/evidence/02-dispatch-result.png`

6. Approved the recommendation and recorded service completion.

   Action:

   - Clicked `Aprobar Recomendacion`.
   - The app opened the service-completion modal.
   - Kept the suggested real duration of `90` minutes.
   - Clicked `Completar y Aprender`.

   Observed result:

   - Work Order `order_001` changed to `completada`.
   - Juan Perez workload changed from `5 hs` to `6.5 hs`.

   Evidence:

   - `docs/evidence/03-recommendation-approved.png`
   - `docs/evidence/04-learning-completed.png`
   - `docs/evidence/api-orders-after-session.json`

7. Reviewed the operational map and calendar after the completed dispatch.

   Observed result:

   - The map showed seeded work orders and technicians by zone.
   - The calendar showed the completed service visit grouped by technician.

   Evidence:

   - `docs/evidence/05-map-operative.png`
   - `docs/evidence/06-calendar-visits.png`

8. Reviewed the admin technician profile screen.

   Observed result:

   - Admin screen exposed technician status, shift, workload, rating, GPS, contact, documents, and audit notes.

   Evidence:

   - `docs/evidence/07-admin-technicians.png`

9. Ran the explicit no-feasible-candidates scenario.

   Action:

   - Selected Work Order `order_003`: Data Center Puerto Madero.
   - Clicked `Despachar`.

   Observed result:

   - The canonical state reached `NO_FEASIBLE_CANDIDATES`.
   - The UI showed rejection evidence without forcing a recommendation.

   Evidence:

   - `docs/evidence/08-no-feasible-candidates.png`

10. Exported Docker logs for the real session.

   Evidence:

   - `docs/evidence/docker-session.log`

   Log excerpt:

   ```text
   Uvicorn running on http://0.0.0.0:8050
   GET / HTTP/1.1 200 OK
   GET /api/technicians HTTP/1.1 200 OK
   GET /api/orders HTTP/1.1 200 OK
   POST /api/dispatch/simulate HTTP/1.1 200 OK
   POST /api/dispatch/confirm HTTP/1.1 200 OK
   ```

## Evidence Checklist

- [x] Screenshot: application loaded on `8050`.
- [x] Screenshot: technicians section.
- [x] Screenshot: orders section.
- [x] Screenshot: dispatch simulation result.
- [x] Screenshot: recommendation/candidates/evidence.
- [x] Screenshot: approved recommendation / service completion modal.
- [x] Screenshot: order completed after learning step.
- [x] Screenshot: operational map.
- [x] Screenshot: calendar with visit history.
- [x] Screenshot: admin technician profile fields.
- [x] Screenshot: `NO_FEASIBLE_CANDIDATES` scenario.
- [x] API output excerpt: `/api/technicians`.
- [x] API output excerpt: `/api/orders` after completion.
- [x] Docker logs excerpt showing Uvicorn on `0.0.0.0:8050`.

## Notes For The Report

The session proves the application is executable and not only a PDF/specification. It also records the current post-polish UI state, including the new operational evidence views and explicit no-feasible path.

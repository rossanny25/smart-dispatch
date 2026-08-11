# Real Usage Session Log

Use this log as evidence for the final PDF. The screenshots and API/log excerpts below were captured from the Dockerized app running on port `8050`.

## Session Metadata

| Field | Value |
| --- | --- |
| Date | 2026-08-11 |
| Runtime | Docker Compose |
| URL | `http://127.0.0.1:8050` |
| Command | `docker compose up --build` |
| Purpose | Demonstrate that Smart Dispatch IA exists, runs, and serves frontend/API evidence. |

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

7. Exported Docker logs for the real session.

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
- [x] API output excerpt: `/api/technicians`.
- [x] API output excerpt: `/api/orders` after completion.
- [x] Docker logs excerpt showing Uvicorn on `0.0.0.0:8050`.

## Notes For The Report

The session proves the application is executable and not only a PDF/specification. For final grading, replace local-only evidence with a GitHub repository link and, if possible, a live deployed URL.

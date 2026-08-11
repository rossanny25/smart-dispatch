---
baseline_commit: NO_VCS
---

# Story 1.2: Capture and Validate a Work Order

Status: done

## Story

As a dispatcher,
I want to submit the incident and its available operational context,
so that the system can create a trustworthy Work Order for dispatch analysis.

## Requirements Traceability

- **Functional:** FR4.
- **Non-functional:** NFR3, NFR5, NFR7.
- **Journey:** UJ-1, limited to canonical Work Order capture; the browser form is completed in Story 1.9.
- **Architecture:** AD-1, AD-5, AD-7, AD-8, AD-12, AD-13, AD-15, AD-16, AD-18, AD-19, AD-22, AD-26, and AD-27.
- **Epic requirements registry:** AR1, AR5, AR7, AR8, AR12, AR13, AR15, AR16, AR18, AR20, AR24, AR25, AR27, and AR29.
- **Success metrics:** no direct SM is owned by this story. Story 1.11 verifies FR1-FR14 and the applicable NFRs; Story 4.4 completes release-level SM traceability.

## Acceptance Criteria

1. **Canonical valid creation**
   - **Given** valid `incident_text`, `address`, `zone`, and optional `context`
   - **When** the dispatcher sends `POST /api/v1/work-orders` with `Content-Type: application/json` and a nonblank `Idempotency-Key`
   - **Then** the API returns HTTP `201`
   - **And** the standard success envelope is `{"data": ..., "meta": {"schema_version": "v1", "request_id": "..."}}`
   - **And** `data` contains an opaque UUID `id`, `schema_version: "v1"`, the complete semantic `raw_input`, and a timezone-aware UTC `created_at` ending in `Z`
   - **And** the Work Order and its successful idempotency record are persisted atomically.

2. **Strict versioned capture contract**
   - **Given** a Work Order creation request
   - **When** the versioned Pydantic boundary validates it
   - **Then** unknown top-level fields are forbidden
   - **And** `incident_text`, `address`, and `zone` must be strings containing at least one non-whitespace character
   - **And** `context`, when supplied, is a JSON object whose values may contain JSON-compatible nested data and is preserved without semantic interpretation
   - **And** validation checks blank values without trimming or replacing the stored raw strings.

3. **Raw-input preservation and scope boundary**
   - **Given** a valid request is stored
   - **When** the persisted Work Order is retrieved by the creation result
   - **Then** `raw_input` preserves the submitted `incident_text`, `address`, `zone`, and `context` values semantically
   - **And** no category, priority, SLA, certification, service-duration, eligibility, score, confidence, warning, recommendation, State Transition, or Dispatch Run is derived or created
   - **And** later stories must copy the stored Work Order into an immutable run snapshot rather than calculate from a mutable operational row.

4. **Stable field-level validation**
   - **Given** a required field is missing, has the wrong type, is blank, or an unsupported top-level field is supplied
   - **When** request validation runs
   - **Then** the API returns HTTP `422` with error code `VALIDATION_FAILED`
   - **And** the standard error envelope contains `details` entries with stable `field`, `code`, and `message` values
   - **And** unsupported fields are identified by their request path
   - **And** neither a Work Order nor an idempotency row is written.

5. **Required route-scoped idempotency**
   - **Given** a mutating Work Order request has no `Idempotency-Key` or a whitespace-only key
   - **When** transport validation runs
   - **Then** the API returns `422 VALIDATION_FAILED` with a field detail for `idempotency_key`
   - **And** no application command executes.
   - **Given** the same route, nonblank key, and canonical request body are submitted again
   - **When** the first request already committed successfully
   - **Then** the API returns the original HTTP `201` success response, including the original Work Order identifier, timestamp, schema metadata, and response request identifier
   - **And** no duplicate Work Order is created.
   - **Given** the same route and key are reused with a different canonical request body
   - **When** idempotency validation runs
   - **Then** the API returns `409 CONFLICT`
   - **And** the original Work Order and retained response remain unchanged.

6. **Deterministic request hashing and concurrent retry safety**
   - **Given** a validated request
   - **When** its idempotency hash is calculated
   - **Then** SHA-256 is computed over UTF-8 canonical JSON from the validated contract using sorted keys, compact separators, JSON-mode values, and explicit default/null representation
   - **And** insignificant JSON member order or whitespace does not change the hash
   - **And** the database enforces one idempotency record per `(route, idempotency_key)`
   - **And** concurrent identical requests produce one Work Order and the same retained successful result
   - **And** a uniqueness race is resolved by reading the committed idempotency result rather than exposing an internal persistence error.

7. **Transport safety before command execution**
   - **Given** the request media type is not `application/json` with an optional charset
   - **When** it reaches the canonical API boundary
   - **Then** the API returns `415 UNSUPPORTED_MEDIA_TYPE`.
   - **Given** the body exceeds `1,048,576` bytes
   - **When** body bytes are received, regardless of an absent or dishonest `Content-Length`
   - **Then** the API returns `413 PAYLOAD_TOO_LARGE`.
   - **And** both errors use the standard envelope
   - **And** neither case parses the contract, invokes the application command, nor mutates persistence.

8. **One Unit of Work and fail-safe rollback**
   - **Given** Work Order creation or idempotency persistence fails
   - **When** the application command exits its Unit of Work
   - **Then** every write from that command is rolled back
   - **And** repositories never commit independently
   - **And** the HTTP adapter maps the typed failure once to `500 PERSISTENCE_ERROR`
   - **And** the response contains a safe generic message without SQL, stack trace, stored values, database paths, or user-home paths.

9. **Privacy-safe structured logging**
   - **Given** a canonical Work Order request is accepted or rejected
   - **When** application/API status logs are emitted
   - **Then** each operation log is valid structured JSON containing `request_id`, `operation`, and `status`
   - **And** applicable errors include only a stable error code
   - **And** logs never contain the raw address, exact coordinates, complete incident narrative, request body, or private reasoning
   - **And** HTTP validation handlers do not log `RequestValidationError.body`.

10. **Minimal Story 1.2 schema**
    - **Given** the production migration reaches head
    - **When** non-internal SQLite schema objects are listed
    - **Then** the only application tables added by this story are `work_orders` and `idempotency_records`
    - **And** `work_orders` stores the UUID identity, schema version, raw-input JSON, captured fields, optional-context JSON, and UTC creation timestamp
    - **And** `idempotency_records` stores route, key, request hash, retained HTTP status, retained success body, and UTC creation timestamp
    - **And** the database enforces primary/unique keys and non-null fields required for atomic creation
    - **And** no future Dispatch Run, Technician, candidate, Decision, outcome, Memory, KPI, replay, reset, configuration, or fixture table is introduced.

11. **OpenAPI authority and contract evidence**
    - **Given** FastAPI generates `/openapi.json`
    - **When** the Work Order operation and models are inspected
    - **Then** the canonical path, required header, request model, `201`, `409`, `413`, `415`, `422`, and `500` response models are declared
    - **And** success/error response examples validate against their referenced OpenAPI schemas
    - **And** contract tests validate actual valid, invalid, replay, conflict, oversized, unsupported-media, and persistence-failure responses against generated OpenAPI
    - **And** invalid transport and contract cases prove persistence remains unchanged.

12. **Brownfield and runtime preservation**
    - **Given** Story 1.2 is installed over the completed Story 1.1 runtime
    - **When** imports, migrations, legacy routes, static assets, and process-level tests run
    - **Then** `app.main` remains import-safe and composition-only
    - **And** startup still migrates before serving with backup/fail-closed behavior, one worker, loopback binding, and required SQLite PRAGMAs
    - **And** existing `/api/*` route shapes and module-level legacy state remain unchanged
    - **And** the SPA continues using the legacy API until Story 1.9/1.10
    - **And** `data/learning_store.json` remains byte-preserved.

## Tasks / Subtasks

- [x] 1. Establish failing canonical contract tests before implementation (AC: 1, 2, 4, 5, 7, 9, 11, 12)
  - [x] Extend `tests/asgi_client.py` to send arbitrary bytes, headers, media types, and chunked ASGI request messages while preserving existing callers.
  - [x] Add `tests/contract/test_work_orders_api.py` covering the exact success and error envelopes, UUID/UTC/schema fields, raw-input preservation, blank/missing/type/extra-field failures, required idempotency, replay, conflict, `413`, `415`, sanitized `500`, and OpenAPI validation.
  - [x] Add a persistence-state probe to prove every pre-command rejection leaves both Story 1.2 tables unchanged.
  - [x] Run the new contract tests and confirm they fail because the canonical route/contracts do not yet exist.

- [x] 2. Define versioned contracts and common envelopes without domain/framework leakage (AC: 1, 2, 4, 7, 11)
  - [x] Create strict schema-version-v1 API contracts under `app/contracts` using Pydantic 2.13.4 and `ConfigDict(extra="forbid")`; do not use the `pydantic.v1` compatibility namespace.
  - [x] Model `WorkOrderCreateV1`, the captured raw-input/result resources, `SuccessEnvelopeV1`, `ErrorEnvelopeV1`, `ErrorDetailV1`, and metadata.
  - [x] Preserve raw strings while rejecting whitespace-only required values; keep optional `context` as an explicitly allowed JSON object rather than accepting unknown request fields.
  - [x] Keep contracts free of persistence and application behavior; do not introduce derived Story 1.3 fields.

- [x] 3. Add only the Work Order and generic idempotency schema (AC: 6, 8, 10, 12)
  - [x] Add one ordered Alembic revision after `20260727_0001` using SQLAlchemy Core table definitions.
  - [x] Create plural `work_orders` and `idempotency_records` with the exact fields and constraints required by AC 10.
  - [x] Keep identifiers as UUID text, timestamps as UTC text ending in `Z`, raw/context/response JSON as canonical text, and `(route, idempotency_key)` unique.
  - [x] Update migration tests to assert the complete allowed `sqlite_schema` object set and prove upgrade against a fresh and existing Story 1.1 database.
  - [x] Rebase `tests/fixtures/migrations/success/20260728_0002_review_success.py` and `tests/fixtures/migrations/failure/20260728_0002_review_failure.py` so their `down_revision` is the new production Work Order revision, then prove each fixture chain has exactly one head.
  - [x] Prove startup backup-before-schema-change and fail-closed migration behavior remain green.

- [x] 4. Introduce the application ports, pure Work Order model, and Unit of Work (AC: 1, 3, 5, 6, 8)
  - [x] Add a pure domain `WorkOrder` representation and typed application results/errors without importing FastAPI, Pydantic, SQLAlchemy, or SQLite.
  - [x] Define Work Order repository, idempotency repository, Unit of Work, UUID factory, and UTC clock ports under `app/application`.
  - [x] Implement `CreateWorkOrder` as the only owner of creation/idempotency coordination.
  - [x] Make the command accept injected deterministic UUID/clock/request ID inputs for tests and execute all persistence through one Unit of Work.
  - [x] Keep Dispatch Run creation and all derived dispatch behavior out of the command.

- [x] 5. Implement SQLAlchemy Core repositories and atomic idempotency (AC: 1, 5, 6, 8, 10)
  - [x] Define reusable SQLAlchemy Core metadata/tables in the persistence adapter without introducing ORM models.
  - [x] Implement Work Order and idempotency repositories that operate on a caller-owned `Connection` and never commit.
  - [x] Implement a SQLite Unit of Work using `create_sqlite_engine()` and one transaction for Work Order plus retained idempotency response.
  - [x] Store/replay the original status and complete success body; recover a `(route, key)` uniqueness race by reading the winning committed record and applying normal hash comparison.
  - [x] Add real file-backed SQLite integration tests for creation, retrieval, exact raw/UTC persistence, identical replay, changed-body conflict, concurrent same-key requests, and injected rollback failure.

- [x] 6. Add the reusable canonical HTTP boundary and Work Order route (AC: 1, 4, 5, 7, 8, 9, 11)
  - [x] Add `/api/v1` router composition and `POST /work-orders` with explicit OpenAPI response models/statuses.
  - [x] Add shared request-ID, JSON media-type, streamed 1 MiB body-limit, idempotency-header, envelope, and error-mapping support suitable for later canonical commands.
  - [x] Map Pydantic/FastAPI validation locations to stable field paths without returning or logging raw request bodies.
  - [x] Generate privacy-safe structured operation logs and map typed conflicts/persistence errors once in the HTTP adapter.
  - [x] Inject the concrete Unit of Work, UUID, and UTC clock at composition; importing `app.main` must not connect to or create the database.

- [x] 7. Preserve legacy behavior and document the first canonical slice (AC: 3, 9, 12)
  - [x] Mount the canonical router beside, not inside, the temporary legacy adapter.
  - [x] Do not call `classify_order`, mutate legacy `orders`, change `/api/orders`, alter the SPA, or expose canonical Work Orders through legacy GET routes.
  - [x] Update `README.md` and `docs/development-guide.md` with the canonical endpoint, required headers, 1 MiB/JSON-only rules, SQLite tables, and the fact that analysis/UI migration remain later.
  - [x] Re-run legacy ASGI and both real-process route characterizations plus evidence checksum checks.

- [x] 8. Complete boundary-aligned verification (AC: 1-12)
  - [x] Add pure unit tests for canonical hashing, blank-value validation behavior, command idempotency decisions, and privacy-safe log construction.
  - [x] Run all new unit, integration, migration, contract, and process tests against temporary file-backed SQLite databases.
  - [x] Add dependency-free generated-OpenAPI contract tests: resolve the operation response `$ref`, compare the referenced component with the exact response model's `model_json_schema()`, and validate every actual success/error body with that referenced Pydantic model; do not add a JSON Schema dependency.
  - [x] Run `uv lock --check`, compile checks, the complete regression suite, and a manual frozen launch/HTTP creation check.
  - [x] Verify `data/learning_store.json` retains SHA-256 `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.

### Review Findings

- [x] [Review][Patch] Reject finite-syntax JSON numbers that overflow to non-finite Python values before they can become `null` and collapse distinct idempotency requests [app/api/v1/middleware.py:97]
- [x] [Review][Patch] Enforce the 1 MiB limit before copying each ASGI chunk into the body buffer [app/api/v1/middleware.py:83]
- [x] [Review][Patch] Offload the synchronous SQLite command so `BEGIN IMMEDIATE` cannot block the FastAPI event loop [app/api/v1/work_orders.py:42]
- [x] [Review][Patch] Translate excessive JSON nesting (`RecursionError`) into the stable `422 VALIDATION_FAILED` envelope [app/api/v1/middleware.py:97]
- [x] [Review][Patch] Restrict the canonical path boundary so `/api/v10/*` is not treated as `/api/v1` [app/api/v1/middleware.py:42]
- [x] [Review][Patch] Translate corrupted repository values and reject malformed retained idempotency responses before public replay [app/adapters/persistence/work_orders.py:63]
- [x] [Review][Patch] Add a real incremental migration test from Story 1.1 revision `20260727_0001` to the Story 1.2 head [tests/integration/test_migrations.py:6]
- [x] [Review][Patch] Exercise the `ConcurrentIdempotencyWrite` recovery branch for identical and changed hashes [tests/unit/test_create_work_order.py:1]
- [x] [Review][Patch] Exercise repository `get` reconstruction and its typed corruption failures [tests/integration/test_work_order_persistence.py:45]
- [x] [Review][Patch] Prove a valid JSON request of exactly 1,048,576 bytes is accepted [tests/contract/test_work_orders_api.py:249]

## Dev Notes

### Binding Contract Decisions

- Canonical route: `POST /api/v1/work-orders`.
- Success status: `201 Created`; an idempotent replay returns the retained original `201`.
- Required header: nonblank `Idempotency-Key`; missing/blank is `422 VALIDATION_FAILED`.
- Accepted request media type: `application/json` with an optional charset parameter.
- Maximum body size: exactly 1 MiB (`1,048,576` bytes), enforced from received bytes rather than trusting only `Content-Length`.
- Stable public errors:

  | HTTP | Code | Meaning |
  | --- | --- | --- |
  | 409 | `CONFLICT` | Same route/key with a different canonical request hash |
  | 413 | `PAYLOAD_TOO_LARGE` | Received body exceeds 1 MiB |
  | 415 | `UNSUPPORTED_MEDIA_TYPE` | Command request is not JSON |
  | 422 | `VALIDATION_FAILED` | Header or Pydantic contract failure |
  | 500 | `PERSISTENCE_ERROR` | Sanitized command persistence failure |

- Error details use `{field, code, message}`. Use dotted field paths such as `incident_text`, `context.some_field`, or `idempotency_key`; never include submitted values.
- Every canonical error uses the exact outer shape `{"schema_version":"v1","error":{"code":"...","message":"...","details":[]},"meta":{"schema_version":"v1","request_id":"..."}}`.
- Error `meta` is exactly `{ "schema_version": "v1", "request_id": "<current request UUID>" }`.
- Validation details are sorted by dotted `field` path and then by `code`; this order is part of the public contract.
- Transport, conflict, and persistence errors use `details: []`.

  | Case | HTTP | Top-level code | Top-level message | Detail field | Detail code | Detail message |
  | --- | ---: | --- | --- | --- | --- | --- |
  | Missing required body field | 422 | `VALIDATION_FAILED` | `Request validation failed.` | Request field name | `missing` | `Field is required.` |
  | Wrong field type | 422 | `VALIDATION_FAILED` | `Request validation failed.` | Request field name | `invalid_type` | `Field has an invalid type.` |
  | Blank required string | 422 | `VALIDATION_FAILED` | `Request validation failed.` | Request field name | `blank` | `Field must not be blank.` |
  | Extra body field | 422 | `VALIDATION_FAILED` | `Request validation failed.` | Dotted extra-field path | `extra_forbidden` | `Field is not supported.` |
  | Malformed JSON or invalid UTF-8 | 422 | `VALIDATION_FAILED` | `Request validation failed.` | `body` | `invalid_json` | `Request body must be valid UTF-8 JSON.` |
  | Missing `Idempotency-Key` | 422 | `VALIDATION_FAILED` | `Request validation failed.` | `idempotency_key` | `missing` | `Header is required.` |
  | Blank `Idempotency-Key` | 422 | `VALIDATION_FAILED` | `Request validation failed.` | `idempotency_key` | `blank` | `Header must not be blank.` |
  | Unsupported content type | 415 | `UNSUPPORTED_MEDIA_TYPE` | `Content-Type must be application/json.` | — | — | — |
  | Body larger than 1 MiB | 413 | `PAYLOAD_TOO_LARGE` | `Request body exceeds 1 MiB.` | — | — | — |
  | Same key, different request | 409 | `CONFLICT` | `Idempotency key was already used with a different request.` | — | — | — |
  | Persistence failure | 500 | `PERSISTENCE_ERROR` | `Work Order could not be created.` | — | — | — |

- Do not expose raw Pydantic error types, exception text, SQL, stack traces, or rejected request content.
- Canonical request hashing uses validated JSON-mode data with defaults represented explicitly, sorted keys, compact separators, UTF-8, and SHA-256. The idempotency scope string is the stable route template `/api/v1/work-orders`.
- `raw_input` means the complete semantic submitted object after type validation but before any trimming, classification, inference, or derivation. JSON whitespace/member order is not evidence and need not be retained.
- `context` is an optional JSON object preserved as supplied. It is an explicit extension container, not permission for unknown top-level fields and not a source of derived Story 1.3 values in this story.
- The retained idempotency body is the complete successful envelope so replay preserves the original resource, timestamp, schema metadata, and response request ID.

### Non-Destructive Invariants

- Do not modify `data/learning_store.json`, import legacy learnings, or create/reset default runtime data during module import.
- Do not remove or redesign `app/adapters/legacy/compatibility.py`, `server.py`, `/api/*`, or the current SPA.
- Do not create a Work Order, idempotency row, database file, or directory for rejected transport/contract requests.
- Do not let repository methods commit. The application Unit of Work owns the single transaction.
- Do not expose SQL, paths, stack traces, raw address, full incident text, exact GPS, or `RequestValidationError.body` in public errors or structured logs.
- Do not place FastAPI/Pydantic/SQLAlchemy imports inside pure domain or application-port modules.

### Scope Boundary

**In scope:** canonical Work Order capture contract; standard envelopes/errors; required route-scoped idempotency; deterministic hashing; minimal Work Order/idempotency migration; SQLAlchemy Core repositories and Unit of Work; POST route; privacy-safe logs; OpenAPI/contract/unit/integration evidence; documentation.

**Out of scope:** category/priority/SLA/certification/duration derivation; Capture-to-Analyze State Transition; Dispatch Run and snapshots; Technicians; eligibility; scoring; confidence; recommendation; browser migration/accessibility; Human Decision; outcome; Memory; KPIs; replay/reset; JSON migration; priority-5 correction; authentication/HTTPS implementation; multi-user/multi-process deployment.

### Architecture Compliance

- Dependencies point inward: `api/v1` calls the application command; the command depends on domain types and ports; SQLAlchemy implements ports.
- `app/main.py` remains composition only and import-safe. Route handlers perform transport work and error mapping, not business or transaction logic.
- The deterministic local Capture path remains the baseline; this story only persists schema-valid captured input and does not add an LLM/provider adapter.
- Only a future `DispatchOrchestrator` may advance run state. Work Order creation creates no run or stage execution.
- Use SQLAlchemy Core and Alembic; do not add an ORM model layer or a new dependency.
- Generated FastAPI OpenAPI from `app/contracts` owns the canonical API schema. Do not hand-maintain a divergent contract.
- Canonical middleware, dependencies, and exception translation apply only under `/api/v1`; non-`/api/v1` paths pass through unchanged, including request/media handling, response bodies, status codes, and exception behavior.

### Story 1.1 Intelligence

- Reuse `create_sqlite_engine()` so every connection retains foreign keys, WAL, 5000 ms timeout, capability validation, and URL-safe paths.
- Add one migration after `20260727_0001`; existing-database startup automatically creates and verifies a backup, serializes migration preparation, and restores/cleans on failure.
- Use this exact Story 1.2 schema:

  | Table | Column | SQLite type | Nullability / key |
  | --- | --- | --- | --- |
  | `work_orders` | `id` | `TEXT` | `PRIMARY KEY NOT NULL` |
  | `work_orders` | `schema_version` | `TEXT` | `NOT NULL` |
  | `work_orders` | `raw_input_json` | `TEXT` | `NOT NULL` |
  | `work_orders` | `incident_text` | `TEXT` | `NOT NULL` |
  | `work_orders` | `address` | `TEXT` | `NOT NULL` |
  | `work_orders` | `zone` | `TEXT` | `NOT NULL` |
  | `work_orders` | `context_json` | `TEXT` | `NOT NULL`; absent or explicit-null context is canonical JSON `null` |
  | `work_orders` | `created_at` | `TEXT` | `NOT NULL`; UTC RFC 3339 ending in `Z` |
  | `idempotency_records` | `route` | `TEXT` | `NOT NULL`, composite primary key part 1 |
  | `idempotency_records` | `idempotency_key` | `TEXT` | `NOT NULL`, composite primary key part 2 |
  | `idempotency_records` | `request_hash` | `TEXT` | `NOT NULL`; lowercase SHA-256 hex |
  | `idempotency_records` | `response_status` | `INTEGER` | `NOT NULL` |
  | `idempotency_records` | `response_body_json` | `TEXT` | `NOT NULL`; canonical complete response envelope |
  | `idempotency_records` | `created_at` | `TEXT` | `NOT NULL`; UTC RFC 3339 ending in `Z` |
- Preserve Story 1.1's import-safety, loopback/one-worker launch, same-origin/no-wildcard-CORS behavior, runtime-artifact ignores, and real process tests.
- Story 1.1 review found missing real migrations, incomplete schema-object assertions, pooled-connection assumptions, weak process readiness, and evidence mutation. Story 1.2 tests must preserve the corrected patterns rather than regress to file-existence or mocked-only assertions.
- The current `tests/asgi_client.py` cannot send raw/non-JSON/oversized/chunked requests or arbitrary headers; extend it compatibly instead of creating another ad hoc ASGI client.
- `docs/source-tree-analysis.md` and parts of `docs/architecture.md` describe the pre-Story-1.1 state. Treat the implementation, Architecture Spine, project context, and updated development guide as current authority.

### File Structure Requirements

Expected new files, subject to bounded naming refinements:

```text
app/
  api/
    __init__.py
    v1/
      __init__.py
      errors.py
      middleware.py
      router.py
      work_orders.py
  application/
    __init__.py
    commands/
      __init__.py
      create_work_order.py
    ports/
      __init__.py
      persistence.py
  contracts/
    __init__.py
    common.py
    work_orders.py
  domain/
    __init__.py
    work_orders/
      __init__.py
      models.py
  adapters/
    persistence/
      schema.py
      unit_of_work.py
      work_orders.py
  migrations/
    versions/
      20260728_0002_work_orders.py
tests/
  contract/
    test_work_orders_api.py
  integration/
    test_work_order_persistence.py
  unit/
    test_create_work_order.py
    test_work_order_contracts.py
```

Expected updates:

- `app/main.py` — compose the canonical router with dependency injection and no import-time I/O.
- `tests/asgi_client.py` — support arbitrary transport cases while preserving existing tests.
- `tests/integration/test_migrations.py` — update the complete production schema allowlist.
- `tests/fixtures/migrations/success/20260728_0002_review_success.py` and `tests/fixtures/migrations/failure/20260728_0002_review_failure.py` — keep the review migrations on one linear head after the new production revision.
- `README.md` and `docs/development-guide.md` — document the first canonical operation.

Do not update `frontend/*` or move legacy behavior in this story.

### Testing Requirements

- Follow red-green-refactor for each task. The first canonical endpoint tests must fail before route implementation.
- Unit: raw-string blank validation without normalization; canonical hashing; injected clock/UUID; command idempotency branches; privacy-safe log event construction.
- Integration: real temporary file-backed SQLite; fresh/existing migration; exact schema objects; UoW rollback; Work Order/idempotency atomicity; UUID/UTC/raw JSON; uniqueness race; same/different hash behavior.
- Contract: validate actual bodies against the operation's generated OpenAPI schemas for `201`, `409`, `413`, `415`, `422`, and `500`; verify forbidden fields and stable field paths.
- Regression: full Story 1.1 suite, legacy routes, process launchers, import safety, CORS, PRAGMAs, backup/restore, and evidence checksum remain green.
- Browser tests are not required because the SPA remains on legacy routes; Story 1.9 owns form migration and accessibility evidence.
- Use deterministic fixture UUIDs, timestamps, request IDs, and temporary DB paths. Tests must not depend on external services or user-global state.

### Latest Technical Information

- Keep the pinned project versions. Do not upgrade opportunistically; exact reproducibility is binding.
- FastAPI generates request JSON Schema/OpenAPI from typed Pydantic body models and permits overriding `RequestValidationError` handling for the standard envelope. Do not return or log the exception body. [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/) and [FastAPI error handling](https://fastapi.tiangolo.com/tutorial/handling-errors/).
- Pydantic v2 uses `model_config = ConfigDict(extra="forbid")` for strict unknown-field rejection. [Pydantic configuration](https://docs.pydantic.dev/latest/api/config/).
- SQLAlchemy Core `Engine.begin()` provides a transaction context that commits on success and rolls back on exception; repositories must share that caller-owned connection. [SQLAlchemy Core transactions](https://docs.sqlalchemy.org/en/20/tutorial/dbapi_transactions.html).
- SQLite transaction/uniqueness behavior remains the persistence authority; resolve uniqueness races by rereading the committed idempotency row rather than adding retry-side partial commits. [SQLite transactions](https://www.sqlite.org/lang_transaction.html).

### Project Structure Notes

- No Git metadata is available; when development begins, set `baseline_commit: NO_VCS`.
- The completed Story 1.1 suite has 34 passing tests. Story 1.2 must increase coverage without weakening or deleting those tests.
- No separate UX specification exists. This is non-blocking because the browser is intentionally unchanged.
- No new dependencies are expected. If implementation discovers a dependency beyond the pinned lock, halt for approval rather than changing `pyproject.toml`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.2]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/prd.md` — UJ-1, FR4, NFR3, NFR5, NFR7, Constraints, Non-Goals]
- [Source: `_bmad-output/planning-artifacts/prds/prd-smart-dispatch-ia-spec-v2-2026-07-27/addendum.md` — Brownfield Baseline, JSON Contracts, SQLite]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ARCHITECTURE-SPINE.md` — AD-1, AD-5, AD-7, AD-8, AD-12, AD-13, AD-15, AD-16, AD-18, AD-19, AD-22, AD-26, AD-27, Consistency Conventions, Structural Seed]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-smart-dispatch-ia-spec-v2-2026-07-27/ACADEMIC-ARCHITECTURE.md` — Components, Transactions, Data Model, API Surface, Testing, Brownfield Migration]
- [Source: `_bmad-output/project-context.md` — Language, Framework, Testing, Quality, Workflow, Critical Rules]
- [Source: `_bmad-output/implementation-artifacts/1-1-launch-the-local-simulator-safely-and-reproducibly.md` — Story 1.1 Completion, Review Findings, File List]
- [Source: `_bmad-output/implementation-artifacts/deferred-work.md` — Brownfield issues deferred from Story 1.1]
- [Source: `docs/index.md`, `docs/api-contracts.md`, `docs/data-models.md`, `docs/development-guide.md` — Brownfield history and current launch contract]
- [Source: `app/main.py`, `app/adapters/persistence/database.py`, `app/migrations/runtime.py`, `tests/asgi_client.py`, `tests/integration/test_migrations.py` — current implementation seams]

## Definition of Done

- [x] All tasks and subtasks are complete with tests passing.
- [x] `POST /api/v1/work-orders` implements all twelve acceptance criteria.
- [x] Production schema contains exactly the Story 1.1 baseline plus `work_orders` and `idempotency_records`.
- [x] Invalid, oversized, unsupported-media, duplicate, conflict, concurrent, and persistence-failure cases cannot leave partial state.
- [x] Every actual canonical response validates against generated OpenAPI.
- [x] Existing legacy routes, process launch, SQLite safety, static assets, and evidence checksum remain unchanged.
- [x] The full regression suite, lock check, compile check, and manual frozen launch verification pass.
- [x] Dev Agent Record lists exact commands/results and every created or modified file.

## Dev Agent Record

### Agent Model Used

GPT-5.6

### Implementation Plan

- Establish strict contract tests and transport probes first.
- Add the minimal schema and application/persistence ports.
- Implement atomic creation/idempotency through one Unit of Work.
- Compose the canonical API and centralized envelopes/errors/logging.
- Finish with OpenAPI, real-SQLite, process, documentation, and full regression evidence.

### Debug Log References

- Initial `pytest -q tests/contract/test_work_orders_api.py` red phase — 11 expected errors because the canonical composition/route did not exist.
- Final `.venv/bin/pytest -q` outside the network sandbox — 62 tests passed, including both real-process launchers.
- `.venv/bin/python -m compileall -q app tests` — passed.
- `uv 0.11.16 lock --check` with an isolated temporary cache — 28 packages resolved; lock is current.
- Manual frozen `uv run --frozen smart-dispatch` — server started on `127.0.0.1:8000`; canonical POST returned HTTP `201`; clean shutdown passed.
- `data/learning_store.json` SHA-256 remained `2678ee1b9d4cb9dc921078f8784a53960d2a2132143c3f385fc58172566578a2`.
- Code-review red phase — 8 focused failures reproduced implementation defects; migration, race-recovery, retrieval, and exact-boundary coverage tests already passed once added.
- Code-review green phase — 41 focused tests and 74 full-suite tests passed after all 10 review patches.
- Post-review compile, `uv lock --check`, and evidence checksum checks passed.

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created.
- Implemented the strict versioned Work Order capture contract, success/error envelopes, deterministic validation mapping, JSON-only/1 MiB transport guard, request IDs, and privacy-safe structured logs.
- Added pure domain/application boundaries, canonical request hashing, required route-scoped idempotency, retained byte-stable replay, conflict handling, and typed persistence failure mapping.
- Added the exact two-table Alembic schema plus SQLAlchemy Core repositories and one SQLite Unit of Work; rollback and concurrent identical request behavior are verified against real file-backed databases.
- Preserved the legacy `/api/*` surface and SPA behavior while mounting `POST /api/v1/work-orders` beside it.
- Added generated-OpenAPI contract evidence for actual `201`, `409`, `413`, `415`, `422`, and `500` bodies and validated embedded examples without adding dependencies.
- Completed all twelve acceptance criteria with 62 passing tests, synchronized lock, clean compilation, manual frozen launch/HTTP verification, and unchanged evidence checksum.
- Code review resolved all 10 actionable findings: finite-number preservation, pre-copy body limiting, event-loop offload, deep-JSON handling, exact v1 path scoping, typed corruption handling, retained-response validation, Story 1.1 incremental migration evidence, uniqueness-race evidence, repository retrieval coverage, and the inclusive 1 MiB boundary.
- Final post-review regression contains 74 passing tests with no unresolved high or medium findings.

### File List

- `README.md`
- `_bmad-output/implementation-artifacts/1-2-capture-and-validate-a-work-order.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `app/adapters/persistence/schema.py`
- `app/adapters/persistence/unit_of_work.py`
- `app/adapters/persistence/work_orders.py`
- `app/api/__init__.py`
- `app/api/v1/__init__.py`
- `app/api/v1/errors.py`
- `app/api/v1/middleware.py`
- `app/api/v1/router.py`
- `app/api/v1/work_orders.py`
- `app/application/__init__.py`
- `app/application/commands/__init__.py`
- `app/application/commands/create_work_order.py`
- `app/application/ports/__init__.py`
- `app/application/ports/persistence.py`
- `app/contracts/__init__.py`
- `app/contracts/common.py`
- `app/contracts/work_orders.py`
- `app/domain/__init__.py`
- `app/domain/work_orders/__init__.py`
- `app/domain/work_orders/models.py`
- `app/main.py`
- `app/migrations/versions/20260728_0002_work_orders.py`
- `docs/development-guide.md`
- `tests/asgi_client.py`
- `tests/contract/test_work_orders_api.py`
- `tests/fixtures/migrations/failure/20260728_0002_review_failure.py`
- `tests/fixtures/migrations/success/20260728_0002_review_success.py`
- `tests/integration/test_migrations.py`
- `tests/integration/test_work_order_persistence.py`
- `tests/unit/test_create_work_order.py`
- `tests/unit/test_work_order_contracts.py`

### Change Log

- 2026-07-28: Created the implementation-ready Story 1.2 context for canonical Work Order capture and validation.
- 2026-07-28: Implemented and verified the complete canonical Work Order capture slice; moved Story 1.2 to review.
- 2026-07-28: Applied all 10 code-review patches, expanded verification from 62 to 74 tests, and marked Story 1.2 done.

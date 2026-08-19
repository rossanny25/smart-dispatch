---
title: 'User Role Administration And SQLite Login'
type: 'feature'
created: '2026-08-18'
status: 'done'
review_loop_iteration: 0
baseline_commit: 'a4b8506'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/ai-project-status.md'
  - '{project-root}/_bmad-output/project-context.md'
---

<frozen-after-approval reason="human-owned intent -- do not modify unless human renegotiates">

## Intent

**Problem:** Smart Dispatch IA currently protects access with one hardcoded-style
single-user credential. The product now needs a professional administration
base: an initial admin user, persisted accounts, roles, and a visible path to
manage mostly technician users without adding paid infrastructure.

**Approach:** Add SQLite-backed users and roles through Alembic, seed the
initial admin account with username `admin` and password `smart2026AI`, update
login to authenticate against the database, and add a small admin UI/API for
listing, creating, editing, and assigning roles. Keep the existing dispatcher
demo working and keep the data store free on Render by staying on SQLite.

## Boundaries & Constraints

**Always:** Preserve FastAPI + vanilla frontend + SQLite. Keep one deployed
process and one SQLite database path. Store password hashes, never plain text,
using Python standard-library hashing with per-user salts. Keep session cookies
signed and HTTP-only. Restrict user-management routes to `admin` role. Keep
technician accounts representable by role even if full technician fichas are
deferred. Preserve existing demo login compatibility only if it is needed for
smooth migration.

**Ask First:** Adding external email, paid database services, OAuth, third-party
maps, a frontend framework, destructive migration of existing runtime data, or
changing the published hosting target.

**Never:** Do not store plaintext passwords in SQLite. Do not expose password
hashes through API/UI. Do not add public self-registration. Do not mix this
slice with visit calendars, map providers, technician fichas, or JSON-to-DB
dispatch-data migration.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ADMIN_LOGIN | `admin` / `smart2026AI` after migrations | Session cookie is issued and `/auth/session` returns role `admin` | Invalid credentials return existing login error |
| USER_LIST | Authenticated admin calls users API | Active users are returned with id, username, display name, role, active state, and timestamps | Non-admin receives `403` |
| CREATE_TECH | Admin creates `tecnico` user | User is persisted with hashed password and role `tecnico` | Duplicate username returns `409`; invalid role returns `422` |
| EDIT_USER | Admin edits display name, role, active state, or password | Updated fields persist without exposing password material | Cannot deactivate or demote the last active admin |
| FORGOT_PASSWORD | User clicks forgot-password action | UI shows a clear operational message to contact the administrator | No token/email is generated in this slice |

</frozen-after-approval>

## Code Map

- `app/auth.py` -- current session-cookie and credential helper; update to verify users from SQLite and expose current user claims.
- `app/main.py` -- composition root and route registration; inject database path into auth/admin routes.
- `app/migrations/versions/` -- add users/roles table migration after `20260728_0007`.
- `app/adapters/persistence/schema.py` -- declare SQLAlchemy table metadata for application users.
- `frontend/login.html` -- add forgot-password control and use admin credential copy.
- `frontend/index.html` -- add compact administration section reachable inside the current UI.
- `frontend/main.js` -- load session role, guard admin UI, call user-management endpoints.
- `frontend/index.css` -- add focused styles for admin user controls without redesigning the app.
- `tests/integration/test_auth.py` -- extend login/session tests for SQLite-backed admin.
- `tests/integration/test_user_admin.py` -- cover list/create/edit/role authorization and last-admin protection.

## Tasks & Acceptance

**Execution:**
- [x] `app/migrations/versions/20260818_0008_users.py` -- create `app_users` with username uniqueness, role checks, password hash/salt, active flag, timestamps.
- [x] `app/adapters/persistence/schema.py` -- mirror `app_users` table metadata.
- [x] `app/auth.py` -- add password hashing, admin bootstrap, DB-backed credential validation, and role-aware sessions.
- [x] `app/main.py` -- wire auth to database path and add protected user-admin JSON endpoints.
- [x] `frontend/login.html` -- expose admin login hint and forgot-password action.
- [x] `frontend/index.html`, `frontend/main.js`, `frontend/index.css` -- add user administration UI for admins.
- [x] `tests/integration/test_auth.py`, `tests/integration/test_user_admin.py` -- add regression coverage for auth and admin flows.
- [x] `README.md`, `AGENTS.md`, `docs/ai-project-status.md`, `docs/runbook.md` -- update operational handoff and next steps.

**Acceptance Criteria:**
- Given a fresh SQLite database, when migrations/startup run, then one active admin account exists with username `admin` and password `smart2026AI`.
- Given valid admin credentials, when logging in, then the app issues a signed session cookie containing role-aware claims and the dashboard loads.
- Given a technician user, when attempting user-admin APIs, then the response is `403`.
- Given an admin, when creating or editing a user, then the user is persisted in SQLite and visible in the admin UI.
- Given the only active admin, when attempting to deactivate or demote that account, then the API rejects the operation.
- Given a user clicks forgot password, when no email integration is configured, then the UI gives an operational recovery message without pretending to send email.
- Given an admin mutation is retried with the same idempotency key and payload, then the stored response is replayed instead of duplicating data.
- Given an existing session belongs to a user whose role or active state changed, then the next protected request revalidates against SQLite.

## Design Notes

Use one `app_users` table rather than a full RBAC schema for this slice:
`role IN ('admin','tecnico','dispatcher')` is enough to support admin and mostly
technician users while keeping the migration small. Password storage can use
`hashlib.pbkdf2_hmac` with a random salt and iteration count encoded into the
stored hash string. Session tokens should remain stateless but include only
minimal claims: user id, username, role, and expiry, signed with the existing
session secret.

## Verification

**Commands:**
- `/private/tmp/smart-dispatch-py312-test/bin/python -m pytest tests/integration/test_auth.py tests/integration/test_user_admin.py tests/unit/test_runtime.py` -- expected: all selected tests pass.
- `node --check frontend/main.js` -- expected: syntax check succeeds.
- `docker build -t smart-dispatch-ia:user-admin .` -- expected: image builds.

**Performed:**
- `.venv/bin/python -m pytest tests/integration/test_auth.py tests/integration/test_user_admin.py tests/integration/test_migrations.py tests/unit/test_runtime.py tests/integration/test_legacy_compatibility.py tests/integration/test_legacy_eligibility_regression.py tests/unit/test_repository_hygiene.py tests/unit/test_project_metadata.py` -- passed: `65 passed`.
- `node --check frontend/main.js` -- passed.
- `.venv/bin/python -m py_compile app/auth.py app/main.py app/startup.py app/migrations/versions/20260818_0008_users.py` -- passed.
- `docker build -t smart-dispatch-ia:user-admin .` -- passed.
- Docker HTTP smoke on `8050` -- passed: login page `200`, admin API without session `401`, admin login `200`, session role `admin`, users list `200`, technician creation `201`.
- `.venv/bin/python -m pytest tests/integration/test_auth.py tests/integration/test_user_admin.py tests/integration/test_migrations.py tests/integration/test_startup_safety.py tests/unit/test_runtime.py -k 'not test_startup_lock_serializes_independent_processes'` -- passed: `63 passed, 1 deselected`.
- `test_startup_lock_serializes_independent_processes` remains an existing timing-sensitive multiprocessing test; it measured just under its `0.4s` threshold in the combined run.
- Docker Compose smoke on `8050` -- passed: `/healthz` `200`, `/login` `200`, unauthenticated admin API `401`, admin login `200`, `/auth/session` role `admin`, user list `200`, technician create `201`, repeated idempotency key replayed the same user response.

## Suggested Review Order

**Auth Model**

- SQLite-backed auth, hashing, sessions, and hardening live together.
  [`auth.py:23`](../../app/auth.py#L23)

- Session cookies can be secure in hosted HTTPS environments.
  [`auth.py:91`](../../app/auth.py#L91)

- Active sessions are revalidated against the user store.
  [`auth.py:227`](../../app/auth.py#L227)

- Login parsing now enforces a small body limit.
  [`auth.py:278`](../../app/auth.py#L278)

- Idempotency records replay admin mutations safely.
  [`auth.py:305`](../../app/auth.py#L305)

**API Surface**

- Login middleware passes the SQLite auth store into session checks.
  [`main.py:164`](../../app/main.py#L164)

- Login route authenticates against persisted users.
  [`main.py:187`](../../app/main.py#L187)

- Admin create/update endpoints enforce role and idempotency.
  [`main.py:242`](../../app/main.py#L242)

**Persistence**

- Alembic adds the application-user table after existing dispatch schema.
  [`20260818_0008_users.py:20`](../../app/migrations/versions/20260818_0008_users.py#L20)

- Schema metadata mirrors constraints for usernames, roles, and hashes.
  [`schema.py:60`](../../app/adapters/persistence/schema.py#L60)

**Frontend**

- Admin UI loads only when the session role is admin.
  [`main.js:165`](../../frontend/main.js#L165)

- User list/edit flow keeps username immutable on edit.
  [`main.js:203`](../../frontend/main.js#L203)

- Admin mutations send canonical idempotency keys.
  [`main.js:139`](../../frontend/main.js#L139)

**Deployment And Tests**

- Render generates a session secret and enables secure cookies.
  [`render.yaml:15`](../../render.yaml#L15)

- Integration tests cover admin CRUD, role denial, and idempotency replay.
  [`test_user_admin.py:56`](../../tests/integration/test_user_admin.py#L56)

- Auth tests cover corrupt stores, oversized login, and malformed hashes.
  [`test_auth.py:40`](../../tests/integration/test_auth.py#L40)

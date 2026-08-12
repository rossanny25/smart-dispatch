# Spec - Single-User Login

Date: 2026-08-11
Status: Implemented
Baseline commit: `0f72924`

## Intent

Protect the Smart Dispatch IA browser experience and API routes with a simple
single-user login suitable for the current demo deployment.

## User Credential

- Username: `tecnico-fisca`
- Password: `smart2026AI`

The credential is configurable through environment variables so hosted or shared
environments can rotate it without code changes.

## Scope

Implemented:

- Public `/login` page.
- `POST /auth/login` supporting JSON and URL-encoded form bodies.
- Signed HTTP-only session cookie named `smart_dispatch_session`.
- `POST /auth/logout` to clear the session.
- Middleware protection for browser and API routes.
- Public access for `/healthz`, `/login`, `/auth/login`, and `/index.css`.
- README, runbook, agent handoff, status, backlog, and security log updates.
- Integration tests for redirect, API `401`, invalid login, valid login, and logout.

Out of scope:

- Registration.
- Multi-user roles.
- Password reset.
- Admin panel.
- CSRF-hardening for multi-user production use.
- External identity provider integration.

## Configuration

| Variable | Purpose |
| --- | --- |
| `SMART_DISPATCH_LOGIN_USER` | Overrides default username. |
| `SMART_DISPATCH_LOGIN_PASSWORD` | Overrides default password. |
| `SMART_DISPATCH_SESSION_SECRET` | Overrides local fallback secret used to sign session cookies. |

## Acceptance Evidence

Focused verification passed:

```text
tests/integration/test_auth.py
tests/unit/test_runtime.py
tests/integration/test_legacy_compatibility.py
tests/integration/test_legacy_eligibility_regression.py
tests/unit/test_repository_hygiene.py
tests/unit/test_project_metadata.py
29 passed
```

## Next Recommended Work

Keep `NO_FEASIBLE_CANDIDATES` as the next product slice. Authentication should
only expand when the product needs separate users, roles, audit trails, or an
admin workflow.

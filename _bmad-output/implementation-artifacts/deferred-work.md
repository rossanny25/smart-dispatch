# Deferred Work

## Deferred from: code review of 1-1-launch-the-local-simulator-safely-and-reproducibly (2026-07-27)

- Make legacy confirmation persistence atomic and roll back the order/technician in-memory mutations if the learning-store write fails. Pre-existing brownfield behavior; address during the canonical compatibility cutover.
- Validate malformed legacy simulation environments and unexpected learning-store structures so they do not raise HTTP 500 or silently collapse evidence. Pre-existing brownfield behavior; address when Story 1.10 replaces the compatibility implementation with canonical use cases.
- Replace the legacy order ID based on the final four epoch-second digits with collision-safe identifiers. Pre-existing brownfield behavior; address with the canonical Work Order model.

## Deferred from: user-requested administration expansion (2026-08-18)

- source_spec: none
  summary: Build editable technician profile pages with schedules, operational details, and availability.
  evidence: Split from the current request because technician fichas are a separate shippable workflow after user/role authorization exists.
- source_spec: none
  summary: Add technician visit calendars and visit scheduling views.
  evidence: Split from the current request because calendar workflows require separate data models and UI states beyond account administration.
- source_spec: none
  summary: Add map visualization for visits, addresses, and technician zones without paid provider dependency.
  evidence: Split from the current request because maps need a separate provider/asset decision and should follow visit/calendar modeling.
- source_spec: none
  summary: Migrate seeded demo technicians/orders from JSON bootstrap into SQLite-backed operational records.
  evidence: Split from the current request because it changes dispatch data ownership and should not be mixed with login/account administration.
- source_spec: none
  summary: Implement a complete forgot-password recovery flow.
  evidence: Split from the current request because real recovery requires email/token delivery decisions; this slice will expose a safe placeholder action only.

## Deferred from: technician operations quality pass (2026-08-18)

- source_spec: none
  summary: Add technician visit calendars with day/week views and assignment history.
  evidence: Split from the current request because calendars are independently shippable after editable technician profiles and schedules exist.
- source_spec: none
  summary: Add no-cost map visualization for technician zones and planned visits.
  evidence: Split from the current request because map rendering requires separate coordinate, layout, and no-provider decisions.
- source_spec: none
  summary: Migrate work orders and dispatch execution fully from legacy seed routes to canonical SQLite operational records.
  evidence: Split from the current request because technician CRUD can become real first while preserving the existing dispatch flow.

- source_spec: `_bmad-output/implementation-artifacts/spec-technician-operations-sqlite-clarity.md`
  summary: Make legacy confirmation atomic across order state, technician workload, and learning writes.
  evidence: Review confirmed `confirm_dispatch` still spans compatibility memory, SQLite workload, and learning-file writes; this belongs with canonical dispatch/outcome migration.
- source_spec: `_bmad-output/implementation-artifacts/spec-technician-operations-sqlite-clarity.md`
  summary: Replace process-global compatibility database configuration with app-scoped dependency injection.
  evidence: Review confirmed `configure_database_path` is shared across app instances; acceptable for current single-process runtime but brittle for future embedded tests/runtime reuse.

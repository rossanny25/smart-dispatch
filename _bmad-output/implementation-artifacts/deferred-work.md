# Deferred Work

## Deferred from: code review of 1-1-launch-the-local-simulator-safely-and-reproducibly (2026-07-27)

- Make legacy confirmation persistence atomic and roll back the order/technician in-memory mutations if the learning-store write fails. Pre-existing brownfield behavior; address during the canonical compatibility cutover.
- Validate malformed legacy simulation environments and unexpected learning-store structures so they do not raise HTTP 500 or silently collapse evidence. Pre-existing brownfield behavior; address when Story 1.10 replaces the compatibility implementation with canonical use cases.
- Replace the legacy order ID based on the final four epoch-second digits with collision-safe identifiers. Pre-existing brownfield behavior; address with the canonical Work Order model.

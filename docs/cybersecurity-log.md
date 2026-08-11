# Cybersecurity Log

This log documents security risks and mitigations for the current MVP.

| Risk | Impact | Current Mitigation | Remaining Limitation |
| --- | --- | --- | --- |
| Accidental public exposure | Local prototype could be accessed by unintended users if bound to all interfaces. | Local default binds to `127.0.0.1`; Docker uses `0.0.0.0` only inside an explicit container demo on port `8050`. | Production deployment needs authentication, HTTPS, and network policy. |
| Missing authentication | Any local user with access to the port can call endpoints. | Scope is local classroom demo; no production claims are made. | Must add auth before real operational use. |
| Sensitive location/address data | Addresses and GPS could expose customer/technician privacy. | Structured logs must not expose raw addresses or exact GPS; long-term semantic memory should use zone-level data. | Current legacy UI/data still contains demo addresses and approximate coordinates. |
| Oversized or malformed JSON | Large payloads or bad content could degrade service or cause unsafe errors. | Canonical middleware enforces JSON content handling, 1 MiB limit, and typed errors for `/api/v1`. | Legacy compatibility routes are temporary migration surface. |
| Unsafe exception disclosure | Stack traces could reveal internals. | API maps known failures to stable safe envelopes. | Need full production error policy before deployment. |
| Dependency drift | Unpinned packages can make demo unreproducible or vulnerable. | `pyproject.toml`, `uv.lock`, and Docker pinned runtime dependencies. | Need routine vulnerability scanning for public hosting. |
| Database corruption/loss during migrations | Failed migration could lose evidence. | Startup runs Alembic fail-closed and creates verified SQLite backups for existing databases. | Backup retention/export policy remains MVP-level, not production-grade. |
| External frontend assets | CDN fonts/icons can fail or leak request metadata. | Acceptable for prototype demo. | Vendoring assets is recommended for fully offline/public evidence. |

## Security Posture

Smart Dispatch IA is a scoped MVP. It should not be presented as enterprise production-ready. The correct claim is that security risks were identified, mitigated where reasonable for the current scope, and documented as limitations for future work.

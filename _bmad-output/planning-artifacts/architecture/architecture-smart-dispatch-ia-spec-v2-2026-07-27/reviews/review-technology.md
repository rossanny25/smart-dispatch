# Technology Reality Check

**Reviewed:** `ARCHITECTURE-SPINE.md`  
**Date:** 2026-07-27  
**Lens:** currency, stability, compatibility, and brownfield/evaluator provisionability  
**Verdict:** **CHANGES REQUIRED before implementation readiness**

The proposed technology family is appropriate for a local academic MVP and the pinned application-library versions are real, stable releases compatible with Python 3.12. The architecture is not yet executable or reproducible from the current repository, however: the declared interpreter and package manager are absent, dependency/lock files do not exist, the HTTP runtime is underspecified, and the required browser test capability has no selected tool.

## Findings

### [P1] The evaluator cannot currently provision or run the committed stack

**Evidence**

- The repository has no `pyproject.toml`, `uv.lock`, `.python-version`, requirements file, bootstrap script, or installation instructions for the new stack.
- The current machine exposes Python `3.9.6`, while the architecture pins `3.12.10`.
- `uv` is not installed.
- The currently documented launch path remains `python3 server.py` and explicitly says there are no third-party dependencies.
- FastAPI 0.138.2 and Alembic 1.18.5 both require Python 3.10 or newer, so the available 3.9.6 interpreter cannot host the committed stack. See [FastAPI 0.138.2 metadata](https://pypi.org/project/fastapi/0.138.2/) and [Alembic metadata](https://pypi.org/project/alembic/).

**Impact**

An evaluator cloning the current repository can run only the legacy standard-library server. They cannot reproduce the architecture's FastAPI application or its tests from repository-owned artifacts.

**Required resolution**

Before implementation-readiness approval, add:

1. `.python-version` (or an explicit `requires-python`) defining the supported interpreter policy;
2. `pyproject.toml` with runtime and development dependency groups;
3. a committed `uv.lock`;
4. a documented clean-machine bootstrap and launch command;
5. a clean-environment verification run on the evaluator's macOS/arm64 class of machine.

`uv` can install and manage Python versions, and has supported macOS binaries, so this is readily provisionable once documented. The official installation and project workflows are described in the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) and [uv feature guide](https://docs.astral.sh/uv/getting-started/features/).

### [P1] The application server dependency and launch contract are missing

**Evidence**

- The stack lists FastAPI but no ASGI server or FastAPI extra.
- `app/main.py` is described as the composition root, but no committed command identifies how it is served, on which host, or how Alembic runs before serving.
- AD-13 requires migrations before serving and AD-22 requires loopback-only binding; neither invariant has an executable startup contract.

**Impact**

Installing plain `fastapi==0.138.2` does not, by itself, make the intended local process contract explicit. Different implementers could install different server extras or launch with the unsafe default shown in generic examples.

**Required resolution**

Choose and pin one runtime contract, for example `fastapi[standard]==0.138.2` or an explicitly pinned `uvicorn[standard]`, then define one repository-owned command that:

1. executes `alembic upgrade head`;
2. fails closed if migration fails;
3. starts exactly one process;
4. binds `127.0.0.1`;
5. serves `app.main:app`.

FastAPI's official deployment documentation states that an ASGI server such as Uvicorn is required and that `fastapi[standard]` includes it: [Run a Server Manually](https://fastapi.tiangolo.com/deployment/manually/).

### [P1] AD-15 requires browser smoke tests, but no browser-test technology is committed

**Evidence**

- AD-15 makes browser smoke tests mandatory for UJ-1–UJ-3.
- The Stack and Structural Seed name only `tests/browser/`; they do not select Playwright, Selenium, or another runner, nor specify supported browser/version.
- “ECMAScript 2023 baseline” is a language target, not an executable browser compatibility matrix.

**Impact**

The architecture cannot prove its own UI acceptance and accessibility-related flow invariants reproducibly. Implementers could choose incompatible runners or leave the mandatory layer manual.

**Required resolution**

Commit one browser automation stack and its browser provisioning command, pin it in the lockfile, and state the evaluator browser target. For a Python-only toolchain, a pinned Playwright-for-Python dependency plus its managed Chromium install is a coherent option; alternatively, explicitly downgrade AD-15 to a manual checklist for the course MVP.

### [P2] Exact version pins are valid but the pinning policy is unexplained and partly stale

**Reality check**

| Technology | Declared | Status on review date | Compatibility |
| --- | ---: | --- | --- |
| Python | 3.12.10 | Stable but superseded by 3.12.13; 3.12 is security-fixes-only | Compatible |
| uv | 0.11.16 | Stable, real release; newer 0.11.32 exists | Compatible |
| FastAPI | 0.138.2 | Stable, real release; newer 0.139.2 exists | Compatible with Python 3.12 and Pydantic 2 |
| Pydantic | 2.13.4 | Current stable 2.x on the checked index; 2.14.0a1 is prerelease | Compatible |
| SQLAlchemy Core | 2.0.51 | Current stable 2.0 line; 2.1 is prerelease | Compatible |
| Alembic | 1.18.5 | Current stable release | Compatible with Python 3.12 / SQLAlchemy 2.0 |
| pytest | 9.1.1 | Current stable release | Requires Python >=3.10; compatible |
| coverage.py | 7.13.5 | Stable but superseded by 7.15.2 | Compatible |

Primary release evidence: [Python 3.12.10](https://www.python.org/downloads/release/python-31210/), [uv 0.11.16](https://pypi.org/project/uv/0.11.16/), [FastAPI 0.138.2](https://pypi.org/project/fastapi/0.138.2/), [Pydantic 2.13.4](https://pypi.org/project/pydantic/), [SQLAlchemy 2.0.51](https://pypi.org/project/SQLAlchemy/), [Alembic 1.18.5](https://pypi.org/project/alembic/), [pytest 9.1.1](https://pypi.org/project/pytest/9.1.1/), and [coverage.py 7.13.5](https://pypi.org/project/coverage/7.13.5/).

**Impact**

Older exact pins are not inherently wrong, but an unexplained patch-level freeze will look accidental and invites inconsistency between the Stack table, `pyproject.toml`, and the future lockfile. Python 3.12.10 is particularly awkward because Python.org explicitly marks it superseded.

**Required resolution**

State a version policy:

- pin Python to the supported series (`>=3.12,<3.13`) and let the provisioning artifact select the latest available 3.12 security patch; or
- retain exact `3.12.10` and document why reproducibility outweighs later security fixes.

For libraries, make `pyproject.toml` the direct-dependency policy and `uv.lock` the exact graph. Do not maintain an independent manually copied patch-version table unless it is generated or verified against those files.

### [P2] “SQLite = CPython bundled version” is not a reproducible version declaration

**Evidence**

- The local legacy Python 3.9.6 reports SQLite 3.43.2.
- A uv-managed Python 3.12 build may bundle a different SQLite patch than a python.org or system build.
- No minimum SQLite version or startup capability check is stated.

**Impact**

The selected features (foreign keys, WAL, busy timeout, backup API) are broadly available, so this is not a likely functional incompatibility. It is nevertheless impossible to reproduce the exact database engine from the Stack table alone.

**Required resolution**

Specify capabilities and a tested minimum SQLite version, record `sqlite3.sqlite_version` in diagnostics/evidence, and verify the selected Python distribution on the evaluator platform. Avoid presenting “CPython bundled version” as an exact pin.

## Compatibility conclusion

No direct incompatibility was found among Python 3.12, FastAPI 0.138.2, Pydantic 2.13.4, SQLAlchemy 2.0.51, Alembic 1.18.5, pytest 9.1.1, and coverage.py 7.13.5. The design can remain Python-only and local, which is a good fit for the brownfield course project. Approval should be withheld only until the repository turns that viable selection into a clean-machine reproducible environment and closes the two omitted runtime/test-tool choices.

## Re-review

**Date:** 2026-07-27  
**Final verdict:** **PASS — technology architecture approved**

The updated spine resolves every blocking technology finding:

- AD-26 now makes `.python-version`, `pyproject.toml`, and `uv.lock` authoritative and defines `uv sync --frozen` as the reproducible provisioning path.
- The launch contract is explicit: `uv run smart-dispatch` runs migrations fail-closed and starts pinned Uvicorn 0.46.0 on `127.0.0.1:8000` with one worker.
- Playwright for Python 1.60.0 and its pinned browser build close the previously unspecified browser-smoke-test dependency and support Python 3.12 plus the evaluator's macOS/arm64 platform. See [Playwright 1.60.0 release metadata and wheels](https://pypi.org/project/playwright/1.60.0/).
- Uvicorn 0.46.0 is a real release supporting Python 3.12 and is compatible with the selected FastAPI runtime. See [Uvicorn 0.46.0 metadata](https://pypi.org/project/uvicorn/0.46.0/).
- SQLite now has a 3.35.0 capability floor; runtime version recording converts the platform-bundled engine from an implicit assumption into verifiable evidence.
- Patch updates require all four test layers to pass and the lockfile to be regenerated, resolving the version-drift policy gap.

No technology incompatibility or unresolved provisioning ambiguity remains in the architecture contract. Creation of the declared repository artifacts and successful clean-machine execution are implementation/readiness verification tasks, not remaining architecture defects.

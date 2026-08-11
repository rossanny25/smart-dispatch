import ast
from pathlib import Path

from app.domain.confidence.rules import (
    CONFIDENCE_REGISTRY_JSON,
    CONFIDENCE_REGISTRY_SHA256,
)


def test_confidence_registry_digest_is_complete_and_stable() -> None:
    import hashlib

    assert hashlib.sha256(
        CONFIDENCE_REGISTRY_JSON.encode("utf-8")
    ).hexdigest() == CONFIDENCE_REGISTRY_SHA256
    assert '"data_quality"' in CONFIDENCE_REGISTRY_JSON
    assert '"score_margin"' in CONFIDENCE_REGISTRY_JSON
    assert '"freshness_boundaries"' in CONFIDENCE_REGISTRY_JSON
    assert '"warning_rules"' in CONFIDENCE_REGISTRY_JSON
    assert '"explanation_templates"' in CONFIDENCE_REGISTRY_JSON


def test_confidence_domain_has_no_framework_or_io_dependencies() -> None:
    root = Path("app/domain/confidence")
    forbidden = {
        "fastapi",
        "pydantic",
        "sqlalchemy",
        "sqlite3",
        "requests",
        "httpx",
        "openai",
    }
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden), (path, imports & forbidden)

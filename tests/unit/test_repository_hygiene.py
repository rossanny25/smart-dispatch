from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_runtime_artifacts_are_ignored_but_learning_seed_is_preserved() -> None:
    ignore_text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    required_patterns = {
        ".venv/",
        "__pycache__/",
        ".pytest_cache/",
        ".coverage",
        "*.db",
        "*.db-wal",
        "*.db-shm",
        "*.db-journal",
        "*.startup.lock",
        "data/backups/",
        "*.test.db",
        "data/learning_store.runtime.json",
    }

    assert required_patterns.issubset(set(ignore_text.splitlines()))
    assert "data/learning_store.json" not in ignore_text


def test_readme_documents_the_frozen_launch_contract() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Python 3.12.10" in readme
    assert "uv 0.11.16" in readme
    assert "uv sync --frozen" in readme
    assert "uv run smart-dispatch" in readme
    assert "127.0.0.1:8000" in readme


def test_development_guide_documents_safety_and_scope() -> None:
    guide = (PROJECT_ROOT / "docs" / "development-guide.md").read_text(encoding="utf-8")

    for expected in (
        "data/smart_dispatch.db",
        "data/backups/",
        "python3 server.py",
        "HTTPS",
        "authentication",
        "Playwright",
        "migration",
        "fail",
    ):
        assert expected.lower() in guide.lower()

from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_python_version_is_pinned() -> None:
    assert (PROJECT_ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12.10"


def test_project_declares_exact_runtime_and_test_dependencies() -> None:
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["requires-python"] == "==3.12.10"
    assert project["project"]["scripts"]["smart-dispatch"] == "app.runtime:main"
    assert set(project["project"]["dependencies"]) == {
        "fastapi==0.138.2",
        "uvicorn==0.46.0",
        "pydantic==2.13.4",
        "sqlalchemy==2.0.51",
        "alembic==1.18.5",
    }
    assert set(project["dependency-groups"]["dev"]) == {
        "pytest==9.1.1",
        "coverage==7.13.5",
        "playwright==1.60.0",
    }


def test_exact_uv_lock_exists() -> None:
    lock_text = (PROJECT_ROOT / "uv.lock").read_text(encoding="utf-8")

    assert 'requires-python = "==3.12.10"' in lock_text
    for package in ("fastapi", "uvicorn", "pydantic", "sqlalchemy", "alembic", "pytest"):
        assert f'name = "{package}"' in lock_text

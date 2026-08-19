import json

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.adapters.stages.ollama_analyze import (
    OllamaAnalyzeStage,
    build_analyze_stage_from_environment,
)
from app.contracts.stages.analyze import AnalyzeOutputV1


def valid_input() -> dict:
    return {
        "schema_version": "v1",
        "configuration_version": "analysis-v1",
        "work_order": {
            "incident_text": "Corte general de electricidad en local comercial",
            "address": "Direccion privada",
            "zone": "Belgrano",
            "context": None,
        },
    }


def test_ollama_stage_uses_valid_local_proposal_with_llm_metadata() -> None:
    def fake_post_json(url: str, payload: dict, timeout: float) -> dict:
        assert url == "http://ollama.local:11434/api/generate"
        assert payload["model"] == "llama-local"
        assert "Direccion privada" not in payload["prompt"]
        assert timeout == 3.0
        return {
            "response": json.dumps(
                {
                    "category": "electricity",
                    "priority": 4,
                    "sla_target_minutes": 240,
                    "required_certifications": ["electrician_category_a"],
                    "estimated_service_duration_minutes": 90,
                }
            )
        }

    result = OllamaAnalyzeStage(
        base_url="http://ollama.local:11434",
        model="llama-local",
        timeout_seconds=3.0,
        post_json=fake_post_json,
    ).execute(valid_input())

    validated = AnalyzeOutputV1.model_validate(result)
    assert validated.adapter_metadata.kind == "llm"
    assert validated.adapter_metadata.provider == "ollama"
    assert validated.adapter_metadata.model == "llama-local"
    assert validated.requirements.category == "electricity"
    assert all(item.kind == "supplied" for item in validated.provenance)


def test_ollama_stage_falls_back_to_deterministic_when_response_is_invalid() -> None:
    def fake_post_json(url: str, payload: dict, timeout: float) -> dict:
        return {"response": "{\"category\":\"invented\"}"}

    result = OllamaAnalyzeStage(post_json=fake_post_json).execute(valid_input())
    expected = DeterministicAnalyzeStage().execute(valid_input())

    assert result == expected
    assert result["adapter_metadata"] == {
        "kind": "local",
        "provider": None,
        "model": None,
    }


def test_analyze_stage_environment_selector_is_local_only(monkeypatch) -> None:
    monkeypatch.delenv("SMART_DISPATCH_ANALYZE_ADAPTER", raising=False)
    assert isinstance(build_analyze_stage_from_environment(), DeterministicAnalyzeStage)

    monkeypatch.setenv("SMART_DISPATCH_ANALYZE_ADAPTER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
    assert isinstance(build_analyze_stage_from_environment(), OllamaAnalyzeStage)

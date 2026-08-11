import json
from dataclasses import FrozenInstanceError

import pytest

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.domain.analysis.rules import (
    ANALYSIS_CONFIGURATION_VERSION,
    ANALYSIS_REGISTRY_JSON,
    CATEGORY_RULES,
)


def analyze(incident_text: str, context=None) -> dict:
    return DeterministicAnalyzeStage().execute(
        {
            "schema_version": "v1",
            "configuration_version": ANALYSIS_CONFIGURATION_VERSION,
            "work_order": {
                "incident_text": incident_text,
                "address": "Dirección privada",
                "zone": "Centro",
                "context": context,
            },
        }
    )


def provenance(result: dict, field: str) -> dict:
    return next(item for item in result["provenance"] if item["field"] == field)


def test_infers_gas_requirements_with_rule_provenance() -> None:
    result = analyze("URGENTE: fuga de gás en la caldera")

    assert result["requirements"] == {
        "category": "gas",
        "priority": 5,
        "sla_target_minutes": 60,
        "required_certifications": ["gas_registered"],
        "estimated_service_duration_minutes": 90,
    }
    assert provenance(result, "category") == {
        "field": "category",
        "kind": "inferred",
        "rule_id": "category_gas_v1",
        "configuration_version": "analysis-v1",
    }
    assert result["warnings"] == []


def test_supplied_values_win_and_conflicts_do_not_copy_sensitive_values() -> None:
    result = analyze(
        "Fuga de gas crítica",
        {
            "dispatch_requirements": {
                "category": "maintenance",
                "priority": 1,
                "sla_target_minutes": 10080,
                "required_certifications": [],
                "estimated_service_duration_minutes": 30,
            }
        },
    )

    assert result["requirements"]["category"] == "maintenance"
    assert all(item["kind"] == "supplied" for item in result["provenance"])
    assert all("Fuga" not in json.dumps(item) for item in result["warnings"])
    assert {item["code"] for item in result["warnings"]} == {
        "ANALYZE_SUPPLIED_CONFLICT"
    }


def test_unsupported_and_ambiguous_incidents_default_with_stable_warnings() -> None:
    unsupported = analyze("Objeto desconocido sin vocabulario técnico")
    ambiguous = analyze("Fuga de gas y corte de electricidad")

    assert unsupported["requirements"]["category"] == "maintenance"
    assert ambiguous["requirements"]["category"] == "maintenance"
    assert "ANALYZE_UNSUPPORTED_INCIDENT" in {
        warning["code"] for warning in unsupported["warnings"]
    }
    assert "ANALYZE_AMBIGUOUS_CATEGORY" in {
        warning["code"] for warning in ambiguous["warnings"]
    }
    assert provenance(unsupported, "category")["kind"] == "defaulted"


def test_fiber_inference_is_deduplicated_sorted_and_byte_deterministic() -> None:
    first = analyze("Urgente: enlace de fibra en altura sin servicio")
    second = analyze("Urgente: enlace de fibra en altura sin servicio")

    assert first["requirements"]["required_certifications"] == [
        "fiber_optics",
        "wan_networks",
        "working_at_height",
    ]
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(
        second,
        sort_keys=True,
        separators=(",", ":"),
    )


@pytest.mark.parametrize(
    ("incident", "category", "priority", "duration"),
    [
        ("Corte urgente de electricidad", "electricity", 4, 120),
        ("Enlace de internet", "telecommunications", 3, 60),
        ("Inundación de agua", "plumbing", 4, 90),
        ("Climatización industrial", "hvac", 3, 120),
        ("Inspección preventiva", "maintenance", 1, 60),
    ],
)
def test_each_category_rule_is_explicit(
    incident: str,
    category: str,
    priority: int,
    duration: int,
) -> None:
    result = analyze(incident)

    assert result["requirements"]["category"] == category
    assert result["requirements"]["priority"] == priority
    assert result["requirements"]["estimated_service_duration_minutes"] == duration


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category", "hvac"),
        ("priority", 5),
        ("sla_target_minutes", 90),
        ("required_certifications", ["wan_networks"]),
        ("estimated_service_duration_minutes", 45),
    ],
)
def test_each_supported_context_field_is_supplied(field: str, value) -> None:
    result = analyze(
        "Incidente sin clasificación conocida",
        {"dispatch_requirements": {field: value}},
    )

    assert result["requirements"][field] == value
    assert provenance(result, field) == {
        "field": field,
        "kind": "supplied",
        "source_field": f"/context/dispatch_requirements/{field}",
    }


def test_registry_is_deeply_immutable_and_digest_covers_conditional_rules() -> None:
    with pytest.raises(FrozenInstanceError):
        CATEGORY_RULES[0].phrases = ("changed",)
    assert "priority_conditions" in ANALYSIS_REGISTRY_JSON
    assert "conditional_certifications" in ANALYSIS_REGISTRY_JSON


def test_supplied_category_resolves_ambiguity_for_dependent_fields() -> None:
    result = analyze(
        "Fuga de gas y corte de electricidad",
        {"dispatch_requirements": {"category": "gas"}},
    )

    assert result["requirements"]["priority"] == 5
    assert result["requirements"]["required_certifications"] == ["gas_registered"]
    assert result["requirements"]["estimated_service_duration_minutes"] == 90
    assert "ANALYZE_AMBIGUOUS_CATEGORY" not in {
        warning["code"] for warning in result["warnings"]
    }


def test_unique_critical_signal_survives_unresolved_category_ambiguity() -> None:
    result = analyze("Fuga de gas y corte de electricidad")

    assert result["requirements"]["category"] == "maintenance"
    assert result["requirements"]["priority"] == 5
    assert result["requirements"]["sla_target_minutes"] == 60


def test_conflict_warning_contains_rules_but_not_the_supplied_value() -> None:
    result = analyze(
        "Fuga de gas",
        {"dispatch_requirements": {"priority": 1}},
    )
    warning = next(
        item
        for item in result["warnings"]
        if item["code"] == "ANALYZE_SUPPLIED_CONFLICT"
    )

    assert warning["fallback"] is None
    assert warning["rule_ids"] == ["category_gas_v1"]
    assert "1" not in warning["source"]

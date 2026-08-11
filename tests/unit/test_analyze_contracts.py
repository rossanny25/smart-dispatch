import pytest
from pydantic import ValidationError

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.contracts.stages.analyze import AnalyzeInputV1, AnalyzeOutputV1


def valid_input() -> dict:
    return {
        "schema_version": "v1",
        "configuration_version": "analysis-v1",
        "work_order": {
            "incident_text": "Fuga de gas",
            "address": "Calle 1",
            "zone": "Centro",
            "context": None,
        },
    }


def test_analyze_input_rejects_unknown_and_invalid_supplied_values() -> None:
    with pytest.raises(ValidationError):
        AnalyzeInputV1.model_validate({**valid_input(), "extra": True})

    payload = valid_input()
    payload["work_order"]["context"] = {
        "dispatch_requirements": {"priority": True}
    }
    with pytest.raises(ValidationError):
        AnalyzeInputV1.model_validate(payload)


def test_analyze_input_rejects_unknown_dispatch_requirement() -> None:
    payload = valid_input()
    payload["work_order"]["context"] = {
        "dispatch_requirements": {"unknown": "value"}
    }
    with pytest.raises(ValidationError):
        AnalyzeInputV1.model_validate(payload)


def test_analyze_input_rejects_explicit_null_as_supplied_value() -> None:
    payload = valid_input()
    payload["work_order"]["context"] = {
        "dispatch_requirements": {"priority": None}
    }
    with pytest.raises(ValidationError):
        AnalyzeInputV1.model_validate(payload)


def test_analyze_output_rejects_duplicate_certifications_and_bad_provenance() -> None:
    output = {
        "schema_version": "v1",
        "configuration_version": "analysis-v1",
        "requirements": {
            "category": "gas",
            "priority": 5,
            "sla_target_minutes": 60,
            "required_certifications": ["gas_registered", "gas_registered"],
            "estimated_service_duration_minutes": 90,
        },
        "provenance": [],
        "warnings": [],
        "adapter_metadata": {"kind": "local", "provider": None, "model": None},
    }
    with pytest.raises(ValidationError):
        AnalyzeOutputV1.model_validate(output)


def test_defaulted_output_requires_matching_structured_warning() -> None:
    output = {
        "schema_version": "v1",
        "configuration_version": "analysis-v1",
        "requirements": {
            "category": "maintenance",
            "priority": 3,
            "sla_target_minutes": 720,
            "required_certifications": [],
            "estimated_service_duration_minutes": 60,
        },
        "provenance": [
            {
                "field": field,
                "kind": "defaulted",
                "rule_id": f"default_{field}_v1",
                "configuration_version": "analysis-v1",
            }
            for field in (
                "category",
                "priority",
                "sla_target_minutes",
                "required_certifications",
                "estimated_service_duration_minutes",
            )
        ],
        "warnings": [],
        "adapter_metadata": {"kind": "local", "provider": None, "model": None},
    }

    with pytest.raises(ValidationError):
        AnalyzeOutputV1.model_validate(output)


def test_supplied_provenance_source_must_match_its_field() -> None:
    from app.contracts.stages.analyze import SuppliedProvenanceV1

    with pytest.raises(ValidationError):
        SuppliedProvenanceV1.model_validate(
            {
                "field": "priority",
                "kind": "supplied",
                "source_field": "/context/dispatch_requirements/category",
            }
        )


def test_output_rejects_invented_rule_and_duplicate_warning() -> None:
    result = DeterministicAnalyzeStage().execute(valid_input())
    result["provenance"][0]["rule_id"] = "invented_rule"
    with pytest.raises(ValidationError):
        AnalyzeOutputV1.model_validate(result)

    result = DeterministicAnalyzeStage().execute(
        {
            **valid_input(),
            "work_order": {
                **valid_input()["work_order"],
                "incident_text": "Sin términos conocidos",
            },
        }
    )
    result["warnings"].append(dict(result["warnings"][0]))
    result["warnings"].sort(
        key=lambda item: (item["affected_field"], item["code"], item["source"])
    )
    with pytest.raises(ValidationError):
        AnalyzeOutputV1.model_validate(result)


def test_output_rejects_arbitrary_sensitive_warning_metadata() -> None:
    result = DeterministicAnalyzeStage().execute(
        {
            **valid_input(),
            "work_order": {
                **valid_input()["work_order"],
                "incident_text": "Sin términos conocidos",
            },
        }
    )
    result["warnings"][0]["impact"] = "Calle 1"
    with pytest.raises(ValidationError):
        AnalyzeOutputV1.model_validate(result)


@pytest.mark.parametrize(
    ("incident_text", "context"),
    [
        ("Fuga de gas y corte de electricidad", None),
        (
            "Fuga de gas",
            {"dispatch_requirements": {"priority": 1}},
        ),
    ],
)
def test_adapter_ambiguous_and_conflict_outputs_satisfy_strict_contract(
    incident_text: str,
    context,
) -> None:
    payload = valid_input()
    payload["work_order"]["incident_text"] = incident_text
    payload["work_order"]["context"] = context

    result = DeterministicAnalyzeStage().execute(payload)

    assert AnalyzeOutputV1.model_validate(result).model_dump(mode="json") == result

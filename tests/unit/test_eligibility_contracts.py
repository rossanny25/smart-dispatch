from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.contracts.eligibility import EligibilityInputV1, EligibilityOutputV1
from app.domain.eligibility.policy import EligibilityPolicy
from app.domain.eligibility.rules import ELIGIBILITY_CONFIGURATION


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)


def valid_input() -> dict:
    return {
        "schema_version": "v1",
        "configuration_version": "eligibility-v1",
        "requirements": {
            "priority": 5,
            "required_certifications": ["gas_registered"],
            "estimated_service_duration_minutes": 90,
        },
        "captured_at": "2026-07-28T12:00:00Z",
        "technicians": [
            {
                "technician_id": "33333333-3333-4333-8333-333333333333",
                "availability": "available",
                "certifications": ["gas_registered"],
                "shift_start": "2026-07-28T08:00:00Z",
                "shift_end": "2026-07-28T16:00:00Z",
                "assigned_work_minutes": 300,
                "accumulated_driving_minutes": 120,
                "has_required_epp": True,
                "estimated_travel_minutes": 30,
                "distance_meters": 60000,
            }
        ],
    }


def valid_output() -> dict:
    model = EligibilityInputV1.model_validate(valid_input())
    result = EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=model.to_domain_requirements(),
        captured_at=model.captured_at,
        technicians=model.to_domain_technicians(),
    )
    return EligibilityOutputV1.from_domain(result).model_dump(mode="json")


def test_input_is_strict_canonical_and_accepts_empty_roster() -> None:
    empty = valid_input()
    empty["technicians"] = []
    assert EligibilityInputV1.model_validate(empty).technicians == []

    for mutation in (
        lambda value: value.update({"captured_at": "2026-07-28T12:00:00"}),
        lambda value: value["technicians"][0].update({"assigned_work_minutes": True}),
        lambda value: value["technicians"][0].update({"score": 100}),
        lambda value: value["technicians"][0].update(
            {"certifications": ["gas_registered", "gas_registered"]}
        ),
    ):
        invalid = valid_input()
        mutation(invalid)
        with pytest.raises(ValidationError):
            EligibilityInputV1.model_validate(invalid)


def test_output_rejects_incomplete_checks_partition_mismatch_and_extra_score() -> None:
    output = valid_output()
    for mutation in (
        lambda value: value["candidates"][0]["checks"].pop(),
        lambda value: value.update({"eligible_technician_ids": []}),
        lambda value: value["candidates"][0].update({"score": 100}),
    ):
        invalid = valid_output()
        mutation(invalid)
        with pytest.raises(ValidationError):
            EligibilityOutputV1.model_validate(invalid)


@pytest.mark.parametrize(
    ("check_index", "field", "value"),
    [
        (0, "observed", "invented"),
        (1, "missing", ["gas_registered"]),
        (2, "projected_finish", "garbage"),
        (3, "projected_workday_minutes", 999),
        (4, "projected_driving_minutes", 999),
        (5, "required_for_priority", False),
    ],
)
def test_output_rejects_semantically_invalid_check_evidence(
    check_index: int,
    field: str,
    value,
) -> None:
    invalid = valid_output()
    invalid["candidates"][0]["checks"][check_index]["evidence"][field] = value

    with pytest.raises(ValidationError):
        EligibilityOutputV1.model_validate(invalid)


def test_output_rejects_noncanonical_warning_template() -> None:
    invalid_input = valid_input()
    invalid_input["technicians"][0]["accumulated_driving_minutes"] = None
    input_model = EligibilityInputV1.model_validate(invalid_input)
    output = EligibilityOutputV1.from_domain(
        EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
            requirements=input_model.to_domain_requirements(),
            captured_at=input_model.captured_at,
            technicians=input_model.to_domain_technicians(),
        )
    ).model_dump(mode="json")
    output["candidates"][0]["warnings"][0]["impact"] = "arbitrary"

    with pytest.raises(ValidationError):
        EligibilityOutputV1.model_validate(output)


def test_input_rejects_duplicate_or_unsorted_roster_and_all_forbidden_fields() -> None:
    duplicate = valid_input()
    duplicate["technicians"].append(dict(duplicate["technicians"][0]))
    with pytest.raises(ValidationError):
        EligibilityInputV1.model_validate(duplicate)

    for field in ("rank", "confidence", "recommendation", "memory", "state"):
        invalid = valid_input()
        invalid["technicians"][0][field] = "forbidden"
        with pytest.raises(ValidationError):
            EligibilityInputV1.model_validate(invalid)


def test_canonical_output_round_trip_is_stable() -> None:
    output = valid_output()
    assert EligibilityOutputV1.model_validate(output).model_dump(mode="json") == output

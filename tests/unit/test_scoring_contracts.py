from copy import deepcopy
from decimal import getcontext

import pytest
from pydantic import ValidationError

from app.contracts.scoring import (
    ScoringInputV1,
    ScoringOutputV1,
    validate_output_against_input,
)
from app.contracts.eligibility import EligibilityInputV1, EligibilityOutputV1
from app.domain.eligibility.policy import EligibilityPolicy
from app.domain.eligibility.rules import ELIGIBILITY_CONFIGURATION
from app.domain.scoring.policy import ScoringPolicy
from app.domain.scoring.rules import SCORING_CONFIGURATION


def scoring_input() -> dict:
    eligibility_input = EligibilityInputV1.model_validate(
        {
            "requirements": {
                "priority": 3,
                "required_certifications": [],
                "estimated_service_duration_minutes": 60,
            },
            "captured_at": "2026-07-28T12:00:00Z",
            "technicians": [
                {
                    "technician_id": "11111111-1111-4111-8111-111111111111",
                    "availability": "available",
                    "certifications": [],
                    "shift_start": "2026-07-28T08:00:00Z",
                    "shift_end": "2026-07-28T18:00:00Z",
                    "assigned_work_minutes": 150,
                    "accumulated_driving_minutes": 30,
                    "has_required_epp": None,
                    "estimated_travel_minutes": 30,
                    "distance_meters": 10000,
                },
                {
                    "technician_id": "22222222-2222-4222-8222-222222222222",
                    "availability": "busy",
                    "certifications": [],
                    "shift_start": "2026-07-28T08:00:00Z",
                    "shift_end": "2026-07-28T18:00:00Z",
                    "assigned_work_minutes": 120,
                    "accumulated_driving_minutes": 20,
                    "has_required_epp": None,
                    "estimated_travel_minutes": 20,
                    "distance_meters": 5000,
                },
            ],
        }
    )
    eligibility_output = EligibilityOutputV1.from_domain(
        EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
            requirements=eligibility_input.to_domain_requirements(),
            captured_at=eligibility_input.captured_at,
            technicians=eligibility_input.to_domain_technicians(),
        )
    )
    return {
        "schema_version": "v1",
        "configuration_version": "scoring-v1",
        "eligibility_evaluation_set_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "sla_minutes": 60,
        "eligibility_output": eligibility_output.model_dump(mode="json"),
        "technicians": (
            {
                "technician_id": "11111111-1111-4111-8111-111111111111",
                "eta_minutes": 30,
                "distance_meters": 10000,
                "projected_work_minutes": 240,
                "quality_rating_0_to_5": "4.25",
            },
            {
                "technician_id": "22222222-2222-4222-8222-222222222222",
                "eta_minutes": 20,
                "distance_meters": 5000,
                "projected_work_minutes": 200,
                "quality_rating_0_to_5": None,
            },
        ),
    }


def test_contract_rejects_float_quality_and_noncanonical_roster() -> None:
    payload = scoring_input()
    payload["technicians"][0]["quality_rating_0_to_5"] = 4.25
    with pytest.raises(ValidationError):
        ScoringInputV1.model_validate(payload)

    payload = scoring_input()
    payload["technicians"] = tuple(reversed(payload["technicians"]))
    with pytest.raises(ValidationError):
        ScoringInputV1.model_validate(payload)


def test_output_is_semantically_bound_to_input() -> None:
    input_model = ScoringInputV1.model_validate(scoring_input())
    domain_result = ScoringPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=input_model.sla_minutes,
        technicians=input_model.to_domain_eligible_technicians(),
    )
    output = ScoringOutputV1.from_domain(
        domain_result,
        ineligible_candidates=[
            item for item in input_model.eligibility_output.candidates
            if not item.eligible
        ],
    )
    validate_output_against_input(input_model, output)

    corrupt = deepcopy(output.model_dump(mode="json"))
    corrupt["eligible_candidates"][0]["objective_score"] = "99"
    with pytest.raises((ValidationError, ValueError)):
        candidate = ScoringOutputV1.model_validate(corrupt)
        validate_output_against_input(input_model, candidate)


def test_ineligible_results_have_no_scoring_placeholders() -> None:
    input_model = ScoringInputV1.model_validate(scoring_input())
    output = ScoringOutputV1.from_domain(
        ScoringPolicy(SCORING_CONFIGURATION).evaluate(
            sla_minutes=input_model.sla_minutes,
            technicians=input_model.to_domain_eligible_technicians(),
        ),
        ineligible_candidates=[
            item for item in input_model.eligibility_output.candidates
            if not item.eligible
        ],
    )
    dumped = output.model_dump(mode="json")
    assert dumped["ineligible_candidates"][0]["technician_id"] == (
        "22222222-2222-4222-8222-222222222222"
    )
    assert dumped["ineligible_candidates"][0]["eligibility"]["eligible"] is False
    assert "score" not in str(dumped["ineligible_candidates"]).lower()


def test_contract_arithmetic_is_independent_of_process_decimal_context() -> None:
    payload = scoring_input()
    payload["sla_minutes"] = 3
    payload["technicians"][0]["eta_minutes"] = 1
    payload["technicians"][0]["projected_work_minutes"] = 61
    shift = payload["eligibility_output"]["candidates"][0]["checks"][2]["evidence"]
    shift["travel_minutes"] = 1
    shift["projected_finish"] = "2026-07-28T13:01:00Z"
    workday = payload["eligibility_output"]["candidates"][0]["checks"][3]["evidence"]
    workday["assigned_work_minutes"] = 0
    workday["travel_minutes"] = 1
    workday["projected_workday_minutes"] = 61
    input_model = ScoringInputV1.model_validate(payload)
    domain = ScoringPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=3,
        technicians=input_model.to_domain_eligible_technicians(),
    )
    original = getcontext().prec
    try:
        getcontext().prec = 5
        output = ScoringOutputV1.from_domain(
            domain,
            ineligible_candidates=[
                item
                for item in input_model.eligibility_output.candidates
                if not item.eligible
            ],
        )
        validate_output_against_input(input_model, output)
    finally:
        getcontext().prec = original


def test_contract_rejects_oversized_quality_and_fabricated_raw_evidence() -> None:
    payload = scoring_input()
    payload["technicians"][0]["quality_rating_0_to_5"] = "0." + ("0" * 5000) + "1"
    with pytest.raises(ValidationError):
        ScoringInputV1.model_validate(payload)

    input_model = ScoringInputV1.model_validate(scoring_input())
    output = ScoringOutputV1.from_domain(
        ScoringPolicy(SCORING_CONFIGURATION).evaluate(
            sla_minutes=input_model.sla_minutes,
            technicians=input_model.to_domain_eligible_technicians(),
        ),
        ineligible_candidates=[
            item for item in input_model.eligibility_output.candidates
            if not item.eligible
        ],
    ).model_dump(mode="json")
    output["eligible_candidates"][0]["components"][0]["raw_inputs"][
        "eta_minutes"
    ] = "fabricated"
    with pytest.raises(ValidationError):
        ScoringOutputV1.model_validate(output)

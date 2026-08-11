from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.domain.eligibility.models import (
    EligibilityRequirements,
    EligibilityTechnician,
)
from app.domain.eligibility.policy import EligibilityPolicy
from app.domain.eligibility.rules import ELIGIBILITY_CONFIGURATION


NOW = datetime(2026, 7, 28, 12, tzinfo=UTC)
TECHNICIAN_ID = UUID("33333333-3333-4333-8333-333333333333")


def technician(**changes) -> EligibilityTechnician:
    values = {
        "technician_id": TECHNICIAN_ID,
        "availability": "available",
        "certifications": ("gas_registered",),
        "shift_start": NOW - timedelta(hours=4),
        "shift_end": NOW + timedelta(hours=4),
        "assigned_work_minutes": 300,
        "accumulated_driving_minutes": 120,
        "has_required_epp": True,
        "estimated_travel_minutes": 30,
        "distance_meters": 60_000,
    }
    values.update(changes)
    return EligibilityTechnician(**values)


def evaluate(candidate=None, *, priority=5, duration=90, configuration=None):
    return EligibilityPolicy(configuration or ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=EligibilityRequirements(
            priority=priority,
            required_certifications=("gas_registered",),
            estimated_service_duration_minutes=duration,
        ),
        captured_at=NOW,
        technicians=() if candidate is None else (candidate,),
    )


def test_empty_roster_is_a_deterministic_no_feasible_result() -> None:
    first = evaluate()
    second = evaluate()

    assert first == second
    assert first.candidates == ()
    assert first.eligible_technician_ids == ()
    assert first.ineligible_technician_ids == ()
    assert first.no_feasible_candidates is True


def test_all_six_checks_run_and_distance_over_50km_is_not_a_gate() -> None:
    result = evaluate(technician(distance_meters=999_999))
    candidate = result.candidates[0]

    assert [check.name for check in candidate.checks] == [
        "availability",
        "certifications",
        "shift",
        "maximum_workday",
        "driving_limit",
        "required_epp",
    ]
    assert all(check.status == "pass" for check in candidate.checks)
    assert candidate.eligible is True
    assert candidate.distance_meters == 999_999


def test_combined_failures_are_complete_and_priority_five_never_bypasses() -> None:
    result = evaluate(
        technician(
            availability="busy",
            certifications=(),
            shift_start=NOW + timedelta(minutes=1),
            shift_end=NOW + timedelta(minutes=30),
            assigned_work_minutes=400,
            accumulated_driving_minutes=230,
            has_required_epp=False,
        )
    )
    candidate = result.candidates[0]

    assert [check.status for check in candidate.checks] == ["fail"] * 6
    assert [check.reason for check in candidate.checks] == [
        "TECHNICIAN_UNAVAILABLE",
        "CERTIFICATIONS_MISSING",
        "OUTSIDE_SHIFT",
        "MAXIMUM_WORKDAY_EXCEEDED",
        "DRIVING_LIMIT_EXCEEDED",
        "REQUIRED_EPP_MISSING",
    ]
    assert candidate.eligible is False


def test_exact_workday_and_driving_limits_pass_and_one_minute_over_fails() -> None:
    exact = evaluate(
        technician(assigned_work_minutes=360, accumulated_driving_minutes=210)
    ).candidates[0]
    over = evaluate(
        technician(assigned_work_minutes=361, accumulated_driving_minutes=211)
    ).candidates[0]

    assert exact.checks[3].status == "pass"
    assert exact.checks[4].status == "pass"
    assert over.checks[3].reason == "MAXIMUM_WORKDAY_EXCEEDED"
    assert over.checks[4].reason == "DRIVING_LIMIT_EXCEEDED"


def test_missing_and_future_disabled_safety_inputs_fail_closed_with_warnings() -> None:
    missing = evaluate(
        technician(accumulated_driving_minutes=None, has_required_epp=None)
    ).candidates[0]
    disabled_configuration = replace(
        ELIGIBILITY_CONFIGURATION,
        version="eligibility-future-disabled",
        driving_limit_enabled=False,
        required_epp_enabled=False,
    )
    disabled = evaluate(
        technician(),
        configuration=disabled_configuration,
    ).candidates[0]

    assert [missing.checks[index].reason for index in (4, 5)] == [
        "SOURCE_DATA_UNAVAILABLE",
        "SOURCE_DATA_UNAVAILABLE",
    ]
    assert [warning.code for warning in missing.warnings] == [
        "ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        "ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
    ]
    assert [disabled.checks[index].reason for index in (4, 5)] == [
        "CHECK_DISABLED",
        "CHECK_DISABLED",
    ]
    assert [warning.code for warning in disabled.warnings] == [
        "ELIGIBILITY_CHECK_DISABLED",
        "ELIGIBILITY_CHECK_DISABLED",
    ]


def test_low_priority_does_not_require_epp_source_data() -> None:
    candidate = evaluate(
        technician(has_required_epp=None),
        priority=3,
    ).candidates[0]

    assert candidate.checks[5].status == "pass"
    assert candidate.checks[5].reason == "EPP_NOT_REQUIRED_FOR_PRIORITY"
    assert candidate.warnings == ()


@pytest.mark.parametrize("availability", ["busy", "absent", "off_duty"])
def test_every_unavailable_state_fails(availability: str) -> None:
    candidate = evaluate(
        technician(availability=availability)
    ).candidates[0]
    assert candidate.checks[0].reason == "TECHNICIAN_UNAVAILABLE"


def test_empty_certification_requirement_passes() -> None:
    result = EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=EligibilityRequirements(
            priority=3,
            required_certifications=(),
            estimated_service_duration_minutes=60,
        ),
        captured_at=NOW,
        technicians=(technician(certifications=()),),
    )
    assert result.candidates[0].checks[1].reason == "NO_CERTIFICATIONS_REQUIRED"


def test_shift_start_and_exact_finish_pass_while_shift_end_and_overrun_fail() -> None:
    at_start = EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=EligibilityRequirements(
            priority=3,
            required_certifications=("gas_registered",),
            estimated_service_duration_minutes=60,
        ),
        captured_at=NOW,
        technicians=(
            technician(
                shift_start=NOW,
                shift_end=NOW + timedelta(minutes=90),
                estimated_travel_minutes=30,
            ),
        ),
    ).candidates[0]
    at_end = evaluate(
        technician(shift_start=NOW - timedelta(hours=1), shift_end=NOW)
    ).candidates[0]
    overrun = EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=EligibilityRequirements(
            priority=3,
            required_certifications=("gas_registered",),
            estimated_service_duration_minutes=61,
        ),
        captured_at=NOW,
        technicians=(
            technician(
                shift_start=NOW,
                shift_end=NOW + timedelta(minutes=90),
                estimated_travel_minutes=30,
            ),
        ),
    ).candidates[0]

    assert at_start.checks[2].reason == "WITHIN_SHIFT"
    assert at_end.checks[2].reason == "OUTSIDE_SHIFT"
    assert overrun.checks[2].reason == "SHIFT_END_EXCEEDED"


def test_datetime_projection_overflow_fails_closed() -> None:
    near_maximum = datetime.max.replace(tzinfo=UTC) - timedelta(minutes=1)
    result = EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=EligibilityRequirements(
            priority=3,
            required_certifications=(),
            estimated_service_duration_minutes=60,
        ),
        captured_at=near_maximum,
        technicians=(
            technician(
                certifications=(),
                shift_start=near_maximum - timedelta(minutes=1),
                shift_end=datetime.max.replace(tzinfo=UTC),
                estimated_travel_minutes=1,
            ),
        ),
    )
    assert result.candidates[0].checks[2].reason == "SHIFT_END_EXCEEDED"

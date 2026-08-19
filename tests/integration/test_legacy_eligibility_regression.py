import pytest

from app.adapters.legacy.compatibility import build_hard_rule_checks, technicians


@pytest.mark.parametrize("priority", [3, 5])
def test_overtime_is_rejected_for_every_priority_without_push_failure(
    priority: int,
) -> None:
    technician = {**technicians[0], "active_workload_hours": 7.5}
    checks, rejection_reasons, _ = build_hard_rule_checks(
        technician,
        {"structured_data": {"priority": priority}},
        travel_minutes=60,
    )

    by_key = {check["key"]: check for check in checks}
    assert by_key["workload"]["status"] == "fail"
    assert rejection_reasons == ["Jornada proyectada: 10.0hs"]

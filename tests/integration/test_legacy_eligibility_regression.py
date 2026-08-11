import pytest

from app.adapters.legacy.compatibility import evaluate_candidates, technicians


@pytest.mark.parametrize("priority", [3, 5])
def test_overtime_is_rejected_for_every_priority_without_push_failure(
    priority: int,
) -> None:
    original = technicians[0]["active_workload_hours"]
    technicians[0]["active_workload_hours"] = 7.5
    try:
        result = evaluate_candidates(
            [
                {
                    "technician_id": technicians[0]["id"],
                    "calculated_travel_time_minutes": 60,
                    "gps_signal": "online",
                }
            ],
            {"structured_data": {"priority": priority}},
        )
    finally:
        technicians[0]["active_workload_hours"] = original

    assert result[0]["validation_status"] == "rechazado"
    assert result[0]["alerts"] == ["Exceso de jornada: 10.0hs."]

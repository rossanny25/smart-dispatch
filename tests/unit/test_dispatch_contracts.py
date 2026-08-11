from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.contracts.dispatch_runs import DispatchRunStartV1


def valid_input() -> dict:
    technician_id = "33333333-3333-4333-8333-333333333333"
    return {
        "schema_version": "v1",
        "work_order_id": "11111111-1111-4111-8111-111111111111",
        "captured_at": "2026-07-28T12:00:00Z",
        "technicians": [
            {
                "technician_id": technician_id,
                "availability": "available",
                "certifications": ["gas_registered"],
                "shift_start": "2026-07-28T08:00:00Z",
                "shift_end": "2026-07-28T18:00:00Z",
                "assigned_work_minutes": 120,
                "accumulated_driving_minutes": 30,
                "has_required_epp": True,
                "estimated_travel_minutes": 20,
                "distance_meters": 10_000,
            }
        ],
        "technician_quality": [
            {
                "technician_id": technician_id,
                "quality_rating_0_to_5": "4.5",
            }
        ],
        "gps_observations": [
            {
                "technician_id": technician_id,
                "observed_at": "2026-07-28T11:55:00Z",
                "last_known_zone": "Centro",
            }
        ],
        "traffic_observed_at": "2026-07-28T11:58:00Z",
        "weather_observed_at": "2026-07-28T11:57:00Z",
        "active_supporting_episode_count": 0,
        "memory_experiment_mode": "disabled",
    }


def test_dispatch_input_is_strict_frozen_and_rosters_are_exact() -> None:
    model = DispatchRunStartV1.model_validate(valid_input())
    assert str(model.technicians[0].technician_id).startswith("33333333")
    with pytest.raises(ValidationError):
        model.captured_at = model.captured_at

    changed = deepcopy(valid_input())
    changed["gps_observations"] = []
    with pytest.raises(ValidationError):
        DispatchRunStartV1.model_validate(changed)

    extra = deepcopy(valid_input())
    extra["unexpected"] = True
    with pytest.raises(ValidationError):
        DispatchRunStartV1.model_validate(extra)

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contracts.confidence import ConfidenceInputV1


def valid_input() -> dict:
    return {
        "schema_version": "v1",
        "configuration_version": "confidence-v1",
        "scoring_evaluation_set_id": "10000000-0000-0000-0000-000000000001",
        "scoring_output_sha256": "0" * 64,
        "evaluated_at": "2026-07-28T12:00:00Z",
        "candidates": (
            {
                "technician_id": "00000000-0000-0000-0000-000000000001",
                "rank": 1,
                "objective_score": "90",
            },
        ),
        "gps_observations": (
            {
                "technician_id": "00000000-0000-0000-0000-000000000001",
                "observed_at": "2026-07-28T11:59:00Z",
                "last_known_zone": None,
            },
        ),
        "traffic": {
            "observed_at": "2026-07-28T11:59:00Z",
            "default_fallback": "seeded-normal",
        },
        "weather": {
            "observed_at": "2026-07-28T11:59:00Z",
            "default_fallback": "seeded-clear",
        },
        "active_supporting_episode_count": 0,
    }


def test_input_is_strict_frozen_and_canonical() -> None:
    model = ConfidenceInputV1.model_validate(valid_input())
    assert model.scoring_evaluation_set_id == UUID(
        "10000000-0000-0000-0000-000000000001"
    )
    assert model.evaluated_at == datetime(2026, 7, 28, 12, tzinfo=UTC)
    with pytest.raises(ValidationError):
        model.active_supporting_episode_count = 2


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("evaluated_at",), "2026-07-28T12:00:00"),
        (("active_supporting_episode_count",), True),
        (("active_supporting_episode_count",), -1),
        (("traffic", "unknown"), "x"),
    ],
)
def test_input_rejects_invalid_boundary_values(path: tuple[str, ...], value) -> None:
    payload = valid_input()
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        ConfidenceInputV1.model_validate(payload)


def test_environment_fallbacks_are_registry_bound() -> None:
    payload = valid_input()
    payload["traffic"]["default_fallback"] = "caller-choice"
    with pytest.raises(ValidationError, match="traffic fallback"):
        ConfidenceInputV1.model_validate(payload)

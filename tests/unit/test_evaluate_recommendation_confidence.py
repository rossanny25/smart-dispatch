from datetime import UTC, datetime

import pytest

from app.application.commands.evaluate_recommendation_confidence import (
    EvaluateRecommendationConfidence,
    EvaluateRecommendationConfidenceRequest,
    InvalidConfidenceInput,
    ScoringEvaluationNotFound,
)


class MissingScoringRows:
    def get_by_id(self, _):
        return None


class FakeUow:
    scoring_evaluations = MissingScoringRows()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def request(configuration_version: str = "confidence-v1"):
    return EvaluateRecommendationConfidenceRequest(
        scoring_evaluation_set_id="00000000-0000-0000-0000-000000000001",
        evaluated_at=datetime(2026, 7, 28, tzinfo=UTC),
        gps_observations=(),
        traffic_observed_at=None,
        weather_observed_at=None,
        active_supporting_episode_count=0,
        configuration_version=configuration_version,
    )


def test_rejects_wrong_configuration_before_opening_transaction() -> None:
    entered = False

    def factory():
        nonlocal entered
        entered = True
        return FakeUow()

    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=factory,
        uuid_factory=lambda: None,
        clock=lambda: None,
    )
    with pytest.raises(InvalidConfidenceInput):
        command.execute(request("other"))
    assert entered is False


def test_missing_scoring_is_a_typed_error() -> None:
    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=lambda: FakeUow(),
        uuid_factory=lambda: None,
        clock=lambda: None,
    )
    with pytest.raises(ScoringEvaluationNotFound):
        command.execute(request())

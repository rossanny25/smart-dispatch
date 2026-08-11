from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text

from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.application.commands.evaluate_recommendation_confidence import (
    ConfidencePolicyFailure,
    ConfidencePersistenceError,
    EvaluateRecommendationConfidence,
    EvaluateRecommendationConfidenceRequest,
    ScoringEvaluationNotFound,
)
from app.application.commands.score_eligible_technicians import (
    ScoreEligibleTechnicians,
)
from app.migrations.runtime import upgrade_to_head
from tests.integration.test_scoring_persistence import (
    TECH_1,
    _prepare_eligibility,
    _request as scoring_request,
)


NOW = datetime(2026, 7, 28, 12, 5, tzinfo=UTC)


def _prepare_scoring(factory: SqliteUnitOfWorkFactory) -> str:
    eligibility_id = _prepare_eligibility(factory)
    return ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("66666666-6666-4666-8666-666666666666"),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    ).execute(scoring_request(eligibility_id)).evaluation_set_id


def request(scoring_id: str, *, gps_age: int | None = 1, episodes: int = 3):
    return EvaluateRecommendationConfidenceRequest(
        scoring_evaluation_set_id=scoring_id,
        evaluated_at=NOW,
        gps_observations=(
            {
                "technician_id": TECH_1,
                "observed_at": (
                    None
                    if gps_age is None
                    else NOW - timedelta(minutes=gps_age)
                ),
                "last_known_zone": "centro" if gps_age is None else None,
            },
        ),
        traffic_observed_at=NOW - timedelta(minutes=2),
        weather_observed_at=NOW - timedelta(minutes=2),
        active_supporting_episode_count=episodes,
    )


def test_confidence_round_trip_replay_and_changed_evidence(tmp_path: Path) -> None:
    path = tmp_path / "confidence.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    scoring_id = _prepare_scoring(factory)
    identifiers = iter(
        (
            UUID("77777777-7777-4777-8777-777777777777"),
            UUID("88888888-8888-4888-8888-888888888888"),
        )
    )
    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=factory,
        uuid_factory=lambda: next(identifiers),
        clock=lambda: datetime(2026, 7, 28, 12, 6, tzinfo=UTC),
    )
    first = command.execute(request(scoring_id))
    replay = command.execute(request(scoring_id))
    changed = command.execute(request(scoring_id, gps_age=None, episodes=0))

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.evaluation_set_id == first.evaluation_set_id
    assert changed.evaluation_set_id != first.evaluation_set_id
    assert first.output["recommended_technician_id"] == TECH_1
    assert first.output["confidence_label"] in {"low", "medium", "high"}
    assert first.output["scoring_output"]["eligible_candidates"][0]["rank"] == 1
    assert changed.output["confidence_value"] != first.output["confidence_value"]
    with factory._get_engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM confidence_evaluation_sets")
        ).scalar_one() == 2
    factory.dispose()


def test_confidence_corruption_fails_safely(tmp_path: Path) -> None:
    path = tmp_path / "confidence-corrupt.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    scoring_id = _prepare_scoring(factory)
    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("77777777-7777-4777-8777-777777777777"),
        clock=lambda: datetime(2026, 7, 28, 12, 6, tzinfo=UTC),
    )
    result = command.execute(request(scoring_id))
    with factory._get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE confidence_evaluation_sets "
                "SET warning_count = warning_count + 1 WHERE id = :id"
            ),
            {"id": result.evaluation_set_id},
        )
    with pytest.raises(ConfidencePersistenceError):
        command.execute(request(scoring_id))
    factory.dispose()


def test_missing_scoring_and_no_feasible_results_are_safe(tmp_path: Path) -> None:
    path = tmp_path / "confidence-empty.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("77777777-7777-4777-8777-777777777777"),
        clock=lambda: datetime(2026, 7, 28, 12, 6, tzinfo=UTC),
    )
    with pytest.raises(ScoringEvaluationNotFound):
        command.execute(
            request("99999999-9999-4999-8999-999999999999")
        )

    eligibility_id = _prepare_eligibility(
        factory, first_availability="busy"
    )
    scoring_id = ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("66666666-6666-4666-8666-666666666666"),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    ).execute(scoring_request(eligibility_id)).evaluation_set_id
    result = command.execute(
        EvaluateRecommendationConfidenceRequest(
            scoring_evaluation_set_id=scoring_id,
            evaluated_at=NOW,
            gps_observations=(),
            traffic_observed_at=NOW,
            weather_observed_at=NOW,
            active_supporting_episode_count=0,
        )
    )
    assert result.output["recommended_technician_id"] is None
    assert result.output["confidence_value"] is None
    assert result.output["factors"] == []
    assert len(result.output["scoring_output"]["ineligible_candidates"]) == 2
    factory.dispose()


def test_policy_failure_rolls_back_and_preserves_scoring(tmp_path: Path) -> None:
    path = tmp_path / "confidence-rollback.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    scoring_id = _prepare_scoring(factory)
    with factory._get_engine().connect() as connection:
        before = connection.execute(
            text(
                "SELECT input_json, output_json FROM scoring_evaluation_sets "
                "WHERE id = :id"
            ),
            {"id": scoring_id},
        ).one()

    def raising(_):
        raise RuntimeError("private")

    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("77777777-7777-4777-8777-777777777777"),
        clock=lambda: datetime(2026, 7, 28, 12, 6, tzinfo=UTC),
        evaluator=raising,
    )
    with pytest.raises(ConfidencePolicyFailure):
        command.execute(request(scoring_id))
    with factory._get_engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM confidence_evaluation_sets")
        ).scalar_one() == 0
        assert connection.execute(
            text(
                "SELECT count(*) FROM configuration_versions "
                "WHERE version = 'confidence-v1'"
            )
        ).scalar_one() == 0
        after = connection.execute(
            text(
                "SELECT input_json, output_json FROM scoring_evaluation_sets "
                "WHERE id = :id"
            ),
            {"id": scoring_id},
        ).one()
        assert after == before
    factory.dispose()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE confidence_evaluation_sets SET input_hash = '" + ("0" * 64) + "'",
        (
            "UPDATE confidence_evaluation_sets "
            "SET confidence_label = 'high'"
        ),
        (
            "UPDATE confidence_evaluation_sets "
            "SET confidence_value = '99'"
        ),
        (
            "UPDATE confidence_evaluation_sets "
            "SET output_json = json_set(output_json, '$.confidence_label', 'high')"
        ),
        (
            "UPDATE confidence_evaluation_sets "
            "SET source_count = source_count - 1"
        ),
    ],
)
def test_confidence_corruption_matrix_fails_safely(
    tmp_path: Path, statement: str
) -> None:
    path = tmp_path / "confidence-matrix.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    scoring_id = _prepare_scoring(factory)
    command = EvaluateRecommendationConfidence(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("77777777-7777-4777-8777-777777777777"),
        clock=lambda: datetime(2026, 7, 28, 12, 6, tzinfo=UTC),
    )
    command.execute(request(scoring_id))
    with factory._get_engine().begin() as connection:
        connection.execute(text(statement))
    with pytest.raises(ConfidencePersistenceError):
        command.execute(request(scoring_id))
    factory.dispose()

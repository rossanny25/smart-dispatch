from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.confidence.models import (
    ConfidenceCandidate,
    GpsObservation,
    SourceObservation,
)
from app.domain.confidence.policy import ConfidencePolicy, confidence_label
from app.domain.confidence.rules import CONFIDENCE_CONFIGURATION


NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)
TECH_1 = UUID("00000000-0000-0000-0000-000000000001")
TECH_2 = UUID("00000000-0000-0000-0000-000000000002")


def evaluate(
    *,
    first: Decimal = Decimal("90"),
    second: Decimal | None = Decimal("85"),
    gps_age: int | None = 0,
    traffic_age: int | None = 0,
    weather_age: int | None = 0,
    episodes: int = 3,
    last_known_zone: str | None = None,
):
    candidates = [ConfidenceCandidate(TECH_1, 1, first)]
    gps = [GpsObservation(TECH_1, None if gps_age is None else NOW - timedelta(minutes=gps_age), last_known_zone)]
    if second is not None:
        candidates.append(ConfidenceCandidate(TECH_2, 2, second))
        gps.append(GpsObservation(TECH_2, None if gps_age is None else NOW - timedelta(minutes=gps_age), last_known_zone))
    return ConfidencePolicy(CONFIDENCE_CONFIGURATION).evaluate(
        evaluated_at=NOW,
        candidates=tuple(candidates),
        gps_observations=tuple(gps),
        traffic=SourceObservation(
            "traffic",
            None if traffic_age is None else NOW - timedelta(minutes=traffic_age),
        ),
        weather=SourceObservation(
            "weather",
            None if weather_age is None else NOW - timedelta(minutes=weather_age),
        ),
        active_supporting_episode_count=episodes,
    )


def test_calculates_all_factors_independently_from_score() -> None:
    result = evaluate()
    assert tuple(factor.name for factor in result.factors) == (
        "data_quality",
        "historical_evidence",
        "score_margin",
        "condition_certainty",
    )
    assert result.factors[0].value == Decimal("100")
    assert result.factors[1].value == Decimal("30")
    assert result.factors[2].value == Decimal("50")
    assert result.factors[3].value == Decimal("100")
    assert result.value == Decimal("70.00")
    assert result.label == "medium"
    assert result.candidates[0].objective_score == Decimal("90")


@pytest.mark.parametrize(
    ("source", "age", "expected"),
    [
        ("gps", 5, "current"),
        ("gps", 6, "stale"),
        ("gps", 30, "stale"),
        ("gps", 31, "unavailable"),
        ("traffic", 15, "current"),
        ("traffic", 16, "stale"),
        ("traffic", 60, "stale"),
        ("traffic", 61, "unavailable"),
        ("weather", 15, "current"),
        ("weather", 61, "unavailable"),
    ],
)
def test_freshness_boundaries(source: str, age: int, expected: str) -> None:
    kwargs = {f"{source}_age": age}
    result = evaluate(**kwargs)
    evidence = next(item for item in result.sources if item.source == source)
    assert evidence.quality == expected


def test_unavailable_sources_create_low_confidence_and_structured_warnings() -> None:
    result = evaluate(
        first=Decimal("99"),
        second=Decimal("98.9"),
        gps_age=31,
        traffic_age=None,
        weather_age=61,
        episodes=0,
        last_known_zone="north",
    )
    assert result.label == "low"
    assert result.candidates[0].objective_score == Decimal("99")
    assert result.uncertain_conditions == (
        "gps_estimated",
        "historical_evidence_missing",
        "traffic_defaulted",
        "weather_defaulted",
    )
    assert {warning.source for warning in result.warnings} == {
        "gps",
        "traffic",
        "weather",
        "historical_evidence",
    }
    gps_warning = next(w for w in result.warnings if w.source == "gps")
    assert gps_warning.fallback == "last_known_zone:north"
    assert gps_warning.quality == "unavailable"


def test_one_candidate_has_margin_50_and_no_candidates_have_no_confidence() -> None:
    assert evaluate(second=None).factors[2].value == Decimal("50")
    empty = ConfidencePolicy(CONFIDENCE_CONFIGURATION).evaluate(
        evaluated_at=NOW,
        candidates=(),
        gps_observations=(),
        traffic=SourceObservation("traffic", NOW),
        weather=SourceObservation("weather", NOW),
        active_supporting_episode_count=0,
    )
    assert empty.value is None
    assert empty.label is None
    assert empty.factors == ()


def test_rejects_negative_age_and_non_decimal_score() -> None:
    with pytest.raises(ValueError, match="future"):
        evaluate(gps_age=-1)
    with pytest.raises(TypeError, match="Decimal"):
        ConfidencePolicy(CONFIDENCE_CONFIGURATION).evaluate(
            evaluated_at=NOW,
            candidates=(ConfidenceCandidate(TECH_1, 1, 90),),  # type: ignore[arg-type]
            gps_observations=(GpsObservation(TECH_1, NOW, None),),
            traffic=SourceObservation("traffic", NOW),
            weather=SourceObservation("weather", NOW),
            active_supporting_episode_count=0,
        )


@pytest.mark.parametrize(
    ("value", "label"),
    [
        (Decimal("49.999"), "low"),
        (Decimal("50"), "medium"),
        (Decimal("74.999"), "medium"),
        (Decimal("75"), "high"),
    ],
)
def test_label_boundaries(value: Decimal, label: str) -> None:
    assert confidence_label(value, CONFIDENCE_CONFIGURATION) == label


def test_fractional_second_freshness_is_exact_and_types_are_strict() -> None:
    result = ConfidencePolicy(CONFIDENCE_CONFIGURATION).evaluate(
        evaluated_at=NOW,
        candidates=(ConfidenceCandidate(TECH_1, 1, Decimal("90")),),
        gps_observations=(
            GpsObservation(
                TECH_1,
                NOW - timedelta(minutes=5, microseconds=1),
                None,
            ),
        ),
        traffic=SourceObservation("traffic", NOW),
        weather=SourceObservation("weather", NOW),
        active_supporting_episode_count=1,
    )
    gps = result.sources[0]
    assert gps.quality == "stale"
    assert gps.age_minutes == Decimal("5.000000016666666666666666666666667")

    with pytest.raises(TypeError, match="UUID"):
        ConfidencePolicy(CONFIDENCE_CONFIGURATION).evaluate(
            evaluated_at=NOW,
            candidates=(
                ConfidenceCandidate(str(TECH_1), True, Decimal("90")),  # type: ignore[arg-type]
            ),
            gps_observations=(
                GpsObservation(str(TECH_1), NOW, None),  # type: ignore[arg-type]
            ),
            traffic=SourceObservation("traffic", NOW),
            weather=SourceObservation("weather", NOW),
            active_supporting_episode_count=0,
        )


def test_unavailable_gps_fallback_quality_is_explicit() -> None:
    without_zone = evaluate(gps_age=None)
    source = next(item for item in without_zone.sources if item.source == "gps")
    assert source.fallback == "unavailable"
    assert source.fallback_quality == "unavailable"
    with_zone = evaluate(gps_age=None, last_known_zone="north")
    source = next(item for item in with_zone.sources if item.source == "gps")
    assert source.fallback_quality == "estimated"

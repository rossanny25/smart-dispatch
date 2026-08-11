from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from app.domain.scoring.models import ScoringTechnician
from app.domain.scoring.models import ScoreComponent, ScoredTechnician
from app.domain.scoring.policy import ScoringPolicy
from app.domain.scoring.rules import SCORING_CONFIGURATION


TECH_1 = UUID("11111111-1111-4111-8111-111111111111")
TECH_2 = UUID("22222222-2222-4222-8222-222222222222")


def candidate(
    technician_id: UUID = TECH_1,
    *,
    eta: int = 30,
    distance: int = 10_000,
    workload: int = 240,
    quality: Decimal | None = Decimal("4"),
) -> ScoringTechnician:
    return ScoringTechnician(
        technician_id=technician_id,
        eta_minutes=eta,
        distance_meters=distance,
        projected_work_minutes=workload,
        quality_rating_0_to_5=quality,
    )


def test_v1_formulas_expose_exact_decimal_evidence() -> None:
    result = ScoringPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=60,
        technicians=(candidate(distance=60_000),),
    )
    scored = result.candidates[0]
    components = {component.name: component for component in scored.components}

    assert components["sla"].normalized_value == Decimal("50")
    assert components["proximity"].normalized_value == Decimal("0")
    assert components["workload_balance"].normalized_value == Decimal("50")
    assert components["quality"].normalized_value == Decimal("80")
    assert components["memory"].normalized_value == Decimal("50")
    assert components["sla"].weighted_contribution == Decimal("17.50")
    assert scored.penalties[0].amount == Decimal("10")
    assert scored.objective_score == Decimal("30.5")


def test_quality_fallback_memory_neutral_and_distance_boundaries() -> None:
    result = ScoringPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=60,
        technicians=(
            candidate(TECH_1, distance=50_000, quality=None),
            candidate(TECH_2, distance=70_000, quality=Decimal("5")),
        ),
    )
    first = next(item for item in result.candidates if item.technician_id == TECH_1)
    second = next(item for item in result.candidates if item.technician_id == TECH_2)

    assert first.penalties[0].amount == Decimal("0")
    assert second.penalties[0].amount == Decimal("20")
    assert first.warnings[0].code == "SCORING_QUALITY_FALLBACK"
    assert first.components[3].normalized_value == Decimal("50")
    assert all(item.components[4].normalized_value == Decimal("50") for item in result.candidates)


def test_clamps_and_full_tie_break_chain_use_unrounded_values() -> None:
    policy = ScoringPolicy(SCORING_CONFIGURATION)
    clamped = policy.evaluate(
        sla_minutes=1,
        technicians=(candidate(eta=999, distance=1_000_000, workload=4_000),),
    ).candidates[0]
    assert all(
        Decimal("0") <= component.normalized_value <= Decimal("100")
        for component in clamped.components
    )
    assert Decimal("0") <= clamped.objective_score <= Decimal("100")

    tied = policy.evaluate(
        sla_minutes=60,
        technicians=(
            candidate(TECH_2),
            candidate(TECH_1),
        ),
    )
    assert [item.technician_id for item in tied.candidates] == [TECH_1, TECH_2]
    assert [item.rank for item in tied.candidates] == [1, 2]


def test_input_order_does_not_change_domain_result() -> None:
    policy = ScoringPolicy(SCORING_CONFIGURATION)
    left = policy.evaluate(
        sla_minutes=60,
        technicians=(candidate(TECH_1), candidate(TECH_2, eta=20)),
    )
    right = policy.evaluate(
        sla_minutes=60,
        technicians=(candidate(TECH_2, eta=20), candidate(TECH_1)),
    )
    assert left == right


def test_non_terminating_fractions_retain_precision_through_contract() -> None:
    from app.contracts.scoring import ScoringOutputV1

    result = ScoringPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=3,
        technicians=(candidate(eta=1, workload=1),),
    )
    output = ScoringOutputV1.from_domain(
        result,
        ineligible_candidates=[],
    )
    assert output.eligible_candidates[0].components[0].normalized_value == (
        "66.66666666666666666666666666666667"
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"eta_minutes": 1.0},
        {"distance_meters": 1.0},
        {"projected_work_minutes": True},
        {"quality_rating_0_to_5": 4.0},
    ],
)
def test_pure_policy_rejects_binary_float_and_boolean_inputs(changes) -> None:
    values = {
        "technician_id": TECH_1,
        "eta_minutes": 1,
        "distance_meters": 1,
        "projected_work_minutes": 1,
        "quality_rating_0_to_5": Decimal("4"),
    }
    values.update(changes)
    with pytest.raises((TypeError, ValueError)):
        ScoringPolicy(SCORING_CONFIGURATION).evaluate(
            sla_minutes=3,
            technicians=(ScoringTechnician(**values),),
        )


def test_policy_rejects_unsupported_declared_rounding_mode() -> None:
    with pytest.raises(ValueError):
        ScoringPolicy(
            replace(
                SCORING_CONFIGURATION,
                decimal_rounding="ROUND_DOWN",
            )
        )


def test_formula_endpoints_and_distance_growth_are_exact() -> None:
    policy = ScoringPolicy(SCORING_CONFIGURATION)
    zero_inputs = policy.evaluate(
        sla_minutes=60,
        technicians=(
            candidate(
                eta=0,
                distance=0,
                workload=0,
                quality=Decimal("0"),
            ),
        ),
    ).candidates[0]
    assert [item.normalized_value for item in zero_inputs.components[:4]] == [
        Decimal("100"),
        Decimal("100"),
        Decimal("100"),
        Decimal("0"),
    ]

    max_quality = policy.evaluate(
        sla_minutes=60,
        technicians=(candidate(quality=Decimal("5")),),
    ).candidates[0]
    assert max_quality.components[3].normalized_value == Decimal("100")

    just_over = policy.evaluate(
        sla_minutes=60,
        technicians=(candidate(distance=50_001),),
    ).candidates[0]
    capped = policy.evaluate(
        sla_minutes=60,
        technicians=(candidate(distance=80_000),),
    ).candidates[0]
    assert just_over.penalties[0].amount == Decimal("0.001")
    assert capped.penalties[0].amount == Decimal("20")
    assert policy.evaluate(sla_minutes=60, technicians=()).candidates == ()


def _pre_scored(
    technician_id: UUID,
    *,
    score: str,
    sla: str,
    quality: str,
    eta: int,
) -> ScoredTechnician:
    components = tuple(
        ScoreComponent(
            name=name,
            raw_inputs=(),
            normalized_value=Decimal(
                sla if name == "sla" else quality if name == "quality" else "50"
            ),
            weight=SCORING_CONFIGURATION.weight_for(name),
            weighted_contribution=Decimal("0"),
            configuration_version="scoring-v1",
        )
        for name in SCORING_CONFIGURATION.component_order
    )
    return ScoredTechnician(
        technician_id=technician_id,
        rank=0,
        objective_score=Decimal(score),
        components=components,
        penalties=(),
        warnings=(),
        eta_minutes=eta,
    )


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        (
            {"score": "60", "sla": "10", "quality": "10", "eta": 99},
            {"score": "59", "sla": "100", "quality": "100", "eta": 1},
            TECH_1,
        ),
        (
            {"score": "60", "sla": "80", "quality": "10", "eta": 99},
            {"score": "60", "sla": "79", "quality": "100", "eta": 1},
            TECH_1,
        ),
        (
            {"score": "60", "sla": "80", "quality": "90", "eta": 99},
            {"score": "60", "sla": "80", "quality": "89", "eta": 1},
            TECH_1,
        ),
        (
            {"score": "60", "sla": "80", "quality": "90", "eta": 10},
            {"score": "60", "sla": "80", "quality": "90", "eta": 11},
            TECH_1,
        ),
    ],
)
def test_each_ranking_key_precedes_the_next(left, right, expected) -> None:
    class RankingPolicy(ScoringPolicy):
        def _score(self, technician, sla_minutes):
            values = left if technician.technician_id == TECH_1 else right
            return _pre_scored(technician.technician_id, **values)

    result = RankingPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=1,
        technicians=(candidate(TECH_2), candidate(TECH_1)),
    )
    assert result.candidates[0].technician_id == expected

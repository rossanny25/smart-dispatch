from dataclasses import FrozenInstanceError
from decimal import Decimal, getcontext

import pytest

from app.domain.scoring.policy import ScoringPolicy
from app.domain.scoring.rules import (
    SCORING_CONFIGURATION,
    SCORING_REGISTRY_JSON,
    SCORING_REGISTRY_SHA256,
)


def test_scoring_registry_is_complete_hashed_and_immutable() -> None:
    assert len(SCORING_REGISTRY_SHA256) == 64
    for token in (
        "objective_score",
        "distance_penalty",
        "quality",
        "memory",
        "tie_break_order",
        "decimal_precision",
        "warning_template",
        "unknown_penalties",
        "clamp",
        "bounds",
        "operands",
        "operators",
        "decimal_text_max_length",
        "Subtracted from the weighted component total.",
    ):
        assert token in SCORING_REGISTRY_JSON
    with pytest.raises(FrozenInstanceError):
        SCORING_CONFIGURATION.maximum_workday_hours = Decimal("9")


def test_policy_does_not_mutate_process_decimal_context() -> None:
    before = getcontext().copy()
    ScoringPolicy(SCORING_CONFIGURATION).evaluate(
        sla_minutes=60,
        technicians=(),
    )
    after = getcontext()
    assert after.prec == before.prec
    assert after.rounding == before.rounding
    assert after.traps == before.traps

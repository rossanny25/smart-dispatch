from dataclasses import FrozenInstanceError
import hashlib

import pytest

from app.contracts.eligibility import EligibilityInputV1
from app.domain.eligibility.rules import (
    ELIGIBILITY_CONFIGURATION,
    ELIGIBILITY_REGISTRY_JSON,
    ELIGIBILITY_REGISTRY_SHA256,
)


def test_eligibility_registry_digest_and_configuration_are_immutable() -> None:
    assert hashlib.sha256(
        ELIGIBILITY_REGISTRY_JSON.encode("utf-8")
    ).hexdigest() == ELIGIBILITY_REGISTRY_SHA256
    assert isinstance(ELIGIBILITY_CONFIGURATION.check_order, tuple)
    with pytest.raises(FrozenInstanceError):
        ELIGIBILITY_CONFIGURATION.maximum_workday_minutes = 999  # type: ignore[misc]


def test_policy_boundary_has_no_scoring_or_recommendation_fields() -> None:
    schema = EligibilityInputV1.model_json_schema()
    serialized = str(schema).lower()

    assert "score" not in serialized
    assert "rank" not in serialized
    assert "recommendation" not in serialized
    assert "confidence" not in serialized
    assert "memory" not in serialized

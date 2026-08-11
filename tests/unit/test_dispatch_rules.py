import pytest

from app.domain.dispatch.rules import assert_transition


def test_dispatch_state_machine_accepts_only_the_auditable_path() -> None:
    for previous, following in (
        (None, "CAPTURE"),
        ("CAPTURE", "ANALYZE"),
        ("ANALYZE", "PLAN"),
        ("PLAN", "EVALUATE"),
        ("EVALUATE", "WAIT_FOR_DECISION"),
        ("EVALUATE", "NO_FEASIBLE_CANDIDATES"),
    ):
        assert_transition(previous, following)

    with pytest.raises(ValueError):
        assert_transition("CAPTURE", "PLAN")
    with pytest.raises(ValueError):
        assert_transition("WAIT_FOR_DECISION", "EVALUATE")

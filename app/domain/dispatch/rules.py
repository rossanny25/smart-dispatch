import hashlib
from types import MappingProxyType
from typing import Final

from app.domain.analysis.rules import ANALYSIS_REGISTRY_SHA256
from app.domain.confidence.rules import CONFIDENCE_REGISTRY_SHA256
from app.domain.eligibility.rules import ELIGIBILITY_REGISTRY_SHA256
from app.domain.scoring.rules import SCORING_REGISTRY_SHA256, canonical_json


DISPATCH_CONFIGURATION_VERSION: Final = "dispatch-v1"
DISPATCH_CONTRACT_VERSION: Final = "v1"
STAGE_ORDER: Final = ("CAPTURE", "ANALYZE", "PLAN", "EVALUATE")
TERMINAL_STATES: Final = (
    "WAIT_FOR_DECISION",
    "NO_FEASIBLE_CANDIDATES",
    "FAILED",
)
ALLOWED_TRANSITIONS: Final = MappingProxyType({
    None: ("CAPTURE",),
    "CAPTURE": ("ANALYZE", "FAILED"),
    "ANALYZE": ("PLAN", "FAILED"),
    "PLAN": ("EVALUATE", "FAILED"),
    "EVALUATE": (
        "WAIT_FOR_DECISION",
        "NO_FEASIBLE_CANDIDATES",
        "FAILED",
    ),
})

DISPATCH_REGISTRY: Final = MappingProxyType(
    {
        "version": DISPATCH_CONFIGURATION_VERSION,
        "contract_version": DISPATCH_CONTRACT_VERSION,
        "stage_order": STAGE_ORDER,
        "terminal_states": TERMINAL_STATES,
        "transitions": tuple(
            (
                "START" if source is None else source,
                tuple(targets),
            )
            for source, targets in ALLOWED_TRANSITIONS.items()
        ),
        "component_digests": (
            ("analysis-v1", ANALYSIS_REGISTRY_SHA256),
            ("eligibility-v1", ELIGIBILITY_REGISTRY_SHA256),
            ("scoring-v1", SCORING_REGISTRY_SHA256),
            ("confidence-v1", CONFIDENCE_REGISTRY_SHA256),
        ),
        "memory_experiment_mode": "disabled",
        "traffic_fallback": "seeded-normal",
        "weather_fallback": "seeded-clear",
        "evidence_rules": (
            "successful_stage_requires_output_and_no_error",
            "failed_stage_requires_no_output_and_typed_safe_error",
            "all_stage_inputs_reference_authoritative_run_snapshot",
            "evaluate_scoring_must_equal_plan_scoring",
        ),
        "serialization": (
            "canonical-json-utf8-sort-keys-no-nan",
            "decimal-canonical-unrounded-string",
        ),
        "duration": "integer-monotonic-elapsed-milliseconds",
        "terminal_consistency": (
            "wait-for-decision-requires-rank-one-recommendation",
            "no-feasible-requires-zero-eligible-and-no-recommendation",
            "failed-requires-final-failed-execution",
        ),
        "bounds": (
            "technicians:1..100",
            "attempt:1",
            "active-supporting-episodes:0..10000",
        ),
        "presentation_rounding": "ROUND_HALF_UP:2-only-at-display-boundary",
    }
)
DISPATCH_REGISTRY_JSON: Final = canonical_json(dict(DISPATCH_REGISTRY))
DISPATCH_REGISTRY_SHA256: Final = hashlib.sha256(
    DISPATCH_REGISTRY_JSON.encode()
).hexdigest()


def assert_transition(previous: str | None, following: str) -> None:
    if following not in ALLOWED_TRANSITIONS.get(previous, ()):
        raise ValueError(f"invalid dispatch transition: {previous!r} -> {following!r}")

from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib

from app.domain.scoring.rules import canonical_decimal, canonical_json


CONFIDENCE_CONFIGURATION_VERSION = "confidence-v1"
CONFIDENCE_CONTRACT_VERSION = "v1"
CONFIDENCE_CONFIGURATION_CREATED_AT = "2026-07-28T00:00:00Z"
FACTOR_ORDER = (
    "data_quality",
    "historical_evidence",
    "score_margin",
    "condition_certainty",
)
SOURCE_ORDER = ("gps", "traffic", "weather", "historical_evidence")


@dataclass(frozen=True)
class WarningRule:
    source: str
    code_prefix: str
    affected_field: str
    impact: str
    unavailable_fallback: str


@dataclass(frozen=True)
class ConfidenceConfiguration:
    version: str
    contract_version: str
    factor_order: tuple[str, ...]
    weights: tuple[tuple[str, Decimal], ...]
    source_order: tuple[str, ...]
    quality_values: tuple[tuple[str, Decimal], ...]
    gps_current_max_minutes: Decimal
    gps_stale_max_minutes: Decimal
    environment_current_max_minutes: Decimal
    environment_stale_max_minutes: Decimal
    historical_multiplier: Decimal
    historical_cap: Decimal
    single_candidate_margin: Decimal
    margin_multiplier: Decimal
    margin_cap: Decimal
    uncertain_condition_deduction: Decimal
    clamp_minimum: Decimal
    clamp_maximum: Decimal
    decimal_precision: int
    decimal_rounding: str
    low_upper_exclusive: Decimal
    medium_upper_exclusive: Decimal
    traffic_default: str
    weather_default: str
    warning_rules: tuple[WarningRule, ...]
    explanation_templates: tuple[tuple[str, tuple[str, ...]], ...]
    maximum_candidate_count: int
    maximum_episode_count: int
    maximum_text_length: int

    def weight_for(self, name: str) -> Decimal:
        return dict(self.weights)[name]

    def quality_value(self, name: str) -> Decimal:
        return dict(self.quality_values)[name]

    def warning_rule(self, source: str) -> WarningRule:
        return next(item for item in self.warning_rules if item.source == source)


CONFIDENCE_CONFIGURATION = ConfidenceConfiguration(
    version=CONFIDENCE_CONFIGURATION_VERSION,
    contract_version=CONFIDENCE_CONTRACT_VERSION,
    factor_order=FACTOR_ORDER,
    weights=(
        ("data_quality", Decimal("0.35")),
        ("historical_evidence", Decimal("0.25")),
        ("score_margin", Decimal("0.25")),
        ("condition_certainty", Decimal("0.15")),
    ),
    source_order=SOURCE_ORDER,
    quality_values=(
        ("current", Decimal("100")),
        ("stale", Decimal("75")),
        ("unavailable", Decimal("50")),
    ),
    gps_current_max_minutes=Decimal("5"),
    gps_stale_max_minutes=Decimal("30"),
    environment_current_max_minutes=Decimal("15"),
    environment_stale_max_minutes=Decimal("60"),
    historical_multiplier=Decimal("10"),
    historical_cap=Decimal("100"),
    single_candidate_margin=Decimal("50"),
    margin_multiplier=Decimal("10"),
    margin_cap=Decimal("100"),
    uncertain_condition_deduction=Decimal("25"),
    clamp_minimum=Decimal("0"),
    clamp_maximum=Decimal("100"),
    decimal_precision=34,
    decimal_rounding="ROUND_HALF_EVEN",
    low_upper_exclusive=Decimal("50"),
    medium_upper_exclusive=Decimal("75"),
    traffic_default="seeded-normal",
    weather_default="seeded-clear",
    warning_rules=(
        WarningRule(
            "gps",
            "CONFIDENCE_GPS",
            "technician.location",
            "Location evidence limits recommendation certainty.",
            "unavailable",
        ),
        WarningRule(
            "traffic",
            "CONFIDENCE_TRAFFIC",
            "environment.traffic",
            "Default traffic may change estimated arrival conditions.",
            "seeded-normal",
        ),
        WarningRule(
            "weather",
            "CONFIDENCE_WEATHER",
            "environment.weather",
            "Default weather may change operating conditions.",
            "seeded-clear",
        ),
        WarningRule(
            "historical_evidence",
            "CONFIDENCE_HISTORICAL_EVIDENCE",
            "history.active_supporting_episode_count",
            "Limited history reduces recommendation confidence.",
            "no_history",
        ),
    ),
    explanation_templates=(
        (
            "CONFIDENCE_SUMMARY",
            (
                "leading_technician_id",
                "leading_objective_score",
                "confidence_value",
                "confidence_label",
                "first_score",
                "second_score",
                "limiting_factors",
                "warning_codes",
            ),
        ),
        (
            "CONFIDENCE_UNAVAILABLE_NO_ELIGIBLE_CANDIDATE",
            (
                "leading_technician_id",
                "confidence_value",
                "confidence_label",
            ),
        ),
    ),
    maximum_candidate_count=100,
    maximum_episode_count=10_000,
    maximum_text_length=80,
)


def _registry_snapshot() -> dict[str, object]:
    raw = asdict(CONFIDENCE_CONFIGURATION)
    raw["weights"] = {
        key: canonical_decimal(value)
        for key, value in CONFIDENCE_CONFIGURATION.weights
    }
    raw["quality_values"] = {
        key: canonical_decimal(value)
        for key, value in CONFIDENCE_CONFIGURATION.quality_values
    }
    for name in (
        "gps_current_max_minutes",
        "gps_stale_max_minutes",
        "environment_current_max_minutes",
        "environment_stale_max_minutes",
        "historical_multiplier",
        "historical_cap",
        "single_candidate_margin",
        "margin_multiplier",
        "margin_cap",
        "uncertain_condition_deduction",
        "clamp_minimum",
        "clamp_maximum",
        "low_upper_exclusive",
        "medium_upper_exclusive",
    ):
        raw[name] = canonical_decimal(getattr(CONFIDENCE_CONFIGURATION, name))
    return {
        "configuration": raw,
        "formulas": {
            "data_quality": "mean(applicable_source_quality)",
            "historical_evidence": "min(100,10*active_supporting_episode_count)",
            "score_margin": "min(100,10*(first_score-second_score)); one=50",
            "condition_certainty": "clamp(100-25*uncertain_condition_count)",
            "confidence": (
                "clamp(.35*data_quality+.25*historical_evidence+"
                ".25*score_margin+.15*condition_certainty)"
            ),
        },
        "freshness_boundaries": {
            "current_upper_inclusive": True,
            "stale_upper_inclusive": True,
        },
        "uncertain_conditions": [
            "gps_estimated",
            "historical_evidence_missing",
            "traffic_defaulted",
            "weather_defaulted",
        ],
        "warning_rules": [asdict(item) for item in CONFIDENCE_CONFIGURATION.warning_rules],
        "warning_order": list(SOURCE_ORDER),
        "explanation_templates": {
            name: list(parameters)
            for name, parameters in CONFIDENCE_CONFIGURATION.explanation_templates
        },
        "serialization": "canonical-json-decimal-strings",
    }


CONFIDENCE_REGISTRY_JSON = canonical_json(_registry_snapshot())
CONFIDENCE_REGISTRY_SHA256 = hashlib.sha256(
    CONFIDENCE_REGISTRY_JSON.encode("utf-8")
).hexdigest()

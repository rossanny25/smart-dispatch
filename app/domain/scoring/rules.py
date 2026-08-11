from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import json
from types import MappingProxyType


SCORING_CONFIGURATION_VERSION = "scoring-v1"
SCORING_CONTRACT_VERSION = "v1"
SCORING_CONFIGURATION_CREATED_AT = "2026-07-28T00:00:00Z"
COMPONENT_ORDER = ("sla", "proximity", "workload_balance", "quality", "memory")
PENALTY_ORDER = ("distance_penalty",)


@dataclass(frozen=True)
class ScoringConfiguration:
    version: str
    contract_version: str
    component_order: tuple[str, ...]
    penalty_order: tuple[str, ...]
    weights: tuple[tuple[str, Decimal], ...]
    maximum_workday_hours: Decimal
    neutral_quality: Decimal
    neutral_memory: Decimal
    distance_penalty_threshold_km: Decimal
    distance_penalty_cap: Decimal
    decimal_precision: int
    decimal_rounding: str
    tie_break_order: tuple[str, ...]
    clamp_minimum: Decimal
    clamp_maximum: Decimal
    distance_meters_per_km: Decimal
    minutes_per_hour: Decimal
    proximity_points_per_km: Decimal
    quality_points_per_rating: Decimal
    sla_minutes_minimum: int
    sla_minutes_maximum: int
    eta_minutes_minimum: int
    eta_minutes_maximum: int
    distance_meters_minimum: int
    distance_meters_maximum: int
    projected_work_minutes_minimum: int
    projected_work_minutes_maximum: int
    quality_rating_minimum: Decimal
    quality_rating_maximum: Decimal
    maximum_decimal_text_length: int
    memory_active_applicable_effect_count: int
    distance_penalty_impact: str

    def weight_for(self, component: str) -> Decimal:
        return dict(self.weights)[component]


SCORING_CONFIGURATION = ScoringConfiguration(
    version=SCORING_CONFIGURATION_VERSION,
    contract_version=SCORING_CONTRACT_VERSION,
    component_order=COMPONENT_ORDER,
    penalty_order=PENALTY_ORDER,
    weights=(
        ("sla", Decimal("0.35")),
        ("proximity", Decimal("0.25")),
        ("workload_balance", Decimal("0.20")),
        ("quality", Decimal("0.10")),
        ("memory", Decimal("0.10")),
    ),
    maximum_workday_hours=Decimal("8"),
    neutral_quality=Decimal("50"),
    neutral_memory=Decimal("50"),
    distance_penalty_threshold_km=Decimal("50"),
    distance_penalty_cap=Decimal("20"),
    decimal_precision=34,
    decimal_rounding="ROUND_HALF_EVEN",
    tie_break_order=(
        "objective_score_desc",
        "sla_desc",
        "quality_desc",
        "eta_minutes_asc",
        "technician_uuid_asc",
    ),
    clamp_minimum=Decimal("0"),
    clamp_maximum=Decimal("100"),
    distance_meters_per_km=Decimal("1000"),
    minutes_per_hour=Decimal("60"),
    proximity_points_per_km=Decimal("2"),
    quality_points_per_rating=Decimal("20"),
    sla_minutes_minimum=1,
    sla_minutes_maximum=10080,
    eta_minutes_minimum=0,
    eta_minutes_maximum=1440,
    distance_meters_minimum=0,
    distance_meters_maximum=1_000_000,
    projected_work_minutes_minimum=0,
    projected_work_minutes_maximum=4320,
    quality_rating_minimum=Decimal("0"),
    quality_rating_maximum=Decimal("5"),
    maximum_decimal_text_length=80,
    memory_active_applicable_effect_count=0,
    distance_penalty_impact=(
        "Subtracted from the weighted component total."
    ),
)

QUALITY_WARNING = MappingProxyType(
    {
        "code": "SCORING_QUALITY_FALLBACK",
        "severity": "warning",
        "source": "technician.quality_rating_0_to_5",
        "quality": "unavailable",
        "freshness": "not_applicable",
        "fallback": "50",
        "impact": (
            "Quality evidence is unavailable; the neutral value 50 affects "
            "the Objective Score."
        ),
    }
)


def canonical_decimal(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError("decimal must be finite")
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _registry_snapshot() -> dict[str, object]:
    configuration = asdict(SCORING_CONFIGURATION)
    configuration["weights"] = {
        name: canonical_decimal(weight)
        for name, weight in SCORING_CONFIGURATION.weights
    }
    for name in (
        "maximum_workday_hours",
        "neutral_quality",
        "neutral_memory",
        "distance_penalty_threshold_km",
        "distance_penalty_cap",
        "clamp_minimum",
        "clamp_maximum",
        "distance_meters_per_km",
        "minutes_per_hour",
        "proximity_points_per_km",
        "quality_points_per_rating",
        "quality_rating_minimum",
        "quality_rating_maximum",
    ):
        configuration[name] = canonical_decimal(
            getattr(SCORING_CONFIGURATION, name)
        )
    return {
        "configuration": configuration,
        "formulas": {
            "sla": {
                "expression": "clamp(100*(1-eta_minutes/sla_minutes))",
                "operands": ["100", "eta_minutes", "sla_minutes"],
                "operators": ["divide", "subtract", "multiply", "clamp"],
            },
            "proximity": {
                "expression": "clamp(100-2*distance_km)",
                "operands": ["100", "2", "distance_meters", "1000"],
                "operators": ["divide", "multiply", "subtract", "clamp"],
            },
            "workload_balance": {
                "expression": (
                    "clamp(100*(1-(projected_work_minutes/60)/8))"
                ),
                "operands": [
                    "100",
                    "projected_work_minutes",
                    "60",
                    "8",
                ],
                "operators": [
                    "divide",
                    "divide",
                    "subtract",
                    "multiply",
                    "clamp",
                ],
            },
            "quality": {
                "expression": "clamp(20*rating_0_to_5); missing=50",
                "operands": ["20", "rating_0_to_5", "50"],
                "operators": ["multiply", "clamp", "fallback"],
            },
            "memory": {
                "expression": (
                    "clamp(50+sum(active_applicable_effects)); v1 sum=empty"
                ),
                "operands": ["50", "active_applicable_effects"],
                "operators": ["sum", "add", "clamp"],
            },
            "distance_penalty": {
                "expression": "min(20,max(0,distance_km-50))",
                "operands": ["20", "0", "distance_km", "50"],
                "operators": ["subtract", "max", "min"],
            },
            "objective_score": {
                "expression": (
                    "clamp(sum(component*weight)-distance_penalty)"
                ),
                "operands": [
                    "component_values",
                    "weights",
                    "distance_penalty",
                ],
                "operators": [
                    "multiply",
                    "sum",
                    "subtract",
                    "clamp",
                ],
            },
        },
        "raw_evidence": {
            "sla": ["eta_minutes", "sla_minutes"],
            "proximity": ["distance_meters", "distance_km"],
            "workload_balance": [
                "projected_work_minutes",
                "projected_work_hours",
                "maximum_workday_hours",
            ],
            "quality": ["quality_rating_0_to_5", "fallback_used"],
            "memory": ["active_applicable_effect_count"],
            "distance_penalty": [
                "distance_km",
                "threshold_km",
                "cap",
            ],
        },
        "warning_template": dict(QUALITY_WARNING),
        "penalties": {
            "distance_penalty": {
                "version": SCORING_CONFIGURATION.version,
                "impact": SCORING_CONFIGURATION.distance_penalty_impact,
                "threshold_km": canonical_decimal(
                    SCORING_CONFIGURATION.distance_penalty_threshold_km
                ),
                "cap": canonical_decimal(
                    SCORING_CONFIGURATION.distance_penalty_cap
                ),
            }
        },
        "clamp": {
            "definition": "min(maximum,max(minimum,x))",
            "minimum": canonical_decimal(
                SCORING_CONFIGURATION.clamp_minimum
            ),
            "maximum": canonical_decimal(
                SCORING_CONFIGURATION.clamp_maximum
            ),
        },
        "bounds": {
            "sla_minutes": [
                SCORING_CONFIGURATION.sla_minutes_minimum,
                SCORING_CONFIGURATION.sla_minutes_maximum,
            ],
            "eta_minutes": [
                SCORING_CONFIGURATION.eta_minutes_minimum,
                SCORING_CONFIGURATION.eta_minutes_maximum,
            ],
            "distance_meters": [
                SCORING_CONFIGURATION.distance_meters_minimum,
                SCORING_CONFIGURATION.distance_meters_maximum,
            ],
            "projected_work_minutes": [
                SCORING_CONFIGURATION.projected_work_minutes_minimum,
                SCORING_CONFIGURATION.projected_work_minutes_maximum,
            ],
            "quality_rating": [
                canonical_decimal(
                    SCORING_CONFIGURATION.quality_rating_minimum
                ),
                canonical_decimal(
                    SCORING_CONFIGURATION.quality_rating_maximum
                ),
            ],
            "decimal_text_max_length": (
                SCORING_CONFIGURATION.maximum_decimal_text_length
            ),
        },
        "serialization": (
            "finite canonical non-exponent decimal strings; no negative zero"
        ),
        "unknown_penalties": "forbidden; new penalty requires new version",
        "ineligible_rule": "never scored; retained eligibility evidence only",
    }


SCORING_REGISTRY_JSON = canonical_json(_registry_snapshot())
SCORING_REGISTRY_SHA256 = hashlib.sha256(
    SCORING_REGISTRY_JSON.encode("utf-8")
).hexdigest()

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, StrictInt, StrictStr, field_validator, model_validator

from app.contracts.common import StrictContract
from app.contracts.scoring import ScoringOutputV1
from app.domain.confidence.models import (
    ConfidenceCandidate,
    ConfidenceResult,
    GpsObservation,
    SourceObservation,
)
from app.domain.confidence.policy import ConfidencePolicy
from app.domain.confidence.rules import (
    CONFIDENCE_CONFIGURATION,
    FACTOR_ORDER,
)
from app.domain.scoring.rules import canonical_decimal
from app.domain.scoring.rules import canonical_json


DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _decimal_text(value):
    if not isinstance(value, str) or DECIMAL_PATTERN.fullmatch(value) is None:
        raise ValueError("decimal values must be canonical strings")
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("invalid decimal") from error
    if canonical_decimal(parsed) != value:
        raise ValueError("decimal value is not canonical")
    return value


def _canonical_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    if value.isoformat().replace("+00:00", "Z").endswith("Z") is False:
        raise ValueError("timestamp must be canonical UTC")
    return value


class FrozenConfidenceContract(StrictContract):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def _parse_uuid(value):
    return UUID(value) if isinstance(value, str) else value


def _parse_datetime(value):
    if isinstance(value, str):
        if not value.endswith("Z"):
            raise ValueError("timestamp must use canonical UTC Z form")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class GpsObservationV1(FrozenConfidenceContract):
    technician_id: UUID
    observed_at: datetime | None
    last_known_zone: Annotated[StrictStr, Field(min_length=1, max_length=80)] | None

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _parse_time = field_validator("observed_at", mode="before")(_parse_datetime)
    _utc = field_validator("observed_at")(_canonical_utc)


class EnvironmentObservationV1(FrozenConfidenceContract):
    observed_at: datetime | None
    default_fallback: Annotated[StrictStr, Field(min_length=1, max_length=80)]

    _parse_time = field_validator("observed_at", mode="before")(_parse_datetime)
    _utc = field_validator("observed_at")(_canonical_utc)


class ConfidenceCandidateV1(FrozenConfidenceContract):
    technician_id: UUID
    rank: Annotated[StrictInt, Field(ge=1, le=100)]
    objective_score: StrictStr

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _score = field_validator("objective_score")(_decimal_text)


class ConfidenceInputV1(FrozenConfidenceContract):
    schema_version: Literal["v1"]
    configuration_version: Literal["confidence-v1"]
    scoring_evaluation_set_id: UUID
    scoring_output_sha256: Annotated[
        StrictStr, Field(pattern=r"^[0-9a-f]{64}$")
    ]
    evaluated_at: datetime
    candidates: Annotated[
        tuple[ConfidenceCandidateV1, ...], Field(max_length=100)
    ]
    gps_observations: Annotated[tuple[GpsObservationV1, ...], Field(max_length=100)]
    traffic: EnvironmentObservationV1
    weather: EnvironmentObservationV1
    active_supporting_episode_count: Annotated[
        StrictInt, Field(ge=0, le=10_000)
    ]

    _uuid = field_validator("scoring_evaluation_set_id", mode="before")(_parse_uuid)
    _parse_time = field_validator("evaluated_at", mode="before")(_parse_datetime)
    _evaluated_utc = field_validator("evaluated_at")(_canonical_utc)

    @model_validator(mode="after")
    def validate_evidence(self) -> "ConfidenceInputV1":
        identifiers = tuple(item.technician_id for item in self.gps_observations)
        candidate_ids = tuple(item.technician_id for item in self.candidates)
        if tuple(item.rank for item in self.candidates) != tuple(
            range(1, len(self.candidates) + 1)
        ):
            raise ValueError("candidate ranks must be consecutive")
        if identifiers != candidate_ids:
            raise ValueError("GPS roster must match ranked candidates")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("GPS observations must be unique")
        if self.traffic.default_fallback != CONFIDENCE_CONFIGURATION.traffic_default:
            raise ValueError("traffic fallback must match confidence-v1")
        if self.weather.default_fallback != CONFIDENCE_CONFIGURATION.weather_default:
            raise ValueError("weather fallback must match confidence-v1")
        for item in (*self.gps_observations, self.traffic, self.weather):
            if item.observed_at is not None and item.observed_at > self.evaluated_at:
                raise ValueError("source timestamp cannot be in the future")
        return self

    def to_domain_candidates(self) -> tuple[ConfidenceCandidate, ...]:
        return tuple(
            ConfidenceCandidate(
                technician_id=item.technician_id,
                rank=item.rank,
                objective_score=Decimal(item.objective_score),
            )
            for item in self.candidates
        )


class RawInputV1(FrozenConfidenceContract):
    name: StrictStr
    value: StrictStr


class ConfidenceFactorV1(FrozenConfidenceContract):
    name: Literal[
        "data_quality",
        "historical_evidence",
        "score_margin",
        "condition_certainty",
    ]
    raw_inputs: tuple[RawInputV1, ...]
    value: StrictStr
    weight: StrictStr
    weighted_contribution: StrictStr
    configuration_version: Literal["confidence-v1"]

    _values = field_validator(
        "value", "weight", "weighted_contribution"
    )(_decimal_text)


class SourceQualityV1(FrozenConfidenceContract):
    source: Literal["gps", "traffic", "weather", "historical_evidence"]
    technician_id: UUID | None
    affected_field: StrictStr
    observed_at: datetime | None
    age_minutes: StrictStr | None
    quality: Literal["current", "stale", "unavailable"]
    value: StrictStr
    fallback: StrictStr
    fallback_quality: Literal[
        "not_applicable", "estimated", "defaulted", "unavailable"
    ]

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _parse_time = field_validator("observed_at", mode="before")(_parse_datetime)
    _utc = field_validator("observed_at")(_canonical_utc)
    _age = field_validator("age_minutes")(
        lambda value: None if value is None else _decimal_text(value)
    )
    _value = field_validator("value")(_decimal_text)


class ConfidenceWarningV1(FrozenConfidenceContract):
    code: StrictStr
    severity: Literal["warning"]
    source: Literal["gps", "traffic", "weather", "historical_evidence"]
    affected_field: StrictStr
    quality: Literal["stale", "unavailable"]
    freshness: Literal["stale", "unavailable"]
    age_minutes: StrictStr | None
    fallback: StrictStr
    fallback_quality: Literal[
        "not_applicable", "estimated", "defaulted", "unavailable"
    ]
    impact: StrictStr
    technician_id: UUID | None
    configuration_version: Literal["confidence-v1"]

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _age = field_validator("age_minutes")(
        lambda value: None if value is None else _decimal_text(value)
    )


class ConfidenceExplanationV1(FrozenConfidenceContract):
    template_id: Literal[
        "CONFIDENCE_SUMMARY",
        "CONFIDENCE_UNAVAILABLE_NO_ELIGIBLE_CANDIDATE",
    ]
    leading_technician_id: UUID | None
    leading_objective_score: StrictStr | None
    confidence_value: StrictStr | None
    confidence_label: Literal["low", "medium", "high"] | None
    first_score: StrictStr | None
    second_score: StrictStr | None
    limiting_factors: tuple[
        Literal[
            "data_quality",
            "historical_evidence",
            "score_margin",
            "condition_certainty",
        ],
        ...,
    ]
    warning_codes: tuple[StrictStr, ...]

    _uuid = field_validator("leading_technician_id", mode="before")(_parse_uuid)
    _decimals = field_validator(
        "leading_objective_score",
        "confidence_value",
        "first_score",
        "second_score",
    )(lambda value: None if value is None else _decimal_text(value))


class ConfidenceOutputV1(FrozenConfidenceContract):
    schema_version: Literal["v1"]
    configuration_version: Literal["confidence-v1"]
    scoring_output: ScoringOutputV1
    recommended_technician_id: UUID | None
    factors: tuple[ConfidenceFactorV1, ...]
    sources: tuple[SourceQualityV1, ...]
    uncertain_conditions: tuple[
        Literal[
            "gps_estimated",
            "historical_evidence_missing",
            "traffic_defaulted",
            "weather_defaulted",
        ],
        ...,
    ]
    warnings: tuple[ConfidenceWarningV1, ...]
    confidence_value: StrictStr | None
    confidence_label: Literal["low", "medium", "high"] | None
    explanation: ConfidenceExplanationV1

    _uuid = field_validator(
        "recommended_technician_id", mode="before"
    )(_parse_uuid)
    _confidence = field_validator("confidence_value")(
        lambda value: None if value is None else _decimal_text(value)
    )

    @classmethod
    def from_domain(
        cls,
        result: ConfidenceResult,
        scoring_output: ScoringOutputV1,
    ) -> "ConfidenceOutputV1":
        def raw(items):
            return tuple({"name": name, "value": value} for name, value in items)

        return cls.model_validate(
            {
                "schema_version": result.schema_version,
                "configuration_version": result.configuration_version,
                "scoring_output": scoring_output,
                "recommended_technician_id": (
                    None
                    if result.recommended_technician_id is None
                    else str(result.recommended_technician_id)
                ),
                "factors": tuple(
                    {
                        "name": item.name,
                        "raw_inputs": raw(item.raw_inputs),
                        "value": canonical_decimal(item.value),
                        "weight": canonical_decimal(item.weight),
                        "weighted_contribution": canonical_decimal(
                            item.weighted_contribution
                        ),
                        "configuration_version": item.configuration_version,
                    }
                    for item in result.factors
                ),
                "sources": tuple(
                    {
                        "source": item.source,
                        "technician_id": (
                            None
                            if item.technician_id is None
                            else str(item.technician_id)
                        ),
                        "affected_field": item.affected_field,
                        "observed_at": item.observed_at,
                        "age_minutes": (
                            None
                            if item.age_minutes is None
                            else canonical_decimal(item.age_minutes)
                        ),
                        "quality": item.quality,
                        "value": canonical_decimal(item.value),
                        "fallback": item.fallback,
                        "fallback_quality": item.fallback_quality,
                    }
                    for item in result.sources
                ),
                "uncertain_conditions": result.uncertain_conditions,
                "warnings": tuple(
                    {
                        "code": item.code,
                        "severity": item.severity,
                        "source": item.source,
                        "affected_field": item.affected_field,
                        "quality": item.quality,
                        "freshness": item.freshness,
                        "age_minutes": (
                            None
                            if item.age_minutes is None
                            else canonical_decimal(item.age_minutes)
                        ),
                        "fallback": item.fallback,
                        "fallback_quality": item.fallback_quality,
                        "impact": item.impact,
                        "technician_id": (
                            None
                            if item.technician_id is None
                            else str(item.technician_id)
                        ),
                        "configuration_version": item.configuration_version,
                    }
                    for item in result.warnings
                ),
                "confidence_value": (
                    None if result.value is None else canonical_decimal(result.value)
                ),
                "confidence_label": result.label,
                "explanation": {
                    "template_id": result.explanation.template_id,
                    "leading_technician_id": (
                        None
                        if result.explanation.leading_technician_id is None
                        else str(result.explanation.leading_technician_id)
                    ),
                    "leading_objective_score": (
                        None
                        if result.explanation.leading_objective_score is None
                        else canonical_decimal(
                            result.explanation.leading_objective_score
                        )
                    ),
                    "confidence_value": (
                        None
                        if result.explanation.confidence_value is None
                        else canonical_decimal(result.explanation.confidence_value)
                    ),
                    "confidence_label": result.explanation.confidence_label,
                    "first_score": (
                        None
                        if result.explanation.first_score is None
                        else canonical_decimal(result.explanation.first_score)
                    ),
                    "second_score": (
                        None
                        if result.explanation.second_score is None
                        else canonical_decimal(result.explanation.second_score)
                    ),
                    "limiting_factors": result.explanation.limiting_factors,
                    "warning_codes": result.explanation.warning_codes,
                },
            }
        )


def evaluate_input(input_model: ConfidenceInputV1) -> ConfidenceResult:
    return ConfidencePolicy(CONFIDENCE_CONFIGURATION).evaluate(
        evaluated_at=input_model.evaluated_at,
        candidates=input_model.to_domain_candidates(),
        gps_observations=tuple(
            GpsObservation(
                technician_id=item.technician_id,
                observed_at=item.observed_at,
                last_known_zone=item.last_known_zone,
            )
            for item in input_model.gps_observations
        ),
        traffic=SourceObservation("traffic", input_model.traffic.observed_at),
        weather=SourceObservation("weather", input_model.weather.observed_at),
        active_supporting_episode_count=(
            input_model.active_supporting_episode_count
        ),
    )


def validate_output_against_input(
    input_model: ConfidenceInputV1,
    output_model: ConfidenceOutputV1,
    retained_scoring_output: ScoringOutputV1 | None = None,
) -> None:
    embedded_json = canonical_json(
        output_model.scoring_output.model_dump(mode="json")
    )
    embedded_hash = hashlib.sha256(embedded_json.encode("utf-8")).hexdigest()
    if embedded_hash != input_model.scoring_output_sha256:
        raise ValueError("embedded scoring output digest is inconsistent")
    if retained_scoring_output is not None and (
        embedded_json
        != canonical_json(retained_scoring_output.model_dump(mode="json"))
    ):
        raise ValueError("embedded scoring output differs from retained evidence")
    scoring_candidates = output_model.scoring_output.eligible_candidates
    expected = tuple(
        (item.technician_id, item.rank, item.objective_score)
        for item in input_model.candidates
    )
    actual = tuple(
        (item.technician_id, item.rank, item.objective_score)
        for item in scoring_candidates
    )
    if actual != expected:
        raise ValueError("confidence output altered retained scoring evidence")
    recalculated = ConfidenceOutputV1.from_domain(
        evaluate_input(input_model),
        output_model.scoring_output,
    )
    if recalculated.model_dump(mode="json") != output_model.model_dump(mode="json"):
        raise ValueError("confidence output does not match confidence-v1")

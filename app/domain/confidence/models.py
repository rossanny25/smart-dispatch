from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.domain.scoring.models import RawInputs


@dataclass(frozen=True)
class ConfidenceCandidate:
    technician_id: UUID
    rank: int
    objective_score: Decimal


@dataclass(frozen=True)
class GpsObservation:
    technician_id: UUID
    observed_at: datetime | None
    last_known_zone: str | None


@dataclass(frozen=True)
class SourceObservation:
    source: str
    observed_at: datetime | None


@dataclass(frozen=True)
class SourceQuality:
    source: str
    technician_id: UUID | None
    affected_field: str
    observed_at: datetime | None
    age_minutes: Decimal | None
    quality: str
    value: Decimal
    fallback: str
    fallback_quality: str


@dataclass(frozen=True)
class ConfidenceFactor:
    name: str
    raw_inputs: RawInputs
    value: Decimal
    weight: Decimal
    weighted_contribution: Decimal
    configuration_version: str


@dataclass(frozen=True)
class ConfidenceWarning:
    code: str
    severity: str
    source: str
    affected_field: str
    quality: str
    freshness: str
    age_minutes: Decimal | None
    fallback: str
    fallback_quality: str
    impact: str
    technician_id: UUID | None
    configuration_version: str


@dataclass(frozen=True)
class ConfidenceResult:
    schema_version: str
    configuration_version: str
    candidates: tuple[ConfidenceCandidate, ...]
    recommended_technician_id: UUID | None
    factors: tuple[ConfidenceFactor, ...]
    sources: tuple[SourceQuality, ...]
    uncertain_conditions: tuple[str, ...]
    warnings: tuple[ConfidenceWarning, ...]
    value: Decimal | None
    label: str | None
    explanation: "ConfidenceExplanation"


@dataclass(frozen=True)
class ConfidenceExplanation:
    template_id: str
    leading_technician_id: UUID | None
    leading_objective_score: Decimal | None
    confidence_value: Decimal | None
    confidence_label: str | None
    first_score: Decimal | None
    second_score: Decimal | None
    limiting_factors: tuple[str, ...]
    warning_codes: tuple[str, ...]


@dataclass(frozen=True)
class ConfidenceEvaluationSet:
    id: UUID
    scoring_evaluation_set_id: UUID
    schema_version: str
    configuration_version: str
    input_hash: str
    input_json: str
    output_json: str
    eligible_count: int
    source_count: int
    warning_count: int
    recommended_technician_id: UUID | None
    confidence_value: str | None
    confidence_label: str | None
    created_at: datetime

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


RawInputs = tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ScoringTechnician:
    technician_id: UUID
    eta_minutes: int
    distance_meters: int
    projected_work_minutes: int
    quality_rating_0_to_5: Decimal | None


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    raw_inputs: RawInputs
    normalized_value: Decimal
    weight: Decimal
    weighted_contribution: Decimal
    configuration_version: str


@dataclass(frozen=True)
class ScorePenalty:
    name: str
    version: str
    raw_inputs: RawInputs
    amount: Decimal
    impact: str


@dataclass(frozen=True)
class ScoringWarning:
    code: str
    severity: str
    technician_id: UUID
    source: str
    quality: str
    freshness: str
    fallback: str
    impact: str
    configuration_version: str


@dataclass(frozen=True)
class ScoredTechnician:
    technician_id: UUID
    rank: int
    objective_score: Decimal
    components: tuple[ScoreComponent, ...]
    penalties: tuple[ScorePenalty, ...]
    warnings: tuple[ScoringWarning, ...]
    eta_minutes: int


@dataclass(frozen=True)
class ScoringResult:
    schema_version: str
    configuration_version: str
    candidates: tuple[ScoredTechnician, ...]


@dataclass(frozen=True)
class ScoringEvaluationSet:
    id: UUID
    eligibility_evaluation_set_id: UUID
    schema_version: str
    configuration_version: str
    input_hash: str
    input_json: str
    output_json: str
    candidate_count: int
    eligible_count: int
    ineligible_count: int
    top_technician_id: UUID | None
    top_objective_score: str | None
    created_at: datetime

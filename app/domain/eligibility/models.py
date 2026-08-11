from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


EvidenceValue = str | int | bool | None | tuple[str, ...]


@dataclass(frozen=True)
class EligibilityRequirements:
    priority: int
    required_certifications: tuple[str, ...]
    estimated_service_duration_minutes: int


@dataclass(frozen=True)
class EligibilityTechnician:
    technician_id: UUID
    availability: str
    certifications: tuple[str, ...]
    shift_start: datetime
    shift_end: datetime
    assigned_work_minutes: int
    accumulated_driving_minutes: int | None
    has_required_epp: bool | None
    estimated_travel_minutes: int
    distance_meters: int


@dataclass(frozen=True)
class EligibilityCheck:
    name: str
    status: str
    reason: str
    evidence: tuple[tuple[str, EvidenceValue], ...]

    def evidence_dict(self) -> dict[str, Any]:
        return {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in self.evidence
        }


@dataclass(frozen=True)
class EligibilityWarning:
    code: str
    severity: str
    technician_id: UUID
    affected_check: str
    source: str
    quality: str
    freshness: str
    fallback: None
    impact: str
    configuration_version: str


@dataclass(frozen=True)
class EligibilityCandidate:
    technician_id: UUID
    eligible: bool
    distance_meters: int
    checks: tuple[EligibilityCheck, ...]
    warnings: tuple[EligibilityWarning, ...]


@dataclass(frozen=True)
class EligibilityResult:
    schema_version: str
    configuration_version: str
    candidates: tuple[EligibilityCandidate, ...]
    eligible_technician_ids: tuple[UUID, ...]
    ineligible_technician_ids: tuple[UUID, ...]
    no_feasible_candidates: bool


@dataclass(frozen=True)
class EligibilityEvaluationSet:
    id: UUID
    work_order_id: str
    work_order_analysis_id: str
    schema_version: str
    configuration_version: str
    input_hash: str
    input_json: str
    output_json: str
    candidate_count: int
    eligible_count: int
    ineligible_count: int
    no_feasible_candidates: bool
    created_at: datetime

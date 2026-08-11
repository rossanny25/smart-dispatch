from datetime import UTC, datetime
import json
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.contracts.common import ResponseMetaV1, StrictContract
from app.contracts.eligibility import EligibilityTechnicianV1
from app.contracts.scoring import ScoringQualitySupplementV1
from app.contracts.scoring import ScoredTechnicianV1, ScoringOutputV1
from app.contracts.eligibility import EligibilityCandidateV1, EligibilityOutputV1
from app.contracts.confidence import (
    ConfidenceExplanationV1,
    ConfidenceFactorV1,
    ConfidenceWarningV1,
    SourceQualityV1,
)


def _parse_uuid(value: Any) -> Any:
    return UUID(value) if isinstance(value, str) else value


def _parse_datetime(value: Any) -> Any:
    if isinstance(value, str):
        if not value.endswith("Z"):
            raise ValueError("timestamp must use canonical UTC Z form")
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class DispatchGpsObservationV1(StrictContract):
    technician_id: UUID
    observed_at: datetime | None
    last_known_zone: str | None = Field(default=None, min_length=1, max_length=80)

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _time = field_validator("observed_at", mode="before")(_parse_datetime)

    @field_validator("observed_at")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
        ):
            raise ValueError("timestamp must be timezone-aware UTC")
        return value


class DispatchRunStartV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    work_order_id: UUID
    captured_at: datetime
    technicians: tuple[EligibilityTechnicianV1, ...] = Field(
        min_length=1, max_length=100
    )
    technician_quality: tuple[ScoringQualitySupplementV1, ...] = Field(
        min_length=1, max_length=100
    )
    gps_observations: tuple[DispatchGpsObservationV1, ...] = Field(
        min_length=1, max_length=100
    )
    traffic_observed_at: datetime | None
    weather_observed_at: datetime | None
    active_supporting_episode_count: int = Field(strict=True, ge=0, le=10_000)
    memory_experiment_mode: Literal["disabled"] = "disabled"

    _uuid = field_validator("work_order_id", mode="before")(_parse_uuid)
    _times = field_validator(
        "captured_at",
        "traffic_observed_at",
        "weather_observed_at",
        mode="before",
    )(_parse_datetime)

    @field_validator(
        "technicians",
        "technician_quality",
        "gps_observations",
        mode="before",
    )
    @classmethod
    def json_arrays_to_immutable_tuples(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def canonical_snapshot(self) -> "DispatchRunStartV1":
        for value in (
            self.captured_at,
            self.traffic_observed_at,
            self.weather_observed_at,
        ):
            if value is not None and (
                value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
            ):
                raise ValueError("timestamps must be timezone-aware UTC")
            if value is not None and value > self.captured_at:
                raise ValueError("source timestamp cannot be in the future")
        roster = tuple(str(item.technician_id) for item in self.technicians)
        quality = tuple(str(item.technician_id) for item in self.technician_quality)
        gps = tuple(str(item.technician_id) for item in self.gps_observations)
        if roster != tuple(sorted(set(roster))):
            raise ValueError("technicians must be unique and sorted")
        if quality != roster:
            raise ValueError("technician_quality must exactly match roster")
        if gps != roster:
            raise ValueError("gps_observations must exactly match roster")
        return self

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


RunState = Literal[
    "CAPTURE",
    "ANALYZE",
    "PLAN",
    "EVALUATE",
    "WAIT_FOR_DECISION",
    "NO_FEASIBLE_CANDIDATES",
    "FAILED",
]


class StageExecutionV1(StrictContract):
    execution_id: UUID
    sequence: int = Field(strict=True, ge=1, le=4)
    stage: Literal["CAPTURE", "ANALYZE", "PLAN", "EVALUATE"]
    status: Literal["completed", "failed"]
    started_at: datetime
    ended_at: datetime
    duration_ms: int = Field(strict=True, ge=0)
    attempt: Literal[1] = 1
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["dispatch-v1"] = "dispatch-v1"
    input_ref: str
    run_snapshot_ref: str
    output_ref: str | None
    error_code: str | None = None
    error_type: Literal["STAGE_FAILURE"] | None = None
    safe_message: str | None = None

    _uuid = field_validator("execution_id", mode="before")(_parse_uuid)

    _times = field_validator("started_at", "ended_at", mode="before")(
        _parse_datetime
    )

    @model_validator(mode="after")
    def canonical_timing(self) -> "StageExecutionV1":
        if any(
            value.tzinfo is None
            or value.utcoffset() != UTC.utcoffset(value)
            for value in (self.started_at, self.ended_at)
        ) or self.ended_at < self.started_at:
            raise ValueError("stage timing must be chronological UTC")
        return self


class StateTransitionV1(StrictContract):
    sequence: int = Field(strict=True, ge=0, le=4)
    from_state: RunState | None
    to_state: RunState
    outcome_code: str
    run_revision: int = Field(strict=True, ge=0, le=4)
    configuration_version: Literal["dispatch-v1"] = "dispatch-v1"
    occurred_at: datetime

    _time = field_validator("occurred_at", mode="before")(_parse_datetime)

    @field_validator("occurred_at")
    @classmethod
    def utc_transition(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("transition timestamp must be UTC")
        return value


class DispatchRecommendationV1(StrictContract):
    technician_id: UUID
    confidence_value: str
    confidence_label: Literal["low", "medium", "high"]
    scoring: ScoredTechnicianV1
    factors: tuple[ConfidenceFactorV1, ...]
    sources: tuple[SourceQualityV1, ...]
    warnings: tuple[ConfidenceWarningV1, ...]
    explanation: ConfidenceExplanationV1

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @field_validator("scoring", mode="before")
    @classmethod
    def parse_scoring(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return ScoredTechnicianV1.model_validate_json(
                json.dumps(value, separators=(",", ":"), sort_keys=True)
            )
        return value

    @field_validator("factors", mode="before")
    @classmethod
    def parse_factors(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(
                ConfidenceFactorV1.model_validate_json(
                    json.dumps(item, separators=(",", ":"), sort_keys=True)
                )
                for item in value
            )
        return value

    @field_validator("sources", mode="before")
    @classmethod
    def parse_sources(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(
                SourceQualityV1.model_validate_json(
                    json.dumps(item, separators=(",", ":"), sort_keys=True)
                )
                for item in value
            )
        return value

    @field_validator("warnings", mode="before")
    @classmethod
    def parse_warnings(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(
                ConfidenceWarningV1.model_validate_json(
                    json.dumps(item, separators=(",", ":"), sort_keys=True)
                )
                for item in value
            )
        return value

    @field_validator("explanation", mode="before")
    @classmethod
    def parse_explanation(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return ConfidenceExplanationV1.model_validate_json(
                json.dumps(value, separators=(",", ":"), sort_keys=True)
            )
        return value

    @model_validator(mode="after")
    def recommendation_is_rank_one(self) -> "DispatchRecommendationV1":
        if (
            self.scoring.technician_id != self.technician_id
            or self.scoring.rank != 1
            or self.explanation.leading_technician_id != self.technician_id
            or self.explanation.confidence_value != self.confidence_value
            or self.explanation.confidence_label != self.confidence_label
        ):
            raise ValueError("recommendation evidence is inconsistent")
        return self


class DispatchCandidateEvaluationV1(StrictContract):
    technician_id: UUID
    eligible: bool = Field(strict=True)
    eligibility: EligibilityCandidateV1
    objective_score: str | None
    rank: int | None = Field(strict=True, default=None, ge=1, le=100)
    scoring: ScoredTechnicianV1 | None

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @field_validator("scoring", mode="before")
    @classmethod
    def parse_scoring(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return ScoredTechnicianV1.model_validate_json(
                json.dumps(value, separators=(",", ":"), sort_keys=True)
            )
        return value

    @model_validator(mode="after")
    def score_only_eligible(self) -> "DispatchCandidateEvaluationV1":
        if self.eligible != self.eligibility.eligible:
            raise ValueError("candidate eligibility summary is inconsistent")
        if self.eligible != (self.objective_score is not None and self.rank is not None):
            raise ValueError("only eligible candidates can have score and rank")
        if self.eligible != (self.scoring is not None):
            raise ValueError("only eligible candidates can have scoring evidence")
        if self.scoring is not None and (
            self.scoring.technician_id != self.technician_id
            or self.scoring.objective_score != self.objective_score
            or self.scoring.rank != self.rank
        ):
            raise ValueError("candidate scoring summary is inconsistent")
        return self


class DispatchFailureV1(StrictContract):
    stage: Literal["CAPTURE", "ANALYZE", "PLAN", "EVALUATE"]
    code: str
    type: Literal["STAGE_FAILURE"]


class DispatchConfigurationBundleV1(StrictContract):
    dispatch_v1: str = Field(alias="dispatch-v1", pattern=r"^[0-9a-f]{64}$")
    analysis_v1: str = Field(alias="analysis-v1", pattern=r"^[0-9a-f]{64}$")
    eligibility_v1: str = Field(
        alias="eligibility-v1", pattern=r"^[0-9a-f]{64}$"
    )
    scoring_v1: str = Field(alias="scoring-v1", pattern=r"^[0-9a-f]{64}$")
    confidence_v1: str = Field(
        alias="confidence-v1", pattern=r"^[0-9a-f]{64}$"
    )

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        serialize_by_alias=True,
    )


class CaptureOutputV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    validated_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DispatchPlanOutputV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    eligibility: EligibilityOutputV1
    scoring: ScoringOutputV1


class DispatchArtifactRefsV1(StrictContract):
    run_input: str
    capture: str | None = None
    analyze: str | None = None
    plan: str | None = None
    evaluate: str | None = None


class DispatchRunResourceV1(StrictContract):
    run_id: UUID
    work_order_id: UUID
    schema_version: Literal["v1"] = "v1"
    state: RunState
    revision: int = Field(strict=True, ge=0)
    captured_at: datetime
    memory_experiment_mode: Literal["disabled"] = "disabled"
    configuration_versions: DispatchConfigurationBundleV1
    input_snapshot_ref: str
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stage_executions: tuple[StageExecutionV1, ...]
    transitions: tuple[StateTransitionV1, ...]
    recommendation: DispatchRecommendationV1 | None
    candidate_evaluations: tuple[DispatchCandidateEvaluationV1, ...]
    artifacts: DispatchArtifactRefsV1
    failure: DispatchFailureV1 | None = None

    _uuids = field_validator("run_id", "work_order_id", mode="before")(_parse_uuid)
    _captured = field_validator("captured_at", mode="before")(_parse_datetime)

    @field_validator(
        "stage_executions",
        "transitions",
        "candidate_evaluations",
        mode="before",
    )
    @classmethod
    def json_arrays_to_tuples(cls, value: Any) -> Any:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def complete_auditable_resource(self) -> "DispatchRunResourceV1":
        if [item.sequence for item in self.stage_executions] != list(
            range(1, len(self.stage_executions) + 1)
        ):
            raise ValueError("stage execution sequence must be consecutive")
        if [item.sequence for item in self.transitions] != list(
            range(len(self.transitions))
        ):
            raise ValueError("transition sequence must be consecutive")
        transition_times = [item.occurred_at for item in self.transitions]
        if transition_times != sorted(transition_times):
            raise ValueError("transitions must be chronological")
        expected_stages = ("CAPTURE", "ANALYZE", "PLAN", "EVALUATE")
        if tuple(item.stage for item in self.stage_executions) != expected_stages[
            : len(self.stage_executions)
        ]:
            raise ValueError("stage executions must follow canonical order")
        if any(
            item.ended_at < item.started_at
            or item.duration_ms < 0
            or (
                item.status == "completed"
                and (
                    item.output_ref is None
                    or item.error_code is not None
                    or item.error_type is not None
                    or item.safe_message is not None
                )
            )
            or (
                item.status == "failed"
                and (
                    item.output_ref is not None
                    or item.error_code is None
                    or item.error_type is None
                    or item.safe_message is None
                )
            )
            for item in self.stage_executions
        ):
            raise ValueError("stage execution evidence is inconsistent")
        if self.revision != len(self.transitions) - 1:
            raise ValueError("revision must equal completed stage count")
        if self.transitions and self.transitions[-1].to_state != self.state:
            raise ValueError("state must match final transition")
        if self.state == "WAIT_FOR_DECISION":
            if self.recommendation is None or self.failure is not None:
                raise ValueError("completed run requires recommendation")
            ranked_first = next(
                (
                    item
                    for item in self.candidate_evaluations
                    if item.eligible and item.rank == 1
                ),
                None,
            )
            if (
                ranked_first is None
                or ranked_first.technician_id
                != self.recommendation.technician_id
            ):
                raise ValueError("recommendation must equal rank-one candidate")
        elif self.state == "NO_FEASIBLE_CANDIDATES":
            if (
                self.recommendation is not None
                or self.failure is not None
                or any(item.eligible for item in self.candidate_evaluations)
            ):
                raise ValueError("no-feasible outcome is inconsistent")
        elif self.state == "FAILED":
            if self.recommendation is not None or self.failure is None:
                raise ValueError("failed run requires typed failure")
            if (
                not self.stage_executions
                or self.stage_executions[-1].status != "failed"
                or self.stage_executions[-1].stage != self.failure.stage
                or self.stage_executions[-1].error_code != self.failure.code
            ):
                raise ValueError("failure must match final failed execution")
        elif self.recommendation is not None or self.failure is not None:
            raise ValueError("active run cannot contain terminal summary")
        ranks = tuple(
            item.rank for item in self.candidate_evaluations if item.eligible
        )
        if tuple(sorted(ranks)) != tuple(range(1, len(ranks) + 1)):
            raise ValueError("eligible candidate ranks must be consecutive")
        return self


class DispatchRunSuccessEnvelopeV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    data: DispatchRunResourceV1
    meta: ResponseMetaV1

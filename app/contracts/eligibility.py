from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.contracts.common import StrictContract
from app.contracts.stages.analyze import Certification
from app.domain.eligibility.models import (
    EligibilityRequirements,
    EligibilityResult,
    EligibilityTechnician,
)
from app.domain.eligibility.rules import (
    CHECK_ORDER,
    ELIGIBILITY_CONFIGURATION,
    WARNING_TEMPLATES,
)


Availability = Literal["available", "busy", "absent", "off_duty"]
CheckName = Literal[
    "availability",
    "certifications",
    "shift",
    "maximum_workday",
    "driving_limit",
    "required_epp",
]
CheckStatus = Literal["pass", "fail"]
Reason = Literal[
    "TECHNICIAN_AVAILABLE",
    "TECHNICIAN_UNAVAILABLE",
    "ALL_CERTIFICATIONS_PRESENT",
    "NO_CERTIFICATIONS_REQUIRED",
    "CERTIFICATIONS_MISSING",
    "WITHIN_SHIFT",
    "OUTSIDE_SHIFT",
    "SHIFT_END_EXCEEDED",
    "WITHIN_MAXIMUM_WORKDAY",
    "MAXIMUM_WORKDAY_EXCEEDED",
    "WITHIN_DRIVING_LIMIT",
    "DRIVING_LIMIT_EXCEEDED",
    "EPP_PRESENT",
    "EPP_NOT_REQUIRED_FOR_PRIORITY",
    "REQUIRED_EPP_MISSING",
    "SOURCE_DATA_UNAVAILABLE",
    "CHECK_DISABLED",
]
EvidenceValue = str | int | bool | None | list[str]


def _parse_datetime(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_uuid(value: Any) -> Any:
    return UUID(value) if isinstance(value, str) else value


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value


class EligibilityRequirementsV1(StrictContract):
    priority: int = Field(strict=True, ge=1, le=5)
    required_certifications: list[Certification] = Field(max_length=16)
    estimated_service_duration_minutes: int = Field(strict=True, ge=15, le=1440)

    @model_validator(mode="after")
    def canonical_certifications(self):
        if self.required_certifications != sorted(
            set(self.required_certifications)
        ):
            raise ValueError("required_certifications must be unique and sorted")
        return self


class EligibilityTechnicianV1(StrictContract):
    technician_id: UUID
    availability: Availability
    certifications: list[Certification] = Field(max_length=16)
    shift_start: datetime
    shift_end: datetime
    assigned_work_minutes: int = Field(strict=True, ge=0, le=1440)
    accumulated_driving_minutes: int | None = Field(
        strict=True, default=None, ge=0, le=1440
    )
    has_required_epp: bool | None = Field(strict=True, default=None)
    estimated_travel_minutes: int = Field(strict=True, ge=0, le=1440)
    distance_meters: int = Field(strict=True, ge=0, le=1_000_000)

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)
    _datetimes = field_validator(
        "shift_start", "shift_end", mode="before"
    )(_parse_datetime)

    @model_validator(mode="after")
    def canonical_snapshot(self):
        _require_utc(self.shift_start)
        _require_utc(self.shift_end)
        if self.shift_start >= self.shift_end:
            raise ValueError("shift_start must precede shift_end")
        if self.certifications != sorted(set(self.certifications)):
            raise ValueError("certifications must be unique and sorted")
        return self


class EligibilityInputV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["eligibility-v1"] = "eligibility-v1"
    requirements: EligibilityRequirementsV1
    captured_at: datetime
    technicians: list[EligibilityTechnicianV1] = Field(max_length=100)

    _captured = field_validator("captured_at", mode="before")(_parse_datetime)

    @model_validator(mode="after")
    def canonical_input(self):
        _require_utc(self.captured_at)
        identifiers = [str(item.technician_id) for item in self.technicians]
        if identifiers != sorted(set(identifiers)):
            raise ValueError("technicians must be unique and sorted")
        return self

    def to_domain_requirements(self) -> EligibilityRequirements:
        return EligibilityRequirements(
            priority=self.requirements.priority,
            required_certifications=tuple(
                self.requirements.required_certifications
            ),
            estimated_service_duration_minutes=(
                self.requirements.estimated_service_duration_minutes
            ),
        )

    def to_domain_technicians(self) -> tuple[EligibilityTechnician, ...]:
        return tuple(
            EligibilityTechnician(
                technician_id=item.technician_id,
                availability=item.availability,
                certifications=tuple(item.certifications),
                shift_start=item.shift_start,
                shift_end=item.shift_end,
                assigned_work_minutes=item.assigned_work_minutes,
                accumulated_driving_minutes=item.accumulated_driving_minutes,
                has_required_epp=item.has_required_epp,
                estimated_travel_minutes=item.estimated_travel_minutes,
                distance_meters=item.distance_meters,
            )
            for item in self.technicians
        )


REASONS_BY_CHECK = {
    "availability": {
        "TECHNICIAN_AVAILABLE",
        "TECHNICIAN_UNAVAILABLE",
        "CHECK_DISABLED",
    },
    "certifications": {
        "ALL_CERTIFICATIONS_PRESENT",
        "NO_CERTIFICATIONS_REQUIRED",
        "CERTIFICATIONS_MISSING",
        "CHECK_DISABLED",
    },
    "shift": {
        "WITHIN_SHIFT",
        "OUTSIDE_SHIFT",
        "SHIFT_END_EXCEEDED",
        "CHECK_DISABLED",
    },
    "maximum_workday": {
        "WITHIN_MAXIMUM_WORKDAY",
        "MAXIMUM_WORKDAY_EXCEEDED",
        "CHECK_DISABLED",
    },
    "driving_limit": {
        "WITHIN_DRIVING_LIMIT",
        "DRIVING_LIMIT_EXCEEDED",
        "SOURCE_DATA_UNAVAILABLE",
        "CHECK_DISABLED",
    },
    "required_epp": {
        "EPP_PRESENT",
        "EPP_NOT_REQUIRED_FOR_PRIORITY",
        "REQUIRED_EPP_MISSING",
        "SOURCE_DATA_UNAVAILABLE",
        "CHECK_DISABLED",
    },
}
PASS_REASONS = {
    "TECHNICIAN_AVAILABLE",
    "ALL_CERTIFICATIONS_PRESENT",
    "NO_CERTIFICATIONS_REQUIRED",
    "WITHIN_SHIFT",
    "WITHIN_MAXIMUM_WORKDAY",
    "WITHIN_DRIVING_LIMIT",
    "EPP_PRESENT",
    "EPP_NOT_REQUIRED_FOR_PRIORITY",
}
EVIDENCE_KEYS_BY_CHECK = {
    "availability": {"observed"},
    "certifications": {"required", "possessed", "missing"},
    "shift": {
        "captured_at",
        "shift_start",
        "shift_end",
        "travel_minutes",
        "service_minutes",
        "projected_finish",
    },
    "maximum_workday": {
        "assigned_work_minutes",
        "travel_minutes",
        "service_minutes",
        "projected_workday_minutes",
        "maximum_workday_minutes",
    },
    "driving_limit": {
        "enabled",
        "accumulated_driving_minutes",
        "travel_minutes",
        "projected_driving_minutes",
        "maximum_driving_minutes",
    },
    "required_epp": {
        "enabled",
        "required_for_priority",
        "observed",
        "priority_threshold",
    },
}


def _status_for(reason: str) -> str:
    return "pass" if reason in PASS_REASONS else "fail"


class AvailabilityEvidenceV1(StrictContract):
    observed: Availability


class AvailabilityCheckV1(StrictContract):
    name: Literal["availability"]
    status: CheckStatus
    reason: Literal["TECHNICIAN_AVAILABLE", "TECHNICIAN_UNAVAILABLE"]
    evidence: AvailabilityEvidenceV1

    @model_validator(mode="after")
    def semantic_result(self):
        expected_reason = (
            "TECHNICIAN_AVAILABLE"
            if self.evidence.observed == "available"
            else "TECHNICIAN_UNAVAILABLE"
        )
        if self.reason != expected_reason or self.status != _status_for(self.reason):
            raise ValueError("availability result is inconsistent")
        return self


class CertificationsEvidenceV1(StrictContract):
    required: list[Certification]
    possessed: list[Certification]
    missing: list[Certification]

    @model_validator(mode="after")
    def canonical_sets(self):
        for value in (self.required, self.possessed, self.missing):
            if value != sorted(set(value)):
                raise ValueError("certification evidence must be unique and sorted")
        if self.missing != sorted(set(self.required) - set(self.possessed)):
            raise ValueError("missing certifications are inconsistent")
        return self


class CertificationsCheckV1(StrictContract):
    name: Literal["certifications"]
    status: CheckStatus
    reason: Literal[
        "ALL_CERTIFICATIONS_PRESENT",
        "NO_CERTIFICATIONS_REQUIRED",
        "CERTIFICATIONS_MISSING",
    ]
    evidence: CertificationsEvidenceV1

    @model_validator(mode="after")
    def semantic_result(self):
        if not self.evidence.required:
            expected_reason = "NO_CERTIFICATIONS_REQUIRED"
        elif self.evidence.missing:
            expected_reason = "CERTIFICATIONS_MISSING"
        else:
            expected_reason = "ALL_CERTIFICATIONS_PRESENT"
        if self.reason != expected_reason or self.status != _status_for(self.reason):
            raise ValueError("certification result is inconsistent")
        return self


class ShiftEvidenceV1(StrictContract):
    captured_at: datetime
    shift_start: datetime
    shift_end: datetime
    travel_minutes: int = Field(strict=True, ge=0, le=1440)
    service_minutes: int = Field(strict=True, ge=15, le=1440)
    projected_finish: datetime

    _datetimes = field_validator(
        "captured_at",
        "shift_start",
        "shift_end",
        "projected_finish",
        mode="before",
    )(_parse_datetime)

    @model_validator(mode="after")
    def semantic_projection(self):
        for value in (
            self.captured_at,
            self.shift_start,
            self.shift_end,
            self.projected_finish,
        ):
            _require_utc(value)
        if self.shift_start >= self.shift_end:
            raise ValueError("shift evidence boundaries are invalid")
        try:
            expected = self.captured_at + timedelta(
                minutes=self.travel_minutes + self.service_minutes
            )
        except OverflowError:
            expected = datetime.max.replace(tzinfo=UTC)
        if self.projected_finish != expected:
            raise ValueError("projected_finish is inconsistent")
        return self


class ShiftCheckV1(StrictContract):
    name: Literal["shift"]
    status: CheckStatus
    reason: Literal["WITHIN_SHIFT", "OUTSIDE_SHIFT", "SHIFT_END_EXCEEDED"]
    evidence: ShiftEvidenceV1

    @model_validator(mode="after")
    def semantic_result(self):
        evidence = self.evidence
        projection_overflow = False
        try:
            evidence.captured_at + timedelta(
                minutes=evidence.travel_minutes + evidence.service_minutes
            )
        except OverflowError:
            projection_overflow = True
        if not (
            evidence.shift_start
            <= evidence.captured_at
            < evidence.shift_end
        ):
            expected_reason = "OUTSIDE_SHIFT"
        elif projection_overflow or evidence.projected_finish > evidence.shift_end:
            expected_reason = "SHIFT_END_EXCEEDED"
        else:
            expected_reason = "WITHIN_SHIFT"
        if self.reason != expected_reason or self.status != _status_for(self.reason):
            raise ValueError("shift result is inconsistent")
        return self


class MaximumWorkdayEvidenceV1(StrictContract):
    assigned_work_minutes: int = Field(strict=True, ge=0, le=1440)
    travel_minutes: int = Field(strict=True, ge=0, le=1440)
    service_minutes: int = Field(strict=True, ge=15, le=1440)
    projected_workday_minutes: int = Field(strict=True, ge=0, le=4320)
    maximum_workday_minutes: int = Field(strict=True, ge=1, le=1440)

    @model_validator(mode="after")
    def semantic_projection(self):
        if self.projected_workday_minutes != (
            self.assigned_work_minutes
            + self.travel_minutes
            + self.service_minutes
        ):
            raise ValueError("projected workday is inconsistent")
        return self


class MaximumWorkdayCheckV1(StrictContract):
    name: Literal["maximum_workday"]
    status: CheckStatus
    reason: Literal["WITHIN_MAXIMUM_WORKDAY", "MAXIMUM_WORKDAY_EXCEEDED"]
    evidence: MaximumWorkdayEvidenceV1

    @model_validator(mode="after")
    def semantic_result(self):
        expected_reason = (
            "WITHIN_MAXIMUM_WORKDAY"
            if self.evidence.projected_workday_minutes
            <= self.evidence.maximum_workday_minutes
            else "MAXIMUM_WORKDAY_EXCEEDED"
        )
        if self.reason != expected_reason or self.status != _status_for(self.reason):
            raise ValueError("maximum-workday result is inconsistent")
        return self


class DrivingLimitEvidenceV1(StrictContract):
    enabled: bool = Field(strict=True)
    accumulated_driving_minutes: int | None = Field(
        strict=True, ge=0, le=1440
    )
    travel_minutes: int = Field(strict=True, ge=0, le=1440)
    projected_driving_minutes: int | None = Field(
        strict=True, ge=0, le=2880
    )
    maximum_driving_minutes: int = Field(strict=True, ge=1, le=1440)

    @model_validator(mode="after")
    def semantic_projection(self):
        expected = (
            None
            if self.accumulated_driving_minutes is None
            else self.accumulated_driving_minutes + self.travel_minutes
        )
        if self.projected_driving_minutes != expected:
            raise ValueError("projected driving is inconsistent")
        return self


class DrivingLimitCheckV1(StrictContract):
    name: Literal["driving_limit"]
    status: CheckStatus
    reason: Literal[
        "WITHIN_DRIVING_LIMIT",
        "DRIVING_LIMIT_EXCEEDED",
        "SOURCE_DATA_UNAVAILABLE",
        "CHECK_DISABLED",
    ]
    evidence: DrivingLimitEvidenceV1

    @model_validator(mode="after")
    def semantic_result(self):
        evidence = self.evidence
        if not evidence.enabled:
            expected_reason = "CHECK_DISABLED"
        elif evidence.accumulated_driving_minutes is None:
            expected_reason = "SOURCE_DATA_UNAVAILABLE"
        elif (
            evidence.projected_driving_minutes is not None
            and evidence.projected_driving_minutes
            > evidence.maximum_driving_minutes
        ):
            expected_reason = "DRIVING_LIMIT_EXCEEDED"
        else:
            expected_reason = "WITHIN_DRIVING_LIMIT"
        if self.reason != expected_reason or self.status != _status_for(self.reason):
            raise ValueError("driving-limit result is inconsistent")
        return self


class RequiredEppEvidenceV1(StrictContract):
    enabled: bool = Field(strict=True)
    required_for_priority: bool = Field(strict=True)
    observed: bool | None = Field(strict=True)
    priority_threshold: int = Field(strict=True, ge=1, le=5)


class RequiredEppCheckV1(StrictContract):
    name: Literal["required_epp"]
    status: CheckStatus
    reason: Literal[
        "EPP_PRESENT",
        "EPP_NOT_REQUIRED_FOR_PRIORITY",
        "REQUIRED_EPP_MISSING",
        "SOURCE_DATA_UNAVAILABLE",
        "CHECK_DISABLED",
    ]
    evidence: RequiredEppEvidenceV1

    @model_validator(mode="after")
    def semantic_result(self):
        evidence = self.evidence
        if not evidence.enabled:
            expected_reason = "CHECK_DISABLED"
        elif not evidence.required_for_priority:
            expected_reason = "EPP_NOT_REQUIRED_FOR_PRIORITY"
        elif evidence.observed is None:
            expected_reason = "SOURCE_DATA_UNAVAILABLE"
        elif evidence.observed:
            expected_reason = "EPP_PRESENT"
        else:
            expected_reason = "REQUIRED_EPP_MISSING"
        if self.reason != expected_reason or self.status != _status_for(self.reason):
            raise ValueError("required-EPP result is inconsistent")
        return self


EligibilityCheckV1 = Annotated[
    AvailabilityCheckV1
    | CertificationsCheckV1
    | ShiftCheckV1
    | MaximumWorkdayCheckV1
    | DrivingLimitCheckV1
    | RequiredEppCheckV1,
    Field(discriminator="name"),
]


class EligibilityWarningV1(StrictContract):
    code: Literal[
        "ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        "ELIGIBILITY_CHECK_DISABLED",
    ]
    severity: Literal["warning"]
    technician_id: UUID
    affected_check: CheckName
    source: str
    quality: Literal["unavailable", "disabled"]
    freshness: Literal["not_applicable"]
    fallback: None
    impact: str
    configuration_version: Literal["eligibility-v1"]

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @model_validator(mode="after")
    def consistent_warning(self):
        templates = {
            template.affected_check: template for template in WARNING_TEMPLATES
        }
        template = templates[self.affected_check]
        expected_code = (
            template.unavailable_code
            if self.quality == "unavailable"
            else template.disabled_code
        )
        if (
            self.code != expected_code
            or self.source != template.source
            or self.severity != template.severity
            or self.freshness != template.freshness
            or self.fallback is not template.fallback
            or self.impact != template.impact
        ):
            raise ValueError("warning is inconsistent")
        return self


class EligibilityCandidateV1(StrictContract):
    technician_id: UUID
    eligible: bool = Field(strict=True)
    distance_meters: int = Field(strict=True, ge=0, le=1_000_000)
    checks: list[EligibilityCheckV1]
    warnings: list[EligibilityWarningV1]

    _uuid = field_validator("technician_id", mode="before")(_parse_uuid)

    @model_validator(mode="after")
    def complete_evidence(self):
        if [check.name for check in self.checks] != list(CHECK_ORDER):
            raise ValueError("checks must be complete and canonically ordered")
        expected_eligible = all(check.status == "pass" for check in self.checks)
        if self.eligible != expected_eligible:
            raise ValueError("eligible must equal the complete check result")
        expected_warning_checks = [
            check.name
            for check in self.checks
            if check.reason in {"SOURCE_DATA_UNAVAILABLE", "CHECK_DISABLED"}
        ]
        if [warning.affected_check for warning in self.warnings] != (
            expected_warning_checks
        ):
            raise ValueError("warnings must exactly match safety failures")
        for check, warning in zip(
            (
                check
                for check in self.checks
                if check.reason
                in {"SOURCE_DATA_UNAVAILABLE", "CHECK_DISABLED"}
            ),
            self.warnings,
            strict=True,
        ):
            expected_quality = (
                "unavailable"
                if check.reason == "SOURCE_DATA_UNAVAILABLE"
                else "disabled"
            )
            if warning.quality != expected_quality:
                raise ValueError("warning quality must match check failure")
        if any(
            warning.technician_id != self.technician_id
            for warning in self.warnings
        ):
            raise ValueError("warning technician must match candidate")
        return self


class EligibilityOutputV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["eligibility-v1"]
    candidates: list[EligibilityCandidateV1] = Field(max_length=100)
    eligible_technician_ids: list[UUID]
    ineligible_technician_ids: list[UUID]
    no_feasible_candidates: bool = Field(strict=True)

    @field_validator(
        "eligible_technician_ids",
        "ineligible_technician_ids",
        mode="before",
    )
    @classmethod
    def parse_uuid_lists(cls, value: Any):
        if isinstance(value, list):
            return [_parse_uuid(item) for item in value]
        return value

    @model_validator(mode="after")
    def complete_partition(self):
        candidate_ids = [item.technician_id for item in self.candidates]
        if candidate_ids != sorted(set(candidate_ids), key=str):
            raise ValueError("candidates must be unique and sorted")
        eligible = [item.technician_id for item in self.candidates if item.eligible]
        ineligible = [
            item.technician_id for item in self.candidates if not item.eligible
        ]
        if (
            self.eligible_technician_ids != eligible
            or self.ineligible_technician_ids != ineligible
            or self.no_feasible_candidates != (not eligible)
        ):
            raise ValueError("candidate partitions are inconsistent")
        if any(
            warning.configuration_version != self.configuration_version
            for item in self.candidates
            for warning in item.warnings
        ):
            raise ValueError("warning configuration must match output")
        return self

    @classmethod
    def from_domain(cls, result: EligibilityResult) -> "EligibilityOutputV1":
        return cls.model_validate(
            {
                "schema_version": result.schema_version,
                "configuration_version": result.configuration_version,
                "candidates": [
                    {
                        "technician_id": candidate.technician_id,
                        "eligible": candidate.eligible,
                        "distance_meters": candidate.distance_meters,
                        "checks": [
                            {
                                "name": check.name,
                                "status": check.status,
                                "reason": check.reason,
                                "evidence": check.evidence_dict(),
                            }
                            for check in candidate.checks
                        ],
                        "warnings": [
                            {
                                "code": warning.code,
                                "severity": warning.severity,
                                "technician_id": warning.technician_id,
                                "affected_check": warning.affected_check,
                                "source": warning.source,
                                "quality": warning.quality,
                                "freshness": warning.freshness,
                                "fallback": warning.fallback,
                                "impact": warning.impact,
                                "configuration_version": (
                                    warning.configuration_version
                                ),
                            }
                            for warning in candidate.warnings
                        ],
                    }
                    for candidate in result.candidates
                ],
                "eligible_technician_ids": list(
                    result.eligible_technician_ids
                ),
                "ineligible_technician_ids": list(
                    result.ineligible_technician_ids
                ),
                "no_feasible_candidates": result.no_feasible_candidates,
            }
        )


def validate_output_against_input(
    input_model: EligibilityInputV1,
    output_model: EligibilityOutputV1,
) -> None:
    input_ids = [item.technician_id for item in input_model.technicians]
    output_ids = [item.technician_id for item in output_model.candidates]
    if output_ids != input_ids:
        raise ValueError("output candidates must exactly match input roster")
    input_distances = {
        item.technician_id: item.distance_meters
        for item in input_model.technicians
    }
    if any(
        candidate.distance_meters
        != input_distances[candidate.technician_id]
        for candidate in output_model.candidates
    ):
        raise ValueError("output distance must match input snapshot")

    from app.domain.eligibility.policy import EligibilityPolicy

    expected = EligibilityOutputV1.from_domain(
        EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
            requirements=input_model.to_domain_requirements(),
            captured_at=input_model.captured_at,
            technicians=input_model.to_domain_technicians(),
        )
    )
    if output_model.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise ValueError("output does not match canonical policy evaluation")

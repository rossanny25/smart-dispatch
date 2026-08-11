from datetime import datetime, timedelta
from typing import Any

from app.domain.eligibility.models import (
    EligibilityCandidate,
    EligibilityCheck,
    EligibilityRequirements,
    EligibilityResult,
    EligibilityTechnician,
    EligibilityWarning,
)
from app.domain.eligibility.rules import (
    CHECK_ORDER,
    EligibilityConfiguration,
    WARNING_TEMPLATES,
)


def _evidence(**values: Any) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (key, tuple(value) if isinstance(value, list) else value)
        for key, value in values.items()
    )


class EligibilityPolicy:
    def __init__(self, configuration: EligibilityConfiguration) -> None:
        if (
            len(configuration.check_order) != len(CHECK_ORDER)
            or set(configuration.check_order) != set(CHECK_ORDER)
        ):
            raise ValueError("configuration check_order must contain every check")
        self._configuration = configuration

    def evaluate(
        self,
        *,
        requirements: EligibilityRequirements,
        captured_at: datetime,
        technicians: tuple[EligibilityTechnician, ...],
    ) -> EligibilityResult:
        candidates = tuple(
            self._evaluate_candidate(requirements, captured_at, technician)
            for technician in sorted(
                technicians, key=lambda item: str(item.technician_id)
            )
        )
        eligible_ids = tuple(
            item.technician_id for item in candidates if item.eligible
        )
        ineligible_ids = tuple(
            item.technician_id for item in candidates if not item.eligible
        )
        return EligibilityResult(
            schema_version=self._configuration.contract_version,
            configuration_version=self._configuration.version,
            candidates=candidates,
            eligible_technician_ids=eligible_ids,
            ineligible_technician_ids=ineligible_ids,
            no_feasible_candidates=not eligible_ids,
        )

    def _evaluate_candidate(
        self,
        requirements: EligibilityRequirements,
        captured_at: datetime,
        technician: EligibilityTechnician,
    ) -> EligibilityCandidate:
        handlers = {
            "availability": lambda: self._availability(technician),
            "certifications": lambda: self._certifications(
                requirements, technician
            ),
            "shift": lambda: self._shift(
                requirements, captured_at, technician
            ),
            "maximum_workday": lambda: self._maximum_workday(
                requirements, technician
            ),
            "driving_limit": lambda: self._driving_limit(technician),
            "required_epp": lambda: self._required_epp(
                requirements, technician
            ),
        }
        checks = tuple(
            handlers[name]() for name in self._configuration.check_order
        )
        warnings = tuple(
            warning
            for check in checks
            for warning in self._warnings_for(technician, check)
        )
        return EligibilityCandidate(
            technician_id=technician.technician_id,
            eligible=all(check.status == "pass" for check in checks),
            distance_meters=technician.distance_meters,
            checks=checks,
            warnings=warnings,
        )

    def _disabled(self, name: str, **evidence: Any) -> EligibilityCheck:
        evidence = {"enabled": False, **evidence}
        return EligibilityCheck(
            name=name,
            status="fail",
            reason="CHECK_DISABLED",
            evidence=_evidence(**evidence),
        )

    def _availability(self, technician: EligibilityTechnician) -> EligibilityCheck:
        if not self._configuration.availability_enabled:
            return self._disabled(
                "availability", observed=technician.availability
            )
        passed = technician.availability == "available"
        return EligibilityCheck(
            name="availability",
            status="pass" if passed else "fail",
            reason=(
                "TECHNICIAN_AVAILABLE"
                if passed
                else "TECHNICIAN_UNAVAILABLE"
            ),
            evidence=_evidence(observed=technician.availability),
        )

    def _certifications(
        self,
        requirements: EligibilityRequirements,
        technician: EligibilityTechnician,
    ) -> EligibilityCheck:
        required = requirements.required_certifications
        possessed = technician.certifications
        missing = tuple(sorted(set(required) - set(possessed)))
        evidence = _evidence(
            required=required,
            possessed=possessed,
            missing=missing,
        )
        if not self._configuration.certifications_enabled:
            return self._disabled("certifications", **dict(evidence))
        if not required:
            return EligibilityCheck(
                "certifications",
                "pass",
                "NO_CERTIFICATIONS_REQUIRED",
                evidence,
            )
        return EligibilityCheck(
            "certifications",
            "fail" if missing else "pass",
            "CERTIFICATIONS_MISSING" if missing else "ALL_CERTIFICATIONS_PRESENT",
            evidence,
        )

    def _shift(
        self,
        requirements: EligibilityRequirements,
        captured_at: datetime,
        technician: EligibilityTechnician,
    ) -> EligibilityCheck:
        projection_overflow = False
        try:
            projected_finish = captured_at + timedelta(
                minutes=(
                    technician.estimated_travel_minutes
                    + requirements.estimated_service_duration_minutes
                )
            )
        except OverflowError:
            projection_overflow = True
            projected_finish = datetime.max.replace(tzinfo=captured_at.tzinfo)
        evidence = _evidence(
            captured_at=captured_at.isoformat(),
            shift_start=technician.shift_start.isoformat(),
            shift_end=technician.shift_end.isoformat(),
            travel_minutes=technician.estimated_travel_minutes,
            service_minutes=requirements.estimated_service_duration_minutes,
            projected_finish=projected_finish.isoformat(),
        )
        if not self._configuration.shift_enabled:
            return self._disabled("shift", **dict(evidence))
        if not (
            technician.shift_start <= captured_at < technician.shift_end
        ):
            reason = "OUTSIDE_SHIFT"
        elif projection_overflow or projected_finish > technician.shift_end:
            reason = "SHIFT_END_EXCEEDED"
        else:
            reason = "WITHIN_SHIFT"
        return EligibilityCheck(
            "shift",
            "pass" if reason == "WITHIN_SHIFT" else "fail",
            reason,
            evidence,
        )

    def _maximum_workday(
        self,
        requirements: EligibilityRequirements,
        technician: EligibilityTechnician,
    ) -> EligibilityCheck:
        projected = (
            technician.assigned_work_minutes
            + technician.estimated_travel_minutes
            + requirements.estimated_service_duration_minutes
        )
        evidence = _evidence(
            assigned_work_minutes=technician.assigned_work_minutes,
            travel_minutes=technician.estimated_travel_minutes,
            service_minutes=requirements.estimated_service_duration_minutes,
            projected_workday_minutes=projected,
            maximum_workday_minutes=self._configuration.maximum_workday_minutes,
        )
        if not self._configuration.maximum_workday_enabled:
            return self._disabled("maximum_workday", **dict(evidence))
        passed = projected <= self._configuration.maximum_workday_minutes
        return EligibilityCheck(
            "maximum_workday",
            "pass" if passed else "fail",
            (
                "WITHIN_MAXIMUM_WORKDAY"
                if passed
                else "MAXIMUM_WORKDAY_EXCEEDED"
            ),
            evidence,
        )

    def _driving_limit(
        self,
        technician: EligibilityTechnician,
    ) -> EligibilityCheck:
        accumulated = technician.accumulated_driving_minutes
        projected = (
            None
            if accumulated is None
            else accumulated + technician.estimated_travel_minutes
        )
        evidence = _evidence(
            enabled=self._configuration.driving_limit_enabled,
            accumulated_driving_minutes=accumulated,
            travel_minutes=technician.estimated_travel_minutes,
            projected_driving_minutes=projected,
            maximum_driving_minutes=self._configuration.maximum_driving_minutes,
        )
        if not self._configuration.driving_limit_enabled:
            return self._disabled("driving_limit", **dict(evidence))
        if accumulated is None:
            reason = "SOURCE_DATA_UNAVAILABLE"
        elif projected is not None and (
            projected > self._configuration.maximum_driving_minutes
        ):
            reason = "DRIVING_LIMIT_EXCEEDED"
        else:
            reason = "WITHIN_DRIVING_LIMIT"
        return EligibilityCheck(
            "driving_limit",
            "pass" if reason == "WITHIN_DRIVING_LIMIT" else "fail",
            reason,
            evidence,
        )

    def _required_epp(
        self,
        requirements: EligibilityRequirements,
        technician: EligibilityTechnician,
    ) -> EligibilityCheck:
        required = (
            requirements.priority >= self._configuration.epp_priority_threshold
        )
        observed = technician.has_required_epp
        evidence = _evidence(
            enabled=self._configuration.required_epp_enabled,
            required_for_priority=required,
            observed=observed,
            priority_threshold=self._configuration.epp_priority_threshold,
        )
        if not self._configuration.required_epp_enabled:
            return self._disabled("required_epp", **dict(evidence))
        if not required:
            reason = "EPP_NOT_REQUIRED_FOR_PRIORITY"
        elif observed is None:
            reason = "SOURCE_DATA_UNAVAILABLE"
        elif observed:
            reason = "EPP_PRESENT"
        else:
            reason = "REQUIRED_EPP_MISSING"
        return EligibilityCheck(
            "required_epp",
            "pass"
            if reason in {"EPP_PRESENT", "EPP_NOT_REQUIRED_FOR_PRIORITY"}
            else "fail",
            reason,
            evidence,
        )

    def _warnings_for(
        self,
        technician: EligibilityTechnician,
        check: EligibilityCheck,
    ) -> tuple[EligibilityWarning, ...]:
        if check.reason not in {"SOURCE_DATA_UNAVAILABLE", "CHECK_DISABLED"}:
            return ()
        code = (
            "ELIGIBILITY_SOURCE_DATA_UNAVAILABLE"
            if check.reason == "SOURCE_DATA_UNAVAILABLE"
            else "ELIGIBILITY_CHECK_DISABLED"
        )
        templates = {
            template.affected_check: template
            for template in WARNING_TEMPLATES
        }
        template = templates[check.name]
        unavailable = check.reason == "SOURCE_DATA_UNAVAILABLE"
        return (
            EligibilityWarning(
                code=(
                    template.unavailable_code
                    if unavailable
                    else template.disabled_code
                ),
                severity=template.severity,
                technician_id=technician.technician_id,
                affected_check=check.name,
                source=template.source,
                quality=(
                    template.unavailable_quality
                    if unavailable
                    else template.disabled_quality
                ),
                freshness=template.freshness,
                fallback=template.fallback,
                impact=template.impact,
                configuration_version=self._configuration.version,
            ),
        )

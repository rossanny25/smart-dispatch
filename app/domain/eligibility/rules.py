from dataclasses import asdict, dataclass
import hashlib
import json


ELIGIBILITY_CONFIGURATION_VERSION = "eligibility-v1"
ELIGIBILITY_CONTRACT_VERSION = "v1"
ELIGIBILITY_CONFIGURATION_CREATED_AT = "2026-07-28T00:00:00Z"
CHECK_ORDER = (
    "availability",
    "certifications",
    "shift",
    "maximum_workday",
    "driving_limit",
    "required_epp",
)


@dataclass(frozen=True)
class EligibilityConfiguration:
    version: str
    contract_version: str
    maximum_workday_minutes: int
    maximum_driving_minutes: int
    epp_priority_threshold: int
    availability_enabled: bool
    certifications_enabled: bool
    shift_enabled: bool
    maximum_workday_enabled: bool
    driving_limit_enabled: bool
    required_epp_enabled: bool
    check_order: tuple[str, ...]


@dataclass(frozen=True)
class FormulaRule:
    check: str
    expression: str
    pass_condition: str
    missing_data_behavior: str
    evidence_fields: tuple[str, ...]
    pass_reasons: tuple[str, ...]
    fail_reasons: tuple[str, ...]


@dataclass(frozen=True)
class WarningTemplate:
    affected_check: str
    source: str
    severity: str
    freshness: str
    fallback: None
    unavailable_code: str
    unavailable_quality: str
    disabled_code: str
    disabled_quality: str
    impact: str


ELIGIBILITY_CONFIGURATION = EligibilityConfiguration(
    version=ELIGIBILITY_CONFIGURATION_VERSION,
    contract_version=ELIGIBILITY_CONTRACT_VERSION,
    maximum_workday_minutes=480,
    maximum_driving_minutes=240,
    epp_priority_threshold=4,
    availability_enabled=True,
    certifications_enabled=True,
    shift_enabled=True,
    maximum_workday_enabled=True,
    driving_limit_enabled=True,
    required_epp_enabled=True,
    check_order=CHECK_ORDER,
)

FORMULA_RULES = (
    FormulaRule(
        check="availability",
        expression="availability",
        pass_condition="equals:available",
        missing_data_behavior="not_nullable",
        evidence_fields=("observed",),
        pass_reasons=("TECHNICIAN_AVAILABLE",),
        fail_reasons=("TECHNICIAN_UNAVAILABLE",),
    ),
    FormulaRule(
        check="certifications",
        expression="required subset of possessed",
        pass_condition="missing is empty",
        missing_data_behavior="empty_required_passes",
        evidence_fields=("required", "possessed", "missing"),
        pass_reasons=(
            "ALL_CERTIFICATIONS_PRESENT",
            "NO_CERTIFICATIONS_REQUIRED",
        ),
        fail_reasons=("CERTIFICATIONS_MISSING",),
    ),
    FormulaRule(
        check="shift",
        expression="captured_at + travel_minutes + service_minutes",
        pass_condition=(
            "shift_start <= captured_at < shift_end "
            "and projected_finish <= shift_end"
        ),
        missing_data_behavior="not_nullable; overflow_fails_closed",
        evidence_fields=(
            "captured_at",
            "shift_start",
            "shift_end",
            "travel_minutes",
            "service_minutes",
            "projected_finish",
        ),
        pass_reasons=("WITHIN_SHIFT",),
        fail_reasons=("OUTSIDE_SHIFT", "SHIFT_END_EXCEEDED"),
    ),
    FormulaRule(
        check="maximum_workday",
        expression="assigned_work_minutes + travel_minutes + service_minutes",
        pass_condition="projected_workday_minutes <= maximum_workday_minutes",
        missing_data_behavior="not_nullable",
        evidence_fields=(
            "assigned_work_minutes",
            "travel_minutes",
            "service_minutes",
            "projected_workday_minutes",
            "maximum_workday_minutes",
        ),
        pass_reasons=("WITHIN_MAXIMUM_WORKDAY",),
        fail_reasons=("MAXIMUM_WORKDAY_EXCEEDED",),
    ),
    FormulaRule(
        check="driving_limit",
        expression="accumulated_driving_minutes + travel_minutes",
        pass_condition="projected_driving_minutes <= maximum_driving_minutes",
        missing_data_behavior="fail:SOURCE_DATA_UNAVAILABLE",
        evidence_fields=(
            "enabled",
            "accumulated_driving_minutes",
            "travel_minutes",
            "projected_driving_minutes",
            "maximum_driving_minutes",
        ),
        pass_reasons=("WITHIN_DRIVING_LIMIT",),
        fail_reasons=(
            "DRIVING_LIMIT_EXCEEDED",
            "SOURCE_DATA_UNAVAILABLE",
            "CHECK_DISABLED",
        ),
    ),
    FormulaRule(
        check="required_epp",
        expression="priority >= priority_threshold implies observed is true",
        pass_condition="not required or observed is true",
        missing_data_behavior="fail when required:SOURCE_DATA_UNAVAILABLE",
        evidence_fields=(
            "enabled",
            "required_for_priority",
            "observed",
            "priority_threshold",
        ),
        pass_reasons=("EPP_PRESENT", "EPP_NOT_REQUIRED_FOR_PRIORITY"),
        fail_reasons=(
            "REQUIRED_EPP_MISSING",
            "SOURCE_DATA_UNAVAILABLE",
            "CHECK_DISABLED",
        ),
    ),
)
WARNING_TEMPLATES = (
    WarningTemplate(
        affected_check="availability",
        source="availability",
        severity="warning",
        freshness="not_applicable",
        fallback=None,
        unavailable_code="ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        unavailable_quality="unavailable",
        disabled_code="ELIGIBILITY_CHECK_DISABLED",
        disabled_quality="disabled",
        impact="Availability verification is disabled; the Technician is ineligible.",
    ),
    WarningTemplate(
        affected_check="certifications",
        source="certifications",
        severity="warning",
        freshness="not_applicable",
        fallback=None,
        unavailable_code="ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        unavailable_quality="unavailable",
        disabled_code="ELIGIBILITY_CHECK_DISABLED",
        disabled_quality="disabled",
        impact="Certification verification is disabled; the Technician is ineligible.",
    ),
    WarningTemplate(
        affected_check="shift",
        source="shift",
        severity="warning",
        freshness="not_applicable",
        fallback=None,
        unavailable_code="ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        unavailable_quality="unavailable",
        disabled_code="ELIGIBILITY_CHECK_DISABLED",
        disabled_quality="disabled",
        impact="Shift verification is disabled; the Technician is ineligible.",
    ),
    WarningTemplate(
        affected_check="maximum_workday",
        source="maximum_workday",
        severity="warning",
        freshness="not_applicable",
        fallback=None,
        unavailable_code="ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        unavailable_quality="unavailable",
        disabled_code="ELIGIBILITY_CHECK_DISABLED",
        disabled_quality="disabled",
        impact="Maximum-workday verification is disabled; the Technician is ineligible.",
    ),
    WarningTemplate(
        affected_check="driving_limit",
        source="driving_limit",
        severity="warning",
        freshness="not_applicable",
        fallback=None,
        unavailable_code="ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        unavailable_quality="unavailable",
        disabled_code="ELIGIBILITY_CHECK_DISABLED",
        disabled_quality="disabled",
        impact="Driving safety could not be proven; the Technician is ineligible.",
    ),
    WarningTemplate(
        affected_check="required_epp",
        source="required_epp",
        severity="warning",
        freshness="not_applicable",
        fallback=None,
        unavailable_code="ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
        unavailable_quality="unavailable",
        disabled_code="ELIGIBILITY_CHECK_DISABLED",
        disabled_quality="disabled",
        impact="Required protective equipment could not be proven; the Technician is ineligible.",
    ),
)
WARNING_IMPACTS = tuple(
    (template.affected_check, template.impact)
    for template in WARNING_TEMPLATES
)
REASON_CODES_BY_CHECK = (
    (
        "availability",
        (
            "TECHNICIAN_AVAILABLE",
            "TECHNICIAN_UNAVAILABLE",
            "CHECK_DISABLED",
        ),
    ),
    (
        "certifications",
        (
            "ALL_CERTIFICATIONS_PRESENT",
            "NO_CERTIFICATIONS_REQUIRED",
            "CERTIFICATIONS_MISSING",
            "CHECK_DISABLED",
        ),
    ),
    (
        "shift",
        (
            "WITHIN_SHIFT",
            "OUTSIDE_SHIFT",
            "SHIFT_END_EXCEEDED",
            "CHECK_DISABLED",
        ),
    ),
    (
        "maximum_workday",
        (
            "WITHIN_MAXIMUM_WORKDAY",
            "MAXIMUM_WORKDAY_EXCEEDED",
            "CHECK_DISABLED",
        ),
    ),
    (
        "driving_limit",
        (
            "WITHIN_DRIVING_LIMIT",
            "DRIVING_LIMIT_EXCEEDED",
            "SOURCE_DATA_UNAVAILABLE",
            "CHECK_DISABLED",
        ),
    ),
    (
        "required_epp",
        (
            "EPP_PRESENT",
            "EPP_NOT_REQUIRED_FOR_PRIORITY",
            "REQUIRED_EPP_MISSING",
            "SOURCE_DATA_UNAVAILABLE",
            "CHECK_DISABLED",
        ),
    ),
)
WARNING_CODES = (
    "ELIGIBILITY_SOURCE_DATA_UNAVAILABLE",
    "ELIGIBILITY_CHECK_DISABLED",
)


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _registry_snapshot() -> dict[str, object]:
    configuration = asdict(ELIGIBILITY_CONFIGURATION)
    configuration["check_order"] = list(ELIGIBILITY_CONFIGURATION.check_order)
    return {
        "configuration": configuration,
        "formula_rules": [asdict(rule) for rule in FORMULA_RULES],
        "warning_templates": [asdict(template) for template in WARNING_TEMPLATES],
        "reason_codes_by_check": {
            check: list(reasons) for check, reasons in REASON_CODES_BY_CHECK
        },
        "warning_codes": list(WARNING_CODES),
        "candidate_rule": "eligible iff every configured check status is pass",
        "partition_rule": (
            "candidate ids are unique/sorted and exactly partition into "
            "eligible/ineligible; no_feasible iff eligible is empty"
        ),
        "ordering_rule": "technician UUID ascending; checks use check_order",
    }


ELIGIBILITY_REGISTRY_JSON = canonical_json(_registry_snapshot())
ELIGIBILITY_REGISTRY_SHA256 = hashlib.sha256(
    ELIGIBILITY_REGISTRY_JSON.encode("utf-8")
).hexdigest()

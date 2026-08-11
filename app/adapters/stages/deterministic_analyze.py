import re
import unicodedata
from typing import Any

from app.contracts.stages.analyze import (
    AnalyzeInputV1,
    SuppliedDispatchRequirementsV1,
)
from app.domain.analysis.rules import (
    ANALYSIS_CONFIGURATION_VERSION,
    CATEGORY_RULES,
    CONFLICT_WARNING_IMPACTS,
    DEFAULTS,
    DEFAULT_WARNING_IMPACTS,
    PRIORITY_SLA_MINUTES,
    CategoryRule,
)


FIELD_ORDER = (
    "category",
    "priority",
    "sla_target_minutes",
    "required_certifications",
    "estimated_service_duration_minutes",
)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


def _matches(normalized_text: str) -> list[CategoryRule]:
    return [
        rule
        for rule in CATEGORY_RULES
        if any(_contains(normalized_text, phrase) for phrase in rule.phrases)
    ]


def _priority(rule: CategoryRule, text: str) -> int:
    for condition in rule.priority_conditions:
        any_matches = not condition.any_phrases or any(
            _contains(text, phrase) for phrase in condition.any_phrases
        )
        all_match = all(
            _contains(text, phrase) for phrase in condition.all_phrases
        )
        if any_matches and all_match:
            return condition.priority
    return rule.base_priority


def _certifications(rule: CategoryRule, text: str) -> list[str]:
    values = list(rule.certifications)
    for condition in rule.conditional_certifications:
        if any(_contains(text, phrase) for phrase in condition.any_phrases):
            values.extend(condition.certifications)
    return sorted(set(values))


def _warning(
    *,
    code: str,
    field: str,
    source: str,
    quality: str,
    fallback: Any,
    rule_ids: list[str],
) -> dict[str, Any]:
    canonical_rule_ids = sorted(set(rule_ids))
    if quality == "defaulted":
        source = (
            ",".join(canonical_rule_ids)
            if canonical_rule_ids
            else "analysis-v1"
        )
    return {
        "code": code,
        "severity": "warning",
        "affected_field": field,
        "source": source,
        "quality": quality,
        "freshness": "not_applicable",
        "fallback": fallback,
        "impact": (
            CONFLICT_WARNING_IMPACTS[field]
            if quality == "conflicting"
            else DEFAULT_WARNING_IMPACTS[field]
        ),
        "rule_ids": canonical_rule_ids,
    }


class DeterministicAnalyzeStage:
    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        validated = AnalyzeInputV1.model_validate(payload)
        work_order = validated.work_order
        text = _normalize(work_order.incident_text)
        matches = _matches(text)
        supplied_raw = (
            (work_order.context or {}).get("dispatch_requirements") or {}
        )
        supplied = SuppliedDispatchRequirementsV1.model_validate(supplied_raw)
        supplied_values = supplied.model_dump(exclude_none=True, mode="json")

        inferred: dict[str, Any] = {}
        rules: dict[str, str] = {}
        category_issue: str | None = None
        selected_rule: CategoryRule | None = None
        if len(matches) == 1:
            selected_rule = matches[0]
        elif len(matches) > 1 and "category" in supplied_values:
            resolved = [
                rule
                for rule in matches
                if rule.category == supplied_values["category"]
            ]
            if len(resolved) == 1:
                selected_rule = resolved[0]

        if selected_rule is not None:
            rule = selected_rule
            inferred = {
                "category": rule.category,
                "priority": _priority(rule, text),
                "required_certifications": _certifications(rule, text),
                "estimated_service_duration_minutes": rule.duration_minutes,
            }
            rules = {
                field: rule.rule_id
                for field in (
                    "category",
                    "priority",
                    "required_certifications",
                    "estimated_service_duration_minutes",
                )
            }
        elif len(matches) > 1:
            category_issue = "ANALYZE_AMBIGUOUS_CATEGORY"
            critical_matches = [
                rule for rule in matches if _priority(rule, text) == 5
            ]
            if len(critical_matches) == 1:
                inferred["priority"] = 5
                rules["priority"] = critical_matches[0].rule_id
        else:
            category_issue = "ANALYZE_UNSUPPORTED_INCIDENT"

        if "priority" in supplied_values:
            inferred["sla_target_minutes"] = PRIORITY_SLA_MINUTES[
                supplied_values["priority"]
            ]
        elif "priority" in inferred:
            inferred["sla_target_minutes"] = PRIORITY_SLA_MINUTES[
                inferred["priority"]
            ]
        else:
            inferred["sla_target_minutes"] = PRIORITY_SLA_MINUTES[
                DEFAULTS["priority"]
            ]
        rules["sla_target_minutes"] = "priority_sla_v1"

        requirements: dict[str, Any] = {}
        provenance: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        for field in FIELD_ORDER:
            if field in supplied_values:
                value = supplied_values[field]
                requirements[field] = (
                    sorted(set(value))
                    if field == "required_certifications"
                    else value
                )
                provenance.append(
                    {
                        "field": field,
                        "kind": "supplied",
                        "source_field": f"/context/dispatch_requirements/{field}",
                    }
                )
                if field in inferred and requirements[field] != inferred[field]:
                    warnings.append(
                        _warning(
                            code="ANALYZE_SUPPLIED_CONFLICT",
                            field=field,
                            source=f"/context/dispatch_requirements/{field}",
                            quality="conflicting",
                            fallback=None,
                            rule_ids=[rules[field]],
                        )
                    )
                elif (
                    field == "category"
                    and matches
                    and requirements[field]
                    not in {rule.category for rule in matches}
                ):
                    warnings.append(
                        _warning(
                            code="ANALYZE_SUPPLIED_CONFLICT",
                            field=field,
                            source=f"/context/dispatch_requirements/{field}",
                            quality="conflicting",
                            fallback=None,
                            rule_ids=[rule.rule_id for rule in matches],
                        )
                    )
                continue

            if field in inferred and not (
                category_issue is not None
                and field
                in (
                    "category",
                    "required_certifications",
                    "estimated_service_duration_minutes",
                )
            ):
                requirements[field] = inferred[field]
                provenance.append(
                    {
                        "field": field,
                        "kind": "inferred",
                        "rule_id": rules[field],
                        "configuration_version": ANALYSIS_CONFIGURATION_VERSION,
                    }
                )
                continue

            if field == "sla_target_minutes":
                value = PRIORITY_SLA_MINUTES[requirements["priority"]]
            else:
                value = DEFAULTS[field]
                if field == "required_certifications":
                    value = list(value)
            requirements[field] = value
            provenance.append(
                {
                    "field": field,
                    "kind": "defaulted",
                    "rule_id": f"default_{field}_v1",
                    "configuration_version": ANALYSIS_CONFIGURATION_VERSION,
                }
            )
            code = (
                category_issue
                if field == "category" and category_issue is not None
                else "ANALYZE_DEFAULT_APPLIED"
            )
            warnings.append(
                _warning(
                    code=code,
                    field=field,
                    source=(
                        ",".join(rule.rule_id for rule in matches)
                        if matches
                        else "analysis-v1"
                    ),
                    quality="defaulted",
                    fallback=value,
                    rule_ids=[rule.rule_id for rule in matches],
                )
            )

        warnings.sort(
            key=lambda item: (
                item["affected_field"],
                item["code"],
                item["source"],
            )
        )
        return {
            "schema_version": "v1",
            "configuration_version": ANALYSIS_CONFIGURATION_VERSION,
            "requirements": requirements,
            "provenance": provenance,
            "warnings": warnings,
            "adapter_metadata": {
                "kind": "local",
                "provider": None,
                "model": None,
            },
        }

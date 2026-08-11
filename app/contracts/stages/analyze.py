from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field, model_validator

from app.contracts.common import StrictContract
from app.domain.analysis.rules import (
    CATEGORY_RULE_IDS,
    CONFLICT_WARNING_IMPACTS,
    DEFAULT_RULE_IDS,
    DEFAULT_WARNING_IMPACTS,
    INFERRED_RULE_IDS_BY_FIELD,
)


Category = Literal[
    "gas",
    "electricity",
    "telecommunications",
    "plumbing",
    "hvac",
    "maintenance",
]
Certification = Literal[
    "gas_registered",
    "electrician_category_a",
    "wan_networks",
    "fiber_optics",
    "working_at_height",
    "licensed_plumber",
    "high_pressure_refrigerants",
]
AnalyzeField = Literal[
    "category",
    "priority",
    "sla_target_minutes",
    "required_certifications",
    "estimated_service_duration_minutes",
]


class SuppliedDispatchRequirementsV1(StrictContract):
    category: Category | None = None
    priority: int | None = Field(default=None, strict=True, ge=1, le=5)
    sla_target_minutes: int | None = Field(
        default=None, strict=True, ge=1, le=10080
    )
    required_certifications: list[Certification] | None = Field(
        default=None, max_length=16
    )
    estimated_service_duration_minutes: int | None = Field(
        default=None, strict=True, ge=15, le=1440
    )

    @model_validator(mode="after")
    def unique_certifications(self):
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError("supplied dispatch fields cannot be null")
        if self.required_certifications is not None and len(
            set(self.required_certifications)
        ) != len(self.required_certifications):
            raise ValueError("required_certifications must be unique")
        return self


class AnalyzeWorkOrderInputV1(StrictContract):
    incident_text: str
    address: str
    zone: str
    context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_dispatch_requirements(self):
        if self.context is None:
            return self
        supplied = self.context.get("dispatch_requirements")
        if supplied is not None:
            SuppliedDispatchRequirementsV1.model_validate(supplied)
        return self


class AnalyzeInputV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["analysis-v1"] = "analysis-v1"
    work_order: AnalyzeWorkOrderInputV1


class DispatchRequirementsV1(StrictContract):
    category: Category
    priority: int = Field(strict=True, ge=1, le=5)
    sla_target_minutes: int = Field(strict=True, ge=1, le=10080)
    required_certifications: list[Certification] = Field(max_length=16)
    estimated_service_duration_minutes: int = Field(strict=True, ge=15, le=1440)

    @model_validator(mode="after")
    def canonical_certifications(self):
        if self.required_certifications != sorted(set(self.required_certifications)):
            raise ValueError("required_certifications must be unique and sorted")
        return self


class SuppliedProvenanceV1(StrictContract):
    field: AnalyzeField
    kind: Literal["supplied"]
    source_field: str

    @model_validator(mode="after")
    def source_matches_field(self):
        if self.source_field != f"/context/dispatch_requirements/{self.field}":
            raise ValueError("supplied provenance source_field must match field")
        return self


class InferredProvenanceV1(StrictContract):
    field: AnalyzeField
    kind: Literal["inferred"]
    rule_id: str
    configuration_version: Literal["analysis-v1"]


class DefaultedProvenanceV1(StrictContract):
    field: AnalyzeField
    kind: Literal["defaulted"]
    rule_id: str
    configuration_version: Literal["analysis-v1"]


ProvenanceV1 = Annotated[
    SuppliedProvenanceV1 | InferredProvenanceV1 | DefaultedProvenanceV1,
    Field(discriminator="kind"),
]


class DataQualityWarningV1(StrictContract):
    code: Literal[
        "ANALYZE_DEFAULT_APPLIED",
        "ANALYZE_AMBIGUOUS_CATEGORY",
        "ANALYZE_UNSUPPORTED_INCIDENT",
        "ANALYZE_SUPPLIED_CONFLICT",
    ]
    severity: Literal["warning"]
    affected_field: AnalyzeField
    source: str
    quality: Literal["defaulted", "conflicting"]
    freshness: Literal["not_applicable"]
    fallback: Category | int | list[Certification] | None
    impact: str
    rule_ids: list[str]

    @model_validator(mode="after")
    def canonical_rule_ids(self):
        if self.rule_ids != sorted(set(self.rule_ids)):
            raise ValueError("warning rule_ids must be unique and sorted")
        if not set(self.rule_ids).issubset(
            CATEGORY_RULE_IDS | {"priority_sla_v1"}
        ):
            raise ValueError("warning contains an unknown rule_id")
        return self


class AnalyzeAdapterMetadataV1(StrictContract):
    kind: Literal["local", "llm"]
    provider: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def llm_metadata_required(self):
        if self.kind == "llm" and (not self.provider or not self.model):
            raise ValueError("LLM adapter metadata requires provider and model")
        if self.kind == "local" and (self.provider is not None or self.model is not None):
            raise ValueError("Local adapter metadata cannot name provider or model")
        return self


class AnalyzeOutputV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    configuration_version: Literal["analysis-v1"] = "analysis-v1"
    requirements: DispatchRequirementsV1
    provenance: list[ProvenanceV1]
    warnings: list[DataQualityWarningV1]
    adapter_metadata: AnalyzeAdapterMetadataV1

    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="after")
    def complete_and_ordered_provenance(self):
        expected = [
            "category",
            "priority",
            "sla_target_minutes",
            "required_certifications",
            "estimated_service_duration_minutes",
        ]
        if [item.field for item in self.provenance] != expected:
            raise ValueError("provenance must contain each required field in order")
        for item in self.provenance:
            if item.kind == "inferred" and item.rule_id not in (
                INFERRED_RULE_IDS_BY_FIELD[item.field]
            ):
                raise ValueError("inferred provenance rule is invalid for field")
            if item.kind == "defaulted" and item.rule_id != DEFAULT_RULE_IDS[
                item.field
            ]:
                raise ValueError("default provenance rule is invalid for field")
        warning_order = [
            (item.affected_field, item.code, item.source) for item in self.warnings
        ]
        if warning_order != sorted(warning_order):
            raise ValueError("warnings must use canonical order")
        warning_keys = [
            (item.affected_field, item.code, item.source) for item in self.warnings
        ]
        if len(warning_keys) != len(set(warning_keys)):
            raise ValueError("warnings must be unique")
        requirements = self.requirements.model_dump(mode="json")
        warnings_by_field = {
            field: [
                warning
                for warning in self.warnings
                if warning.affected_field == field
            ]
            for field in expected
        }
        for item in self.provenance:
            if item.kind == "defaulted":
                field_warnings = warnings_by_field[item.field]
                if len(field_warnings) != 1:
                    raise ValueError("defaulted provenance requires one warning")
                warning = field_warnings[0]
                if warning.quality != "defaulted":
                    raise ValueError("default warning quality is invalid")
                if warning.fallback != requirements[item.field]:
                    raise ValueError("default warning fallback must match requirement")
                expected_code = "ANALYZE_DEFAULT_APPLIED"
                if item.field == "category":
                    expected_code = (
                        "ANALYZE_AMBIGUOUS_CATEGORY"
                        if len(warning.rule_ids) > 1
                        else "ANALYZE_UNSUPPORTED_INCIDENT"
                    )
                if warning.code != expected_code:
                    raise ValueError("default warning code is inconsistent")
                if warning.impact != DEFAULT_WARNING_IMPACTS[item.field]:
                    raise ValueError("default warning impact is not canonical")
                expected_source = (
                    ",".join(warning.rule_ids)
                    if warning.rule_ids
                    else "analysis-v1"
                )
                if warning.source != expected_source:
                    raise ValueError("default warning source is not canonical")
            elif item.kind == "inferred":
                if warnings_by_field[item.field]:
                    raise ValueError("inferred fields cannot carry warnings")
            else:
                field_warnings = warnings_by_field[item.field]
                if len(field_warnings) > 1:
                    raise ValueError("supplied fields allow at most one warning")
                if field_warnings:
                    warning = field_warnings[0]
                    if (
                        warning.code != "ANALYZE_SUPPLIED_CONFLICT"
                        or warning.quality != "conflicting"
                        or warning.fallback is not None
                        or warning.source != item.source_field
                        or not warning.rule_ids
                        or warning.impact
                        != CONFLICT_WARNING_IMPACTS[item.field]
                    ):
                        raise ValueError("supplied conflict warning is inconsistent")
        return self

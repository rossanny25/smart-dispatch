from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class AnalysisCategory(StrEnum):
    GAS = "gas"
    ELECTRICITY = "electricity"
    TELECOMMUNICATIONS = "telecommunications"
    PLUMBING = "plumbing"
    HVAC = "hvac"
    MAINTENANCE = "maintenance"


class CertificationCode(StrEnum):
    GAS_REGISTERED = "gas_registered"
    ELECTRICIAN_CATEGORY_A = "electrician_category_a"
    WAN_NETWORKS = "wan_networks"
    FIBER_OPTICS = "fiber_optics"
    WORKING_AT_HEIGHT = "working_at_height"
    LICENSED_PLUMBER = "licensed_plumber"
    HIGH_PRESSURE_REFRIGERANTS = "high_pressure_refrigerants"


@dataclass(frozen=True)
class DispatchRequirements:
    category: AnalysisCategory
    priority: int
    sla_target_minutes: int
    required_certifications: tuple[CertificationCode, ...]
    estimated_service_duration_minutes: int


@dataclass(frozen=True)
class FieldProvenance:
    field: str
    kind: str
    source_field: str | None = None
    rule_id: str | None = None
    configuration_version: str | None = None


@dataclass(frozen=True)
class DataQualityWarning:
    code: str
    severity: str
    affected_field: str
    source: str
    quality: str
    freshness: str
    fallback: Any
    impact: str


@dataclass(frozen=True)
class AnalyzeAdapterMetadata:
    kind: str
    provider: str | None = None
    model: str | None = None


@dataclass(frozen=True)
class AnalyzeResult:
    schema_version: str
    configuration_version: str
    requirements: DispatchRequirements
    provenance: tuple[FieldProvenance, ...]
    warnings: tuple[DataQualityWarning, ...]
    adapter_metadata: AnalyzeAdapterMetadata


@dataclass(frozen=True)
class ConfigurationVersion:
    version: str
    contract_version: str
    registry_json: str
    registry_sha256: str
    created_at: datetime


@dataclass(frozen=True)
class WorkOrderAnalysis:
    id: UUID
    work_order_id: str
    schema_version: str
    configuration_version: str
    input_hash: str
    output_json: str
    category: str
    priority: int
    sla_target_minutes: int
    required_certifications_json: str
    estimated_service_duration_minutes: int
    created_at: datetime

    def output(self) -> dict[str, Any]:
        import json

        return json.loads(self.output_json)

from dataclasses import asdict, dataclass
import hashlib
import json
from types import MappingProxyType


ANALYSIS_CONFIGURATION_VERSION = "analysis-v1"
ANALYZE_CONTRACT_VERSION = "v1"
CONFIGURATION_CREATED_AT = "2026-07-28T00:00:00Z"


@dataclass(frozen=True)
class PriorityCondition:
    priority: int
    any_phrases: tuple[str, ...] = ()
    all_phrases: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConditionalCertification:
    certifications: tuple[str, ...]
    any_phrases: tuple[str, ...]


@dataclass(frozen=True)
class CategoryRule:
    rule_id: str
    category: str
    phrases: tuple[str, ...]
    base_priority: int
    priority_conditions: tuple[PriorityCondition, ...]
    certifications: tuple[str, ...]
    conditional_certifications: tuple[ConditionalCertification, ...]
    duration_minutes: int


CATEGORY_RULES = (
    CategoryRule(
        rule_id="category_gas_v1",
        category="gas",
        phrases=("gas", "fuga", "caldera"),
        base_priority=4,
        priority_conditions=(
            PriorityCondition(priority=5, any_phrases=("fuga",)),
        ),
        certifications=("gas_registered",),
        conditional_certifications=(),
        duration_minutes=90,
    ),
    CategoryRule(
        rule_id="category_electricity_v1",
        category="electricity",
        phrases=(
            "luz",
            "electricidad",
            "electrico",
            "termica",
            "tension",
            "cortocircuito",
        ),
        base_priority=3,
        priority_conditions=(
            PriorityCondition(
                priority=5,
                any_phrases=("fuego", "cortocircuito"),
            ),
            PriorityCondition(priority=4, any_phrases=("corte", "urgente")),
        ),
        certifications=("electrician_category_a",),
        conditional_certifications=(),
        duration_minutes=120,
    ),
    CategoryRule(
        rule_id="category_telecommunications_v1",
        category="telecommunications",
        phrases=("internet", "enlace", "fibra", "red", "servidor"),
        base_priority=3,
        priority_conditions=(
            PriorityCondition(
                priority=5,
                all_phrases=("servidor", "critico"),
            ),
            PriorityCondition(
                priority=4,
                any_phrases=("urgente", "sin servicio", "no conecta"),
            ),
        ),
        certifications=("wan_networks",),
        conditional_certifications=(
            ConditionalCertification(
                certifications=("fiber_optics", "working_at_height"),
                any_phrases=("fibra", "altura"),
            ),
        ),
        duration_minutes=60,
    ),
    CategoryRule(
        rule_id="category_plumbing_v1",
        category="plumbing",
        phrases=("agua", "cano", "inundacion", "bano", "plomeria"),
        base_priority=4,
        priority_conditions=(
            PriorityCondition(
                priority=5,
                all_phrases=("inundacion", "riesgo"),
            ),
        ),
        certifications=("licensed_plumber",),
        conditional_certifications=(),
        duration_minutes=90,
    ),
    CategoryRule(
        rule_id="category_hvac_v1",
        category="hvac",
        phrases=("aire acondicionado", "frio", "hvac", "climatizacion"),
        base_priority=3,
        priority_conditions=(),
        certifications=("high_pressure_refrigerants",),
        conditional_certifications=(),
        duration_minutes=120,
    ),
    CategoryRule(
        rule_id="category_maintenance_v1",
        category="maintenance",
        phrases=("mantenimiento", "inspeccion", "preventivo", "rutina"),
        base_priority=1,
        priority_conditions=(),
        certifications=(),
        conditional_certifications=(),
        duration_minutes=60,
    ),
)

PRIORITY_SLA_MINUTES = MappingProxyType(
    {1: 10080, 2: 2880, 3: 720, 4: 240, 5: 60}
)

DEFAULTS = MappingProxyType(
    {
        "category": "maintenance",
        "priority": 3,
        "required_certifications": (),
        "estimated_service_duration_minutes": 60,
    }
)

DEFAULT_WARNING_IMPACTS = MappingProxyType(
    {
        "category": "May under-specify the service specialty; dispatcher review required.",
        "priority": "Medium urgency assumed; dispatcher must verify operational impact.",
        "sla_target_minutes": "A response budget derived from the assumed priority is used.",
        "required_certifications": "No specialty certification inferred; eligibility may be broader than intended.",
        "estimated_service_duration_minutes": "One-hour service duration assumed; schedule feasibility may change after review.",
    }
)

CONFLICT_WARNING_IMPACTS = MappingProxyType(
    {
        "category": "The supplied category differs from deterministic incident rules; dispatcher verification is required.",
        "priority": "The supplied priority differs from deterministic incident rules; dispatcher verification is required.",
        "sla_target_minutes": "The supplied SLA differs from the priority registry; dispatcher verification is required.",
        "required_certifications": "The supplied certifications differ from the category registry; dispatcher verification is required.",
        "estimated_service_duration_minutes": "The supplied duration differs from the category registry; dispatcher verification is required.",
    }
)

CERTIFICATION_LABELS = MappingProxyType(
    {
        "gas_registered": "Gasista Matriculado",
        "electrician_category_a": "Técnico Electricista Categoría A",
        "wan_networks": "Redes WAN",
        "fiber_optics": "Fibra Óptica",
        "working_at_height": "Seguridad en Alturas",
        "licensed_plumber": "Plomero Matriculado",
        "high_pressure_refrigerants": "Refrigerantes de Alta Presión",
    }
)

CATEGORY_RULE_IDS = frozenset(rule.rule_id for rule in CATEGORY_RULES)
DEFAULT_RULE_IDS = MappingProxyType(
    {
        field: f"default_{field}_v1"
        for field in (
            "category",
            "priority",
            "sla_target_minutes",
            "required_certifications",
            "estimated_service_duration_minutes",
        )
    }
)
INFERRED_RULE_IDS_BY_FIELD = MappingProxyType(
    {
        "category": CATEGORY_RULE_IDS,
        "priority": CATEGORY_RULE_IDS,
        "sla_target_minutes": frozenset({"priority_sla_v1"}),
        "required_certifications": CATEGORY_RULE_IDS,
        "estimated_service_duration_minutes": CATEGORY_RULE_IDS,
    }
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
    return {
        "version": ANALYSIS_CONFIGURATION_VERSION,
        "contract_version": ANALYZE_CONTRACT_VERSION,
        "categories": [rule.category for rule in CATEGORY_RULES],
        "category_rules": [asdict(rule) for rule in CATEGORY_RULES],
        "priority_sla_minutes": dict(PRIORITY_SLA_MINUTES),
        "defaults": {
            **DEFAULTS,
            "required_certifications": list(
                DEFAULTS["required_certifications"]
            ),
        },
        "certification_labels": dict(CERTIFICATION_LABELS),
        "default_warning_impacts": dict(DEFAULT_WARNING_IMPACTS),
        "conflict_warning_impacts": dict(CONFLICT_WARNING_IMPACTS),
    }


ANALYSIS_REGISTRY_JSON = canonical_json(_registry_snapshot())
ANALYSIS_REGISTRY_SHA256 = hashlib.sha256(
    ANALYSIS_REGISTRY_JSON.encode("utf-8")
).hexdigest()

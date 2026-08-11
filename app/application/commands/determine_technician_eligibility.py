from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.application.ports.persistence import (
    PersistenceAdapterError,
    UnitOfWorkFactory,
)
from app.contracts.eligibility import EligibilityInputV1, EligibilityOutputV1
from app.contracts.eligibility import validate_output_against_input
from app.contracts.stages.analyze import AnalyzeInputV1, AnalyzeOutputV1
from app.domain.analysis.models import ConfigurationVersion
from app.domain.analysis.rules import (
    ANALYSIS_REGISTRY_JSON,
    ANALYSIS_REGISTRY_SHA256,
)
from app.domain.eligibility.models import EligibilityEvaluationSet
from app.domain.eligibility.policy import EligibilityPolicy
from app.domain.eligibility.rules import (
    ELIGIBILITY_CONFIGURATION,
    ELIGIBILITY_CONFIGURATION_CREATED_AT,
    ELIGIBILITY_CONFIGURATION_VERSION,
    ELIGIBILITY_CONTRACT_VERSION,
    ELIGIBILITY_REGISTRY_JSON,
    ELIGIBILITY_REGISTRY_SHA256,
    canonical_json,
)


class AnalysisNotFound(RuntimeError):
    """The retained Analyze evidence does not exist."""


class InvalidEligibilityInput(RuntimeError):
    """Eligibility input cannot satisfy the versioned contract."""


class InvalidEligibilityOutput(RuntimeError):
    """The policy produced output outside the eligibility contract."""


class EligibilityPolicyFailure(RuntimeError):
    """The eligibility policy failed without leaking internal details."""


class EligibilityPersistenceError(RuntimeError):
    """Eligibility evidence could not be read or committed safely."""


@dataclass(frozen=True)
class DetermineTechnicianEligibilityRequest:
    analysis_id: str
    captured_at: datetime
    technicians: tuple[dict[str, Any], ...]
    configuration_version: str = ELIGIBILITY_CONFIGURATION_VERSION


@dataclass(frozen=True)
class DetermineTechnicianEligibilityResult:
    evaluation_set_id: str
    output: dict[str, Any]
    replayed: bool


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class DetermineTechnicianEligibility:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        uuid_factory: Callable[[], UUID],
        clock: Callable[[], datetime],
        policy_factory: Callable[
            [], EligibilityPolicy
        ] = lambda: EligibilityPolicy(ELIGIBILITY_CONFIGURATION),
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._uuid_factory = uuid_factory
        self._clock = clock
        self._policy_factory = policy_factory

    def execute(
        self,
        request: DetermineTechnicianEligibilityRequest,
    ) -> DetermineTechnicianEligibilityResult:
        if request.configuration_version != ELIGIBILITY_CONFIGURATION_VERSION:
            raise InvalidEligibilityInput
        try:
            with self._unit_of_work_factory() as unit_of_work:
                analysis = unit_of_work.analyses.get_by_id(request.analysis_id)
                if analysis is None:
                    raise AnalysisNotFound
                work_order = unit_of_work.work_orders.get(
                    analysis.work_order_id
                )
                if work_order is None:
                    raise EligibilityPersistenceError
                analysis_configuration = unit_of_work.configurations.get(
                    analysis.configuration_version
                )
                if (
                    analysis_configuration is None
                    or analysis_configuration.registry_json
                    != ANALYSIS_REGISTRY_JSON
                    or analysis_configuration.registry_sha256
                    != ANALYSIS_REGISTRY_SHA256
                    or analysis_configuration.contract_version != "v1"
                ):
                    raise EligibilityPersistenceError
                try:
                    analyze_input = AnalyzeInputV1.model_validate(
                        {
                            "schema_version": "v1",
                            "configuration_version": (
                                analysis.configuration_version
                            ),
                            "work_order": {
                                "incident_text": work_order.incident_text,
                                "address": work_order.address,
                                "zone": work_order.zone,
                                "context": work_order.context,
                            },
                        }
                    )
                    analyze_input_hash = hashlib.sha256(
                        canonical_json(
                            analyze_input.model_dump(mode="json")
                        ).encode("utf-8")
                    ).hexdigest()
                    if analyze_input_hash != analysis.input_hash:
                        raise EligibilityPersistenceError
                    analysis_output = AnalyzeOutputV1.model_validate_json(
                        analysis.output_json
                    )
                    requirements = analysis_output.requirements
                    input_model = EligibilityInputV1.model_validate(
                        {
                            "schema_version": "v1",
                            "configuration_version": (
                                request.configuration_version
                            ),
                            "requirements": {
                                "priority": requirements.priority,
                                "required_certifications": (
                                    requirements.required_certifications
                                ),
                                "estimated_service_duration_minutes": (
                                    requirements
                                    .estimated_service_duration_minutes
                                ),
                            },
                            "captured_at": request.captured_at,
                            "technicians": list(request.technicians),
                        }
                    )
                except ValidationError as error:
                    raise InvalidEligibilityInput from error
                input_payload = input_model.model_dump(mode="json")
                input_json = canonical_json(input_payload)
                input_hash = hashlib.sha256(
                    input_json.encode("utf-8")
                ).hexdigest()

                configuration = unit_of_work.configurations.get(
                    request.configuration_version
                )
                if configuration is None:
                    unit_of_work.configurations.add(
                        ConfigurationVersion(
                            version=ELIGIBILITY_CONFIGURATION_VERSION,
                            contract_version=ELIGIBILITY_CONTRACT_VERSION,
                            registry_json=ELIGIBILITY_REGISTRY_JSON,
                            registry_sha256=ELIGIBILITY_REGISTRY_SHA256,
                            created_at=_parse_utc(
                                ELIGIBILITY_CONFIGURATION_CREATED_AT
                            ),
                        )
                    )
                elif (
                    configuration.registry_json != ELIGIBILITY_REGISTRY_JSON
                    or configuration.registry_sha256
                    != ELIGIBILITY_REGISTRY_SHA256
                    or configuration.contract_version
                    != ELIGIBILITY_CONTRACT_VERSION
                ):
                    raise EligibilityPersistenceError

                existing = unit_of_work.eligibility_evaluations.get_by_input_json(
                    request.analysis_id,
                    request.configuration_version,
                    input_json,
                )
                if existing is None:
                    existing = unit_of_work.eligibility_evaluations.get(
                        request.analysis_id,
                        request.configuration_version,
                        input_hash,
                    )
                if existing is not None:
                    if (
                        existing.work_order_id != analysis.work_order_id
                        or existing.input_json != input_json
                    ):
                        raise EligibilityPersistenceError
                    try:
                        output = EligibilityOutputV1.model_validate_json(
                            existing.output_json
                        ).model_dump(mode="json")
                    except ValidationError as error:
                        raise EligibilityPersistenceError from error
                    return DetermineTechnicianEligibilityResult(
                        evaluation_set_id=str(existing.id),
                        output=output,
                        replayed=True,
                    )

                try:
                    domain_result = self._policy_factory().evaluate(
                        requirements=input_model.to_domain_requirements(),
                        captured_at=input_model.captured_at,
                        technicians=input_model.to_domain_technicians(),
                    )
                except Exception as error:
                    raise EligibilityPolicyFailure from error
                try:
                    output_model = EligibilityOutputV1.from_domain(domain_result)
                    validate_output_against_input(input_model, output_model)
                except (ValidationError, ValueError) as error:
                    raise InvalidEligibilityOutput from error
                output = output_model.model_dump(mode="json")
                output_json = canonical_json(output)
                try:
                    created_at = self._clock()
                    evaluation_id = self._uuid_factory()
                except Exception as error:
                    raise EligibilityPersistenceError from error
                if (
                    created_at.tzinfo is None
                    or created_at.utcoffset() != UTC.utcoffset(created_at)
                    or not isinstance(evaluation_id, UUID)
                ):
                    raise EligibilityPersistenceError
                unit_of_work.eligibility_evaluations.add(
                    EligibilityEvaluationSet(
                        id=evaluation_id,
                        work_order_id=analysis.work_order_id,
                        work_order_analysis_id=request.analysis_id,
                        schema_version=output_model.schema_version,
                        configuration_version=request.configuration_version,
                        input_hash=input_hash,
                        input_json=input_json,
                        output_json=output_json,
                        candidate_count=len(output_model.candidates),
                        eligible_count=len(
                            output_model.eligible_technician_ids
                        ),
                        ineligible_count=len(
                            output_model.ineligible_technician_ids
                        ),
                        no_feasible_candidates=(
                            output_model.no_feasible_candidates
                        ),
                        created_at=created_at,
                    )
                )
                return DetermineTechnicianEligibilityResult(
                    evaluation_set_id=str(evaluation_id),
                    output=output,
                    replayed=False,
                )
        except (
            AnalysisNotFound,
            InvalidEligibilityInput,
            InvalidEligibilityOutput,
            EligibilityPolicyFailure,
            EligibilityPersistenceError,
        ):
            raise
        except (PersistenceAdapterError, TypeError, ValueError) as error:
            raise EligibilityPersistenceError from error

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
from app.contracts.scoring import (
    ScoringInputV1,
    ScoringOutputV1,
    ScoringQualitySupplementsV1,
    validate_output_against_input,
)
from app.contracts.stages.analyze import AnalyzeInputV1, AnalyzeOutputV1
from app.domain.analysis.models import ConfigurationVersion
from app.domain.analysis.rules import (
    ANALYSIS_REGISTRY_JSON,
    ANALYSIS_REGISTRY_SHA256,
)
from app.domain.eligibility.rules import (
    ELIGIBILITY_REGISTRY_JSON,
    ELIGIBILITY_REGISTRY_SHA256,
)
from app.domain.scoring.models import ScoringEvaluationSet
from app.domain.scoring.policy import ScoringPolicy
from app.domain.scoring.rules import (
    SCORING_CONFIGURATION,
    SCORING_CONFIGURATION_CREATED_AT,
    SCORING_CONFIGURATION_VERSION,
    SCORING_CONTRACT_VERSION,
    SCORING_REGISTRY_JSON,
    SCORING_REGISTRY_SHA256,
    canonical_json,
)


class EligibilityEvaluationNotFound(RuntimeError):
    """The retained eligibility evidence does not exist."""


class InvalidScoringInput(RuntimeError):
    """Scoring input cannot satisfy the versioned contract."""


class InvalidScoringOutput(RuntimeError):
    """The policy produced output outside the scoring contract."""


class ScoringPolicyFailure(RuntimeError):
    """The scoring policy failed without leaking internal details."""


class ScoringPersistenceError(RuntimeError):
    """Scoring evidence could not be read or committed safely."""


@dataclass(frozen=True)
class ScoreEligibleTechniciansRequest:
    eligibility_evaluation_set_id: str
    technician_quality: tuple[object, ...]
    configuration_version: str = SCORING_CONFIGURATION_VERSION


@dataclass(frozen=True)
class ScoreEligibleTechniciansResult:
    evaluation_set_id: str
    output: dict[str, Any]
    replayed: bool


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("configuration timestamp must be UTC")
    return parsed


class ScoreEligibleTechnicians:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        uuid_factory: Callable[[], UUID],
        clock: Callable[[], datetime],
        policy_factory: Callable[[], ScoringPolicy] = lambda: ScoringPolicy(
            SCORING_CONFIGURATION
        ),
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._uuid_factory = uuid_factory
        self._clock = clock
        self._policy_factory = policy_factory

    def execute(
        self,
        request: ScoreEligibleTechniciansRequest,
    ) -> ScoreEligibleTechniciansResult:
        if request.configuration_version != SCORING_CONFIGURATION_VERSION:
            raise InvalidScoringInput
        try:
            quality_snapshot = ScoringQualitySupplementsV1.model_validate(
                {"technicians": request.technician_quality}
            )
        except (ValidationError, TypeError, ValueError) as error:
            raise InvalidScoringInput from error
        try:
            with self._unit_of_work_factory() as unit_of_work:
                eligibility = unit_of_work.eligibility_evaluations.get_by_id(
                    request.eligibility_evaluation_set_id
                )
                if eligibility is None:
                    raise EligibilityEvaluationNotFound
                eligibility_configuration = unit_of_work.configurations.get(
                    eligibility.configuration_version
                )
                if (
                    eligibility_configuration is None
                    or eligibility_configuration.registry_json
                    != ELIGIBILITY_REGISTRY_JSON
                    or eligibility_configuration.registry_sha256
                    != ELIGIBILITY_REGISTRY_SHA256
                    or eligibility_configuration.contract_version != "v1"
                ):
                    raise ScoringPersistenceError

                analysis = unit_of_work.analyses.get_by_id(
                    eligibility.work_order_analysis_id
                )
                if (
                    analysis is None
                    or analysis.work_order_id != eligibility.work_order_id
                ):
                    raise ScoringPersistenceError
                work_order = unit_of_work.work_orders.get(analysis.work_order_id)
                analysis_configuration = unit_of_work.configurations.get(
                    analysis.configuration_version
                )
                if (
                    work_order is None
                    or analysis_configuration is None
                    or analysis_configuration.registry_json
                    != ANALYSIS_REGISTRY_JSON
                    or analysis_configuration.registry_sha256
                    != ANALYSIS_REGISTRY_SHA256
                    or analysis_configuration.contract_version != "v1"
                ):
                    raise ScoringPersistenceError
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
                    analysis_output = AnalyzeOutputV1.model_validate_json(
                        analysis.output_json
                    )
                    eligibility_input = (
                        EligibilityInputV1.model_validate_json(
                            eligibility.input_json
                        )
                    )
                    eligibility_output = (
                        EligibilityOutputV1.model_validate_json(
                            eligibility.output_json
                        )
                    )
                except ValidationError as error:
                    raise ScoringPersistenceError from error
                analyze_hash = hashlib.sha256(
                    canonical_json(
                        analyze_input.model_dump(mode="json")
                    ).encode("utf-8")
                ).hexdigest()
                if analyze_hash != analysis.input_hash:
                    raise ScoringPersistenceError
                requirements = analysis_output.requirements
                if (
                    eligibility_input.requirements.priority
                    != requirements.priority
                    or eligibility_input.requirements.required_certifications
                    != requirements.required_certifications
                    or eligibility_input.requirements
                    .estimated_service_duration_minutes
                    != requirements.estimated_service_duration_minutes
                ):
                    raise ScoringPersistenceError

                quality_items = quality_snapshot.technicians
                quality_ids = [
                    str(item.technician_id) for item in quality_items
                ]
                roster_ids = [
                    str(item.technician_id)
                    for item in eligibility_input.technicians
                ]
                if quality_ids != roster_ids:
                    raise InvalidScoringInput
                quality_by_id = {
                    str(item.technician_id): item.quality_rating_0_to_5
                    for item in quality_items
                }
                if len(quality_by_id) != len(roster_ids):
                    raise InvalidScoringInput
                input_model = ScoringInputV1.model_validate(
                    {
                        "schema_version": "v1",
                        "configuration_version": request.configuration_version,
                        "eligibility_evaluation_set_id": str(eligibility.id),
                        "sla_minutes": requirements.sla_target_minutes,
                        "eligibility_output": eligibility_output.model_dump(
                            mode="json"
                        ),
                        "technicians": tuple(
                            {
                                "technician_id": str(item.technician_id),
                                "eta_minutes": item.estimated_travel_minutes,
                                "distance_meters": item.distance_meters,
                                "projected_work_minutes": (
                                    item.assigned_work_minutes
                                    + item.estimated_travel_minutes
                                    + requirements
                                    .estimated_service_duration_minutes
                                ),
                                "quality_rating_0_to_5": quality_by_id[
                                    str(item.technician_id)
                                ],
                            }
                            for item in eligibility_input.technicians
                        ),
                    }
                )
                input_json = canonical_json(
                    input_model.model_dump(mode="json")
                )
                input_hash = hashlib.sha256(
                    input_json.encode("utf-8")
                ).hexdigest()

                configuration = unit_of_work.configurations.get(
                    request.configuration_version
                )
                if configuration is None:
                    unit_of_work.configurations.add(
                        ConfigurationVersion(
                            version=SCORING_CONFIGURATION_VERSION,
                            contract_version=SCORING_CONTRACT_VERSION,
                            registry_json=SCORING_REGISTRY_JSON,
                            registry_sha256=SCORING_REGISTRY_SHA256,
                            created_at=_parse_utc(
                                SCORING_CONFIGURATION_CREATED_AT
                            ),
                        )
                    )
                elif (
                    configuration.registry_json != SCORING_REGISTRY_JSON
                    or configuration.registry_sha256
                    != SCORING_REGISTRY_SHA256
                    or configuration.contract_version
                    != SCORING_CONTRACT_VERSION
                ):
                    raise ScoringPersistenceError

                existing = unit_of_work.scoring_evaluations.get_by_input_json(
                    str(eligibility.id),
                    request.configuration_version,
                    input_json,
                )
                if existing is None:
                    existing = unit_of_work.scoring_evaluations.get(
                        str(eligibility.id),
                        request.configuration_version,
                        input_hash,
                    )
                if existing is not None:
                    if existing.input_json != input_json:
                        raise ScoringPersistenceError
                    output = ScoringOutputV1.model_validate_json(
                        existing.output_json
                    ).model_dump(mode="json")
                    return ScoreEligibleTechniciansResult(
                        evaluation_set_id=str(existing.id),
                        output=output,
                        replayed=True,
                    )

                try:
                    domain_result = self._policy_factory().evaluate(
                        sla_minutes=input_model.sla_minutes,
                        technicians=(
                            input_model.to_domain_eligible_technicians()
                        ),
                    )
                except Exception as error:
                    raise ScoringPolicyFailure from error
                try:
                    output_model = ScoringOutputV1.from_domain(
                        domain_result,
                        ineligible_candidates=[
                            item
                            for item in eligibility_output.candidates
                            if not item.eligible
                        ],
                    )
                    validate_output_against_input(input_model, output_model)
                except (
                    ValidationError,
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    IndexError,
                ) as error:
                    raise InvalidScoringOutput from error
                output = output_model.model_dump(mode="json")
                output_json = canonical_json(output)
                try:
                    created_at = self._clock()
                    evaluation_id = self._uuid_factory()
                except Exception as error:
                    raise ScoringPersistenceError from error
                if (
                    type(created_at) is not datetime
                    or created_at.tzinfo is None
                    or created_at.utcoffset() != UTC.utcoffset(created_at)
                    or not isinstance(evaluation_id, UUID)
                ):
                    raise ScoringPersistenceError
                top = (
                    output_model.eligible_candidates[0]
                    if output_model.eligible_candidates
                    else None
                )
                unit_of_work.scoring_evaluations.add(
                    ScoringEvaluationSet(
                        id=evaluation_id,
                        eligibility_evaluation_set_id=eligibility.id,
                        schema_version=output_model.schema_version,
                        configuration_version=request.configuration_version,
                        input_hash=input_hash,
                        input_json=input_json,
                        output_json=output_json,
                        candidate_count=len(input_model.technicians),
                        eligible_count=len(
                            output_model.eligible_candidates
                        ),
                        ineligible_count=len(
                            output_model.ineligible_candidates
                        ),
                        top_technician_id=(
                            None if top is None else top.technician_id
                        ),
                        top_objective_score=(
                            None if top is None else top.objective_score
                        ),
                        created_at=created_at,
                    )
                )
                return ScoreEligibleTechniciansResult(
                    evaluation_set_id=str(evaluation_id),
                    output=output,
                    replayed=False,
                )
        except (
            EligibilityEvaluationNotFound,
            InvalidScoringInput,
            InvalidScoringOutput,
            ScoringPolicyFailure,
            ScoringPersistenceError,
        ):
            raise
        except ValidationError as error:
            raise InvalidScoringInput from error
        except (PersistenceAdapterError, TypeError, ValueError) as error:
            raise ScoringPersistenceError from error

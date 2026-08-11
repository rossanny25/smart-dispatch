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
from app.contracts.confidence import (
    ConfidenceInputV1,
    ConfidenceOutputV1,
    evaluate_input,
    validate_output_against_input,
)
from app.contracts.scoring import ScoringOutputV1
from app.domain.analysis.models import ConfigurationVersion
from app.domain.confidence.models import ConfidenceEvaluationSet
from app.domain.confidence.rules import (
    CONFIDENCE_CONFIGURATION_CREATED_AT,
    CONFIDENCE_CONFIGURATION_VERSION,
    CONFIDENCE_CONTRACT_VERSION,
    CONFIDENCE_REGISTRY_JSON,
    CONFIDENCE_REGISTRY_SHA256,
)
from app.domain.scoring.rules import (
    SCORING_REGISTRY_JSON,
    SCORING_REGISTRY_SHA256,
    canonical_json,
)


class ScoringEvaluationNotFound(RuntimeError):
    """The retained scoring evidence does not exist."""


class InvalidConfidenceInput(RuntimeError):
    """Confidence input cannot satisfy its versioned contract."""


class InvalidConfidenceOutput(RuntimeError):
    """Confidence output is inconsistent with its input."""


class ConfidencePolicyFailure(RuntimeError):
    """Confidence policy failed without leaking internal details."""


class ConfidencePersistenceError(RuntimeError):
    """Confidence evidence could not be read or persisted safely."""


@dataclass(frozen=True)
class EvaluateRecommendationConfidenceRequest:
    scoring_evaluation_set_id: str
    evaluated_at: datetime
    gps_observations: tuple[object, ...]
    traffic_observed_at: datetime | None
    weather_observed_at: datetime | None
    active_supporting_episode_count: int
    configuration_version: str = CONFIDENCE_CONFIGURATION_VERSION


@dataclass(frozen=True)
class EvaluateRecommendationConfidenceResult:
    evaluation_set_id: str
    output: dict[str, Any]
    replayed: bool


def _configuration_time() -> datetime:
    return datetime.fromisoformat(
        CONFIDENCE_CONFIGURATION_CREATED_AT.replace("Z", "+00:00")
    )


class EvaluateRecommendationConfidence:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        uuid_factory: Callable[[], UUID],
        clock: Callable[[], datetime],
        evaluator: Callable[[ConfidenceInputV1], object] = evaluate_input,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._uuid_factory = uuid_factory
        self._clock = clock
        self._evaluator = evaluator

    def execute(
        self, request: EvaluateRecommendationConfidenceRequest
    ) -> EvaluateRecommendationConfidenceResult:
        if request.configuration_version != CONFIDENCE_CONFIGURATION_VERSION:
            raise InvalidConfidenceInput
        try:
            with self._unit_of_work_factory() as unit_of_work:
                scoring = unit_of_work.scoring_evaluations.get_by_id(
                    request.scoring_evaluation_set_id
                )
                if scoring is None:
                    raise ScoringEvaluationNotFound
                scoring_configuration = unit_of_work.configurations.get(
                    scoring.configuration_version
                )
                if (
                    scoring_configuration is None
                    or scoring_configuration.registry_json
                    != SCORING_REGISTRY_JSON
                    or scoring_configuration.registry_sha256
                    != SCORING_REGISTRY_SHA256
                    or scoring_configuration.contract_version != "v1"
                ):
                    raise ConfidencePersistenceError
                scoring_output = ScoringOutputV1.model_validate_json(
                    scoring.output_json
                )
                scoring_output_json = canonical_json(
                    scoring_output.model_dump(mode="json")
                )
                if scoring_output_json != scoring.output_json:
                    raise ConfidencePersistenceError
                scoring_output_sha256 = hashlib.sha256(
                    scoring_output_json.encode("utf-8")
                ).hexdigest()
                candidates = scoring_output.eligible_candidates
                try:
                    input_model = ConfidenceInputV1.model_validate(
                        {
                            "schema_version": "v1",
                            "configuration_version": request.configuration_version,
                            "scoring_evaluation_set_id": str(scoring.id),
                            "scoring_output_sha256": scoring_output_sha256,
                            "evaluated_at": request.evaluated_at,
                            "candidates": tuple(
                                {
                                    "technician_id": str(item.technician_id),
                                    "rank": item.rank,
                                    "objective_score": item.objective_score,
                                }
                                for item in candidates
                            ),
                            "gps_observations": request.gps_observations,
                            "traffic": {
                                "observed_at": request.traffic_observed_at,
                                "default_fallback": "seeded-normal",
                            },
                            "weather": {
                                "observed_at": request.weather_observed_at,
                                "default_fallback": "seeded-clear",
                            },
                            "active_supporting_episode_count": (
                                request.active_supporting_episode_count
                            ),
                        }
                    )
                except (ValidationError, TypeError, ValueError) as error:
                    raise InvalidConfidenceInput from error

                input_json = canonical_json(input_model.model_dump(mode="json"))
                input_hash = hashlib.sha256(input_json.encode()).hexdigest()
                configuration = unit_of_work.configurations.get(
                    request.configuration_version
                )
                if configuration is None:
                    unit_of_work.configurations.add(
                        ConfigurationVersion(
                            version=CONFIDENCE_CONFIGURATION_VERSION,
                            contract_version=CONFIDENCE_CONTRACT_VERSION,
                            registry_json=CONFIDENCE_REGISTRY_JSON,
                            registry_sha256=CONFIDENCE_REGISTRY_SHA256,
                            created_at=_configuration_time(),
                        )
                    )
                elif (
                    configuration.registry_json != CONFIDENCE_REGISTRY_JSON
                    or configuration.registry_sha256
                    != CONFIDENCE_REGISTRY_SHA256
                    or configuration.contract_version
                    != CONFIDENCE_CONTRACT_VERSION
                ):
                    raise ConfidencePersistenceError

                existing = unit_of_work.confidence_evaluations.get_by_input_json(
                    str(scoring.id), request.configuration_version, input_json
                )
                if existing is None:
                    existing = unit_of_work.confidence_evaluations.get(
                        str(scoring.id),
                        request.configuration_version,
                        input_hash,
                    )
                if existing is not None:
                    if existing.input_json != input_json:
                        raise ConfidencePersistenceError
                    output = ConfidenceOutputV1.model_validate_json(
                        existing.output_json
                    )
                    validate_output_against_input(
                        input_model, output, scoring_output
                    )
                    return EvaluateRecommendationConfidenceResult(
                        evaluation_set_id=str(existing.id),
                        output=output.model_dump(mode="json"),
                        replayed=True,
                    )

                try:
                    domain_result = self._evaluator(input_model)
                except Exception as error:
                    raise ConfidencePolicyFailure from error
                try:
                    output_model = ConfidenceOutputV1.from_domain(
                        domain_result, scoring_output
                    )
                    validate_output_against_input(
                        input_model, output_model, scoring_output
                    )
                except (
                    ValidationError,
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    IndexError,
                ) as error:
                    raise InvalidConfidenceOutput from error
                try:
                    evaluation_id = self._uuid_factory()
                    created_at = self._clock()
                except Exception as error:
                    raise ConfidencePersistenceError from error
                if (
                    not isinstance(evaluation_id, UUID)
                    or type(created_at) is not datetime
                    or created_at.tzinfo is None
                    or created_at.utcoffset() != UTC.utcoffset(created_at)
                ):
                    raise ConfidencePersistenceError
                output_json = canonical_json(output_model.model_dump(mode="json"))
                unit_of_work.confidence_evaluations.add(
                    ConfidenceEvaluationSet(
                        id=evaluation_id,
                        scoring_evaluation_set_id=scoring.id,
                        schema_version=output_model.schema_version,
                        configuration_version=request.configuration_version,
                        input_hash=input_hash,
                        input_json=input_json,
                        output_json=output_json,
                        eligible_count=len(input_model.candidates),
                        source_count=len(output_model.sources),
                        warning_count=len(output_model.warnings),
                        recommended_technician_id=(
                            output_model.recommended_technician_id
                        ),
                        confidence_value=output_model.confidence_value,
                        confidence_label=output_model.confidence_label,
                        created_at=created_at,
                    )
                )
                return EvaluateRecommendationConfidenceResult(
                    evaluation_set_id=str(evaluation_id),
                    output=output_model.model_dump(mode="json"),
                    replayed=False,
                )
        except (
            ScoringEvaluationNotFound,
            InvalidConfidenceInput,
            InvalidConfidenceOutput,
            ConfidencePolicyFailure,
            ConfidencePersistenceError,
        ):
            raise
        except ValidationError as error:
            raise InvalidConfidenceInput from error
        except (PersistenceAdapterError, TypeError, ValueError) as error:
            raise ConfidencePersistenceError from error

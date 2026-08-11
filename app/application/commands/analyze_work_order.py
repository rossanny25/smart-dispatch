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
from app.application.ports.stages import AnalyzeStage
from app.contracts.stages.analyze import AnalyzeInputV1, AnalyzeOutputV1
from app.domain.analysis.models import ConfigurationVersion, WorkOrderAnalysis
from app.domain.analysis.rules import (
    ANALYSIS_CONFIGURATION_VERSION,
    ANALYSIS_REGISTRY_JSON,
    ANALYSIS_REGISTRY_SHA256,
    ANALYZE_CONTRACT_VERSION,
    CONFIGURATION_CREATED_AT,
    canonical_json,
)


class WorkOrderNotFound(RuntimeError):
    """The requested captured Work Order does not exist."""


class InvalidAnalyzeInput(RuntimeError):
    """Captured input cannot satisfy the versioned Analyze contract."""


class InvalidAnalyzeOutput(RuntimeError):
    """The configured stage proposed an invalid result."""


class AnalyzeStageFailure(RuntimeError):
    """The configured stage failed without exposing adapter details."""


class AnalyzePersistenceError(RuntimeError):
    """Analyze evidence could not be read or committed safely."""


@dataclass(frozen=True)
class AnalyzeWorkOrderRequest:
    work_order_id: str
    configuration_version: str = ANALYSIS_CONFIGURATION_VERSION


@dataclass(frozen=True)
class AnalyzeWorkOrderResult:
    analysis_id: str
    output: dict[str, Any]
    replayed: bool


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class AnalyzeWorkOrder:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        stage: AnalyzeStage,
        uuid_factory: Callable[[], UUID],
        clock: Callable[[], datetime],
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._stage = stage
        self._uuid_factory = uuid_factory
        self._clock = clock

    def execute(self, request: AnalyzeWorkOrderRequest) -> AnalyzeWorkOrderResult:
        if request.configuration_version != ANALYSIS_CONFIGURATION_VERSION:
            raise InvalidAnalyzeInput
        try:
            with self._unit_of_work_factory() as unit_of_work:
                work_order = unit_of_work.work_orders.get(request.work_order_id)
                if work_order is None:
                    raise WorkOrderNotFound
                try:
                    input_model = AnalyzeInputV1.model_validate(
                        {
                            "schema_version": "v1",
                            "configuration_version": request.configuration_version,
                            "work_order": {
                                "incident_text": work_order.incident_text,
                                "address": work_order.address,
                                "zone": work_order.zone,
                                "context": work_order.context,
                            },
                        }
                    )
                except ValidationError as error:
                    raise InvalidAnalyzeInput from error
                input_payload = input_model.model_dump(mode="json")
                input_hash = hashlib.sha256(
                    canonical_json(input_payload).encode("utf-8")
                ).hexdigest()
                existing = unit_of_work.analyses.get(
                    request.work_order_id,
                    request.configuration_version,
                )
                configuration = unit_of_work.configurations.get(
                    request.configuration_version
                )
                if configuration is None:
                    if existing is not None:
                        raise AnalyzePersistenceError
                    unit_of_work.configurations.add(
                        ConfigurationVersion(
                            version=ANALYSIS_CONFIGURATION_VERSION,
                            contract_version=ANALYZE_CONTRACT_VERSION,
                            registry_json=ANALYSIS_REGISTRY_JSON,
                            registry_sha256=ANALYSIS_REGISTRY_SHA256,
                            created_at=_parse_utc(CONFIGURATION_CREATED_AT),
                        )
                    )
                elif (
                    configuration.registry_json != ANALYSIS_REGISTRY_JSON
                    or configuration.registry_sha256 != ANALYSIS_REGISTRY_SHA256
                    or configuration.contract_version != ANALYZE_CONTRACT_VERSION
                ):
                    raise AnalyzePersistenceError

                if existing is not None:
                    if existing.input_hash != input_hash:
                        raise AnalyzePersistenceError
                    try:
                        output = AnalyzeOutputV1.model_validate_json(
                            existing.output_json
                        ).model_dump(mode="json")
                    except ValidationError as error:
                        raise AnalyzePersistenceError from error
                    return AnalyzeWorkOrderResult(
                        analysis_id=str(existing.id),
                        output=output,
                        replayed=True,
                    )

                try:
                    proposed = self._stage.execute(input_payload)
                    validated = AnalyzeOutputV1.model_validate(proposed)
                except ValidationError as error:
                    raise InvalidAnalyzeOutput from error
                except Exception as error:
                    raise AnalyzeStageFailure from error
                output = validated.model_dump(mode="json")
                output_json = canonical_json(output)
                analysis_id = self._uuid_factory()
                created_at = self._clock()
                if created_at.tzinfo is None:
                    raise AnalyzePersistenceError
                requirements = output["requirements"]
                unit_of_work.analyses.add(
                    WorkOrderAnalysis(
                        id=analysis_id,
                        work_order_id=str(work_order.id),
                        schema_version="v1",
                        configuration_version=request.configuration_version,
                        input_hash=input_hash,
                        output_json=output_json,
                        category=requirements["category"],
                        priority=requirements["priority"],
                        sla_target_minutes=requirements["sla_target_minutes"],
                        required_certifications_json=canonical_json(
                            requirements["required_certifications"]
                        ),
                        estimated_service_duration_minutes=requirements[
                            "estimated_service_duration_minutes"
                        ],
                        created_at=created_at,
                    )
                )
                return AnalyzeWorkOrderResult(
                    analysis_id=str(analysis_id),
                    output=output,
                    replayed=False,
                )
        except (
            InvalidAnalyzeInput,
            InvalidAnalyzeOutput,
            AnalyzeStageFailure,
            WorkOrderNotFound,
            AnalyzePersistenceError,
        ):
            raise
        except (PersistenceAdapterError, ValueError, TypeError) as error:
            raise AnalyzePersistenceError from error

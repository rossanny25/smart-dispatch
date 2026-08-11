from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self

from app.domain.analysis.models import ConfigurationVersion, WorkOrderAnalysis
from app.domain.eligibility.models import EligibilityEvaluationSet
from app.domain.scoring.models import ScoringEvaluationSet
from app.domain.confidence.models import ConfidenceEvaluationSet
from app.domain.dispatch.models import DispatchRun
from app.domain.work_orders.models import IdempotencyRecord, WorkOrder


class WorkOrderRepository(Protocol):
    def add(self, work_order: WorkOrder) -> None: ...

    def get(self, work_order_id: str) -> WorkOrder | None: ...


class IdempotencyRepository(Protocol):
    def get(self, route: str, key: str) -> IdempotencyRecord | None: ...

    def add(self, record: IdempotencyRecord) -> None: ...


class ConfigurationRepository(Protocol):
    def get(self, version: str) -> ConfigurationVersion | None: ...

    def add(self, configuration: ConfigurationVersion) -> None: ...


class WorkOrderAnalysisRepository(Protocol):
    def get(
        self,
        work_order_id: str,
        configuration_version: str,
    ) -> WorkOrderAnalysis | None: ...

    def add(self, analysis: WorkOrderAnalysis) -> None: ...

    def get_by_id(self, analysis_id: str) -> WorkOrderAnalysis | None: ...


class EligibilityEvaluationRepository(Protocol):
    def get(
        self,
        work_order_analysis_id: str,
        configuration_version: str,
        input_hash: str,
    ) -> EligibilityEvaluationSet | None: ...

    def get_by_input_json(
        self,
        work_order_analysis_id: str,
        configuration_version: str,
        input_json: str,
    ) -> EligibilityEvaluationSet | None: ...

    def add(self, evaluation: EligibilityEvaluationSet) -> None: ...

    def get_by_id(self, evaluation_id: str) -> EligibilityEvaluationSet | None: ...


class ScoringEvaluationRepository(Protocol):
    def get(
        self,
        eligibility_evaluation_set_id: str,
        configuration_version: str,
        input_hash: str,
    ) -> ScoringEvaluationSet | None: ...

    def get_by_input_json(
        self,
        eligibility_evaluation_set_id: str,
        configuration_version: str,
        input_json: str,
    ) -> ScoringEvaluationSet | None: ...

    def add(self, evaluation: ScoringEvaluationSet) -> None: ...

    def get_by_id(self, evaluation_id: str) -> ScoringEvaluationSet | None: ...


class ConfidenceEvaluationRepository(Protocol):
    def get(
        self,
        scoring_evaluation_set_id: str,
        configuration_version: str,
        input_hash: str,
    ) -> ConfidenceEvaluationSet | None: ...

    def get_by_input_json(
        self,
        scoring_evaluation_set_id: str,
        configuration_version: str,
        input_json: str,
    ) -> ConfidenceEvaluationSet | None: ...

    def add(self, evaluation: ConfidenceEvaluationSet) -> None: ...


class DispatchRunRepository(Protocol):
    def get(self, run_id: str) -> DispatchRun | None: ...

    def create(
        self,
        run: DispatchRun,
        *,
        snapshot: dict,
        transition: dict,
    ) -> None: ...

    def advance(
        self,
        run: DispatchRun,
        *,
        expected_state: str,
        expected_revision: int,
        snapshot: dict | None,
        execution: dict,
        transition: dict,
    ) -> None: ...


class UnitOfWork(Protocol):
    work_orders: WorkOrderRepository
    idempotency: IdempotencyRepository
    configurations: ConfigurationRepository
    analyses: WorkOrderAnalysisRepository
    eligibility_evaluations: EligibilityEvaluationRepository
    scoring_evaluations: ScoringEvaluationRepository
    confidence_evaluations: ConfidenceEvaluationRepository
    dispatch_runs: DispatchRunRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]


class PersistenceAdapterError(RuntimeError):
    """A sanitized failure reported by a concrete persistence adapter."""


class ConcurrentIdempotencyWrite(PersistenceAdapterError):
    """Another transaction won the route/key uniqueness race."""

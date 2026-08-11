from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.commands.analyze_work_order import (
    AnalyzeWorkOrder,
    AnalyzeWorkOrderRequest,
    InvalidAnalyzeOutput,
    WorkOrderNotFound,
)
from app.domain.work_orders.models import WorkOrder
from app.application.ports.persistence import PersistenceAdapterError


WORK_ORDER = WorkOrder(
    id=UUID("11111111-1111-4111-8111-111111111111"),
    schema_version="v1",
    raw_input={
        "incident_text": "Fuga de gas",
        "address": "Calle 1",
        "zone": "Centro",
        "context": None,
    },
    incident_text="Fuga de gas",
    address="Calle 1",
    zone="Centro",
    context=None,
    created_at=datetime(2026, 7, 28, tzinfo=UTC),
)


class Rows:
    work_order = WORK_ORDER
    analyses = []
    configurations = {}


class WorkOrders:
    def get(self, work_order_id):
        return Rows.work_order if work_order_id == str(WORK_ORDER.id) else None


class Analyses:
    def get(self, work_order_id, configuration_version):
        return next(
            (
                row
                for row in Rows.analyses
                if row.work_order_id == work_order_id
                and row.configuration_version == configuration_version
            ),
            None,
        )

    def add(self, analysis):
        Rows.analyses.append(analysis)


class Configurations:
    def get(self, version):
        return Rows.configurations.get(version)

    def add(self, configuration):
        Rows.configurations[configuration.version] = configuration


class Uow:
    work_orders = WorkOrders()
    analyses = Analyses()
    configurations = Configurations()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def command(stage=None):
    Rows.analyses = []
    Rows.configurations = {}
    return AnalyzeWorkOrder(
        unit_of_work_factory=Uow,
        stage=stage or DeterministicAnalyzeStage(),
        uuid_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        clock=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    )


def test_command_persists_and_replays_one_validated_analysis() -> None:
    use_case = command()
    request = AnalyzeWorkOrderRequest(work_order_id=str(WORK_ORDER.id))

    first = use_case.execute(request)
    replay = use_case.execute(request)

    assert first.replayed is False
    assert replay.replayed is True
    assert first.output == replay.output
    assert len(Rows.analyses) == 1


def test_command_rejects_missing_work_order() -> None:
    with pytest.raises(WorkOrderNotFound):
        command().execute(AnalyzeWorkOrderRequest(work_order_id="missing"))


class InvalidStage:
    def execute(self, payload):
        return {"schema_version": "v1"}


def test_invalid_stage_output_is_rejected_before_persistence() -> None:
    with pytest.raises(InvalidAnalyzeOutput):
        command(InvalidStage()).execute(
            AnalyzeWorkOrderRequest(work_order_id=str(WORK_ORDER.id))
        )
    assert Rows.analyses == []


class CrashingStage:
    def execute(self, payload):
        raise RuntimeError("provider details")


def test_stage_runtime_failure_is_sanitized_and_typed() -> None:
    from app.application.commands.analyze_work_order import AnalyzeStageFailure

    with pytest.raises(AnalyzeStageFailure) as captured:
        command(CrashingStage()).execute(
            AnalyzeWorkOrderRequest(work_order_id=str(WORK_ORDER.id))
        )
    assert str(captured.value) == ""
    assert Rows.analyses == []


def test_invalid_supplied_context_is_a_typed_input_failure() -> None:
    from app.application.commands.analyze_work_order import InvalidAnalyzeInput

    original = Rows.work_order
    Rows.work_order = WorkOrder(
        **{
            **original.__dict__,
            "context": {"dispatch_requirements": {"priority": True}},
        }
    )
    try:
        with pytest.raises(InvalidAnalyzeInput):
            command().execute(
                AnalyzeWorkOrderRequest(work_order_id=str(WORK_ORDER.id))
            )
        assert Rows.analyses == []
    finally:
        Rows.work_order = original


class FailingUow:
    def __enter__(self):
        raise PersistenceAdapterError

    def __exit__(self, *args):
        return False


def test_adapter_persistence_failure_is_sanitized() -> None:
    from app.application.commands.analyze_work_order import AnalyzePersistenceError

    use_case = AnalyzeWorkOrder(
        unit_of_work_factory=FailingUow,
        stage=DeterministicAnalyzeStage(),
        uuid_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        clock=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    )

    with pytest.raises(AnalyzePersistenceError):
        use_case.execute(AnalyzeWorkOrderRequest(work_order_id=str(WORK_ORDER.id)))

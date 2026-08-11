from datetime import UTC, datetime
import hashlib
from uuid import UUID

import pytest

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.commands.determine_technician_eligibility import (
    AnalysisNotFound,
    DetermineTechnicianEligibility,
    DetermineTechnicianEligibilityRequest,
    EligibilityPolicyFailure,
    InvalidEligibilityInput,
    InvalidEligibilityOutput,
)
from app.domain.analysis.models import ConfigurationVersion, WorkOrderAnalysis
from app.domain.analysis.rules import (
    ANALYSIS_REGISTRY_JSON,
    ANALYSIS_REGISTRY_SHA256,
    canonical_json,
)
from app.domain.eligibility.models import (
    EligibilityCandidate,
    EligibilityResult,
)
from app.domain.work_orders.models import WorkOrder


ANALYSIS_ID = UUID("22222222-2222-4222-8222-222222222222")
WORK_ORDER_ID = "11111111-1111-4111-8111-111111111111"
ANALYSIS_OUTPUT = DeterministicAnalyzeStage().execute(
    {
        "schema_version": "v1",
        "configuration_version": "analysis-v1",
        "work_order": {
            "incident_text": "Fuga de gas",
            "address": "Calle privada",
            "zone": "Centro",
            "context": None,
        },
    }
)
ANALYZE_INPUT = {
    "schema_version": "v1",
    "configuration_version": "analysis-v1",
    "work_order": {
        "incident_text": "Fuga de gas",
        "address": "Calle privada",
        "zone": "Centro",
        "context": None,
    },
}
WORK_ORDER = WorkOrder(
    id=UUID(WORK_ORDER_ID),
    schema_version="v1",
    raw_input={
        "incident_text": "Fuga de gas",
        "address": "Calle privada",
        "zone": "Centro",
        "context": None,
    },
    incident_text="Fuga de gas",
    address="Calle privada",
    zone="Centro",
    context=None,
    created_at=datetime(2026, 7, 28, tzinfo=UTC),
)
ANALYSIS = WorkOrderAnalysis(
    id=ANALYSIS_ID,
    work_order_id=WORK_ORDER_ID,
    schema_version="v1",
    configuration_version="analysis-v1",
    input_hash=hashlib.sha256(
        canonical_json(ANALYZE_INPUT).encode("utf-8")
    ).hexdigest(),
    output_json=canonical_json(ANALYSIS_OUTPUT),
    category="gas",
    priority=5,
    sla_target_minutes=60,
    required_certifications_json='["gas_registered"]',
    estimated_service_duration_minutes=90,
    created_at=datetime(2026, 7, 28, tzinfo=UTC),
)


class Rows:
    analysis = ANALYSIS
    configurations = {
        "analysis-v1": ConfigurationVersion(
            version="analysis-v1",
            contract_version="v1",
            registry_json=ANALYSIS_REGISTRY_JSON,
            registry_sha256=ANALYSIS_REGISTRY_SHA256,
            created_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
    }
    evaluations = []


class Analyses:
    def get_by_id(self, analysis_id):
        return Rows.analysis if analysis_id == str(ANALYSIS_ID) else None


class WorkOrders:
    def get(self, work_order_id):
        return WORK_ORDER if work_order_id == WORK_ORDER_ID else None


class Configurations:
    def get(self, version):
        return Rows.configurations.get(version)

    def add(self, configuration):
        Rows.configurations[configuration.version] = configuration


class Evaluations:
    def get(self, analysis_id, configuration_version, input_hash):
        return next(
            (
                item
                for item in Rows.evaluations
                if item.work_order_analysis_id == analysis_id
                and item.configuration_version == configuration_version
                and item.input_hash == input_hash
            ),
            None,
        )

    def add(self, evaluation):
        Rows.evaluations.append(evaluation)

    def get_by_input_json(self, analysis_id, configuration_version, input_json):
        return next(
            (
                item
                for item in Rows.evaluations
                if item.work_order_analysis_id == analysis_id
                and item.configuration_version == configuration_version
                and item.input_json == input_json
            ),
            None,
        )


class Uow:
    work_orders = WorkOrders()
    analyses = Analyses()
    configurations = Configurations()
    eligibility_evaluations = Evaluations()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def technician() -> dict:
    return {
        "technician_id": "33333333-3333-4333-8333-333333333333",
        "availability": "available",
        "certifications": ["gas_registered"],
        "shift_start": "2026-07-28T08:00:00Z",
        "shift_end": "2026-07-28T16:00:00Z",
        "assigned_work_minutes": 300,
        "accumulated_driving_minutes": 120,
        "has_required_epp": True,
        "estimated_travel_minutes": 30,
        "distance_meters": 60_000,
    }


def request(**changes) -> DetermineTechnicianEligibilityRequest:
    values = {
        "analysis_id": str(ANALYSIS_ID),
        "captured_at": datetime(2026, 7, 28, 12, tzinfo=UTC),
        "technicians": (technician(),),
    }
    values.update(changes)
    return DetermineTechnicianEligibilityRequest(**values)


def command(policy_factory=None) -> DetermineTechnicianEligibility:
    Rows.analysis = ANALYSIS
    Rows.configurations = {
        "analysis-v1": ConfigurationVersion(
            version="analysis-v1",
            contract_version="v1",
            registry_json=ANALYSIS_REGISTRY_JSON,
            registry_sha256=ANALYSIS_REGISTRY_SHA256,
            created_at=datetime(2026, 7, 28, tzinfo=UTC),
        )
    }
    Rows.evaluations = []
    arguments = {}
    if policy_factory is not None:
        arguments["policy_factory"] = policy_factory
    return DetermineTechnicianEligibility(
        unit_of_work_factory=Uow,
        uuid_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
        **arguments,
    )


def test_command_persists_and_replays_validated_evidence() -> None:
    use_case = command()
    first = use_case.execute(request())
    replay = use_case.execute(request())

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.output == first.output
    assert len(Rows.evaluations) == 1


def test_missing_analysis_and_invalid_clock_are_typed() -> None:
    use_case = command()
    with pytest.raises(AnalysisNotFound):
        use_case.execute(request(analysis_id="missing"))
    with pytest.raises(InvalidEligibilityInput):
        use_case.execute(
            request(captured_at=datetime(2026, 7, 28, 12))
        )


class CrashingPolicy:
    def evaluate(self, **kwargs):
        raise RuntimeError("private policy details")


def test_policy_failure_is_sanitized() -> None:
    with pytest.raises(EligibilityPolicyFailure) as captured:
        command(lambda: CrashingPolicy()).execute(request())
    assert str(captured.value) == ""
    assert Rows.evaluations == []


class MalformedPolicy:
    def evaluate(self, **kwargs):
        candidate = EligibilityCandidate(
            technician_id=UUID("33333333-3333-4333-8333-333333333333"),
            eligible=True,
            distance_meters=0,
            checks=(),
            warnings=(),
        )
        return EligibilityResult(
            schema_version="v1",
            configuration_version="eligibility-v1",
            candidates=(candidate,),
            eligible_technician_ids=(candidate.technician_id,),
            ineligible_technician_ids=(),
            no_feasible_candidates=False,
        )


def test_invalid_policy_output_is_rejected_before_persistence() -> None:
    with pytest.raises(InvalidEligibilityOutput):
        command(lambda: MalformedPolicy()).execute(request())
    assert Rows.evaluations == []


class OmittedRosterPolicy:
    def evaluate(self, **kwargs):
        return EligibilityResult(
            schema_version="v1",
            configuration_version="eligibility-v1",
            candidates=(),
            eligible_technician_ids=(),
            ineligible_technician_ids=(),
            no_feasible_candidates=True,
        )


def test_policy_cannot_omit_the_input_roster() -> None:
    with pytest.raises(InvalidEligibilityOutput):
        command(lambda: OmittedRosterPolicy()).execute(request())
    assert Rows.evaluations == []


@pytest.mark.parametrize(
    ("clock", "uuid_factory"),
    [
        (
            lambda: (_ for _ in ()).throw(RuntimeError("clock details")),
            lambda: UUID("44444444-4444-4444-8444-444444444444"),
        ),
        (
            lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
            lambda: (_ for _ in ()).throw(RuntimeError("uuid details")),
        ),
        (
            lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
            lambda: "not-a-uuid",
        ),
    ],
)
def test_clock_and_uuid_failures_are_sanitized(clock, uuid_factory) -> None:
    from app.application.commands.determine_technician_eligibility import (
        EligibilityPersistenceError,
    )

    use_case = command()
    use_case._clock = clock
    use_case._uuid_factory = uuid_factory
    with pytest.raises(EligibilityPersistenceError) as captured:
        use_case.execute(request())
    assert str(captured.value) == ""
    assert Rows.evaluations == []

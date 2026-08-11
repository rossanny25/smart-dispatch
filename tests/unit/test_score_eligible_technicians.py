from copy import deepcopy
from datetime import UTC, datetime
import hashlib
from uuid import UUID

import pytest

from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.commands.score_eligible_technicians import (
    EligibilityEvaluationNotFound,
    InvalidScoringInput,
    InvalidScoringOutput,
    ScoreEligibleTechnicians,
    ScoreEligibleTechniciansRequest,
    ScoringPersistenceError,
    ScoringPolicyFailure,
)
from app.contracts.eligibility import EligibilityInputV1, EligibilityOutputV1
from app.domain.analysis.models import ConfigurationVersion, WorkOrderAnalysis
from app.domain.analysis.rules import (
    ANALYSIS_REGISTRY_JSON,
    ANALYSIS_REGISTRY_SHA256,
)
from app.domain.eligibility.models import EligibilityEvaluationSet
from app.domain.eligibility.policy import EligibilityPolicy
from app.domain.eligibility.rules import (
    ELIGIBILITY_CONFIGURATION,
    ELIGIBILITY_REGISTRY_JSON,
    ELIGIBILITY_REGISTRY_SHA256,
)
from app.domain.scoring.rules import canonical_json
from app.domain.work_orders.models import WorkOrder


WORK_ORDER_ID = "11111111-1111-4111-8111-111111111111"
ANALYSIS_ID = UUID("22222222-2222-4222-8222-222222222222")
ELIGIBILITY_ID = UUID("55555555-5555-4555-8555-555555555555")
TECH_1 = "33333333-3333-4333-8333-333333333333"
TECH_2 = "44444444-4444-4444-8444-444444444444"
WORK_ORDER_INPUT = {
    "incident_text": "Fuga de gas",
    "address": "Calle privada",
    "zone": "Centro",
    "context": None,
}
ANALYZE_INPUT = {
    "schema_version": "v1",
    "configuration_version": "analysis-v1",
    "work_order": WORK_ORDER_INPUT,
}
ANALYZE_OUTPUT = DeterministicAnalyzeStage().execute(ANALYZE_INPUT)
WORK_ORDER = WorkOrder(
    id=UUID(WORK_ORDER_ID),
    schema_version="v1",
    raw_input=WORK_ORDER_INPUT,
    incident_text=WORK_ORDER_INPUT["incident_text"],
    address=WORK_ORDER_INPUT["address"],
    zone=WORK_ORDER_INPUT["zone"],
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
    output_json=canonical_json(ANALYZE_OUTPUT),
    category="gas",
    priority=5,
    sla_target_minutes=60,
    required_certifications_json='["gas_registered"]',
    estimated_service_duration_minutes=90,
    created_at=datetime(2026, 7, 28, tzinfo=UTC),
)
ELIGIBILITY_INPUT = EligibilityInputV1.model_validate(
    {
        "requirements": {
            "priority": 5,
            "required_certifications": ["gas_registered"],
            "estimated_service_duration_minutes": 90,
        },
        "captured_at": "2026-07-28T12:00:00Z",
        "technicians": [
            {
                "technician_id": TECH_1,
                "availability": "available",
                "certifications": ["gas_registered"],
                "shift_start": "2026-07-28T08:00:00Z",
                "shift_end": "2026-07-28T18:00:00Z",
                "assigned_work_minutes": 300,
                "accumulated_driving_minutes": 100,
                "has_required_epp": True,
                "estimated_travel_minutes": 30,
                "distance_meters": 60_000,
            },
            {
                "technician_id": TECH_2,
                "availability": "busy",
                "certifications": ["gas_registered"],
                "shift_start": "2026-07-28T08:00:00Z",
                "shift_end": "2026-07-28T18:00:00Z",
                "assigned_work_minutes": 100,
                "accumulated_driving_minutes": 20,
                "has_required_epp": True,
                "estimated_travel_minutes": 20,
                "distance_meters": 10_000,
            },
        ],
    }
)
ELIGIBILITY_OUTPUT = EligibilityOutputV1.from_domain(
    EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
        requirements=ELIGIBILITY_INPUT.to_domain_requirements(),
        captured_at=ELIGIBILITY_INPUT.captured_at,
        technicians=ELIGIBILITY_INPUT.to_domain_technicians(),
    )
)
ELIGIBILITY = EligibilityEvaluationSet(
    id=ELIGIBILITY_ID,
    work_order_id=WORK_ORDER_ID,
    work_order_analysis_id=str(ANALYSIS_ID),
    schema_version="v1",
    configuration_version="eligibility-v1",
    input_hash=hashlib.sha256(
        canonical_json(
            ELIGIBILITY_INPUT.model_dump(mode="json")
        ).encode("utf-8")
    ).hexdigest(),
    input_json=canonical_json(ELIGIBILITY_INPUT.model_dump(mode="json")),
    output_json=canonical_json(ELIGIBILITY_OUTPUT.model_dump(mode="json")),
    candidate_count=2,
    eligible_count=1,
    ineligible_count=1,
    no_feasible_candidates=False,
    created_at=datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
)


class Rows:
    eligibility = ELIGIBILITY
    configurations = {}
    scoring = []
    entered = 0


def _base_configurations():
    return {
        "analysis-v1": ConfigurationVersion(
            version="analysis-v1",
            contract_version="v1",
            registry_json=ANALYSIS_REGISTRY_JSON,
            registry_sha256=ANALYSIS_REGISTRY_SHA256,
            created_at=datetime(2026, 7, 28, tzinfo=UTC),
        ),
        "eligibility-v1": ConfigurationVersion(
            version="eligibility-v1",
            contract_version="v1",
            registry_json=ELIGIBILITY_REGISTRY_JSON,
            registry_sha256=ELIGIBILITY_REGISTRY_SHA256,
            created_at=datetime(2026, 7, 28, tzinfo=UTC),
        ),
    }


class EligibilityRows:
    def get_by_id(self, evaluation_id):
        if Rows.eligibility is not None and evaluation_id == str(
            Rows.eligibility.id
        ):
            return Rows.eligibility
        return None


class AnalysisRows:
    def get_by_id(self, analysis_id):
        return ANALYSIS if analysis_id == str(ANALYSIS_ID) else None


class WorkOrderRows:
    def get(self, work_order_id):
        return WORK_ORDER if work_order_id == WORK_ORDER_ID else None


class ConfigurationRows:
    def get(self, version):
        return Rows.configurations.get(version)

    def add(self, configuration):
        Rows.configurations[configuration.version] = configuration


class ScoringRows:
    def get(self, eligibility_id, configuration_version, input_hash):
        return next(
            (
                item
                for item in Rows.scoring
                if str(item.eligibility_evaluation_set_id) == eligibility_id
                and item.configuration_version == configuration_version
                and item.input_hash == input_hash
            ),
            None,
        )

    def get_by_input_json(
        self, eligibility_id, configuration_version, input_json
    ):
        return next(
            (
                item
                for item in Rows.scoring
                if str(item.eligibility_evaluation_set_id) == eligibility_id
                and item.configuration_version == configuration_version
                and item.input_json == input_json
            ),
            None,
        )

    def add(self, evaluation):
        Rows.scoring.append(evaluation)


class Uow:
    eligibility_evaluations = EligibilityRows()
    analyses = AnalysisRows()
    work_orders = WorkOrderRows()
    configurations = ConfigurationRows()
    scoring_evaluations = ScoringRows()

    def __enter__(self):
        Rows.entered += 1
        self._configurations = deepcopy(Rows.configurations)
        self._scoring = list(Rows.scoring)
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is not None:
            Rows.configurations = self._configurations
            Rows.scoring = self._scoring
        return False


def request(
    supplements=None,
) -> ScoreEligibleTechniciansRequest:
    return ScoreEligibleTechniciansRequest(
        eligibility_evaluation_set_id=str(ELIGIBILITY_ID),
        technician_quality=(
            supplements
            if supplements is not None
            else (
                {
                    "technician_id": TECH_1,
                    "quality_rating_0_to_5": "4",
                },
                {
                    "technician_id": TECH_2,
                    "quality_rating_0_to_5": None,
                },
            )
        ),
    )


def command(**changes) -> ScoreEligibleTechnicians:
    Rows.eligibility = ELIGIBILITY
    Rows.configurations = _base_configurations()
    Rows.scoring = []
    Rows.entered = 0
    arguments = {
        "unit_of_work_factory": Uow,
        "uuid_factory": lambda: UUID(
            "66666666-6666-4666-8666-666666666666"
        ),
        "clock": lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    }
    arguments.update(changes)
    return ScoreEligibleTechnicians(**arguments)


def test_command_persists_and_replays_exact_evidence() -> None:
    use_case = command()
    first = use_case.execute(request())
    replay = use_case.execute(request())
    assert first.replayed is False
    assert replay.replayed is True
    assert replay.output == first.output
    assert len(Rows.scoring) == 1


@pytest.mark.parametrize(
    "supplements",
    [
        (None,),
        ([],),
        (
            {
                "technician_id": TECH_1,
                "quality_rating_0_to_5": "4",
                "extra": "forbidden",
            },
        ),
        (
            {
                "technician_id": TECH_1,
                "quality_rating_0_to_5": "0." + ("0" * 5000) + "1",
            },
        ),
    ],
)
def test_malformed_quality_supplements_are_typed_before_uow(
    supplements,
) -> None:
    use_case = command()
    with pytest.raises(InvalidScoringInput):
        use_case.execute(request(supplements=supplements))
    assert Rows.entered == 0


@pytest.mark.parametrize(
    ("dependency", "value"),
    [
        ("clock", None),
        ("clock", "not-a-datetime"),
        ("clock", datetime(2026, 7, 28, 12, 2)),
        ("uuid_factory", "not-a-uuid"),
    ],
)
def test_invalid_dependency_results_are_sanitized_and_rolled_back(
    dependency,
    value,
) -> None:
    use_case = command(**{dependency: lambda: value})
    with pytest.raises(ScoringPersistenceError):
        use_case.execute(request())
    assert Rows.scoring == []
    assert "scoring-v1" not in Rows.configurations


def test_policy_failure_and_malformed_output_are_typed_and_rolled_back() -> None:
    class RaisingPolicy:
        def evaluate(self, **_):
            raise RuntimeError("private")

    with pytest.raises(ScoringPolicyFailure):
        command(policy_factory=lambda: RaisingPolicy()).execute(request())
    assert "scoring-v1" not in Rows.configurations

    class InvalidPolicy:
        def evaluate(self, **_):
            return object()

    with pytest.raises(InvalidScoringOutput):
        command(policy_factory=lambda: InvalidPolicy()).execute(request())
    assert Rows.scoring == []
    assert "scoring-v1" not in Rows.configurations


def test_missing_or_corrupt_source_configuration_fails_safely() -> None:
    use_case = command()
    Rows.eligibility = None
    with pytest.raises(EligibilityEvaluationNotFound):
        use_case.execute(request())

    use_case = command()
    Rows.configurations["eligibility-v1"] = deepcopy(
        Rows.configurations["eligibility-v1"]
    )
    Rows.configurations["eligibility-v1"] = ConfigurationVersion(
        version="eligibility-v1",
        contract_version="v1",
        registry_json="{}",
        registry_sha256="0" * 64,
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    with pytest.raises(ScoringPersistenceError):
        use_case.execute(request())


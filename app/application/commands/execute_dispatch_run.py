from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from time import perf_counter_ns
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from app.application.commands.analyze_work_order import WorkOrderNotFound
from app.application.ports.persistence import PersistenceAdapterError, UnitOfWorkFactory
from app.application.ports.stages import AnalyzeStage
from app.contracts.confidence import (
    ConfidenceInputV1,
    ConfidenceOutputV1,
    evaluate_input,
    validate_output_against_input as validate_confidence,
)
from app.contracts.dispatch_runs import (
    CaptureOutputV1,
    DispatchRunResourceV1,
    DispatchRunStartV1,
    DispatchRunSuccessEnvelopeV1,
)
from app.contracts.eligibility import (
    EligibilityInputV1,
    EligibilityOutputV1,
    validate_output_against_input as validate_eligibility,
)
from app.contracts.scoring import (
    ScoredTechnicianV1,
    ScoringInputV1,
    ScoringOutputV1,
    validate_output_against_input as validate_scoring,
)
from app.contracts.stages.analyze import AnalyzeInputV1, AnalyzeOutputV1
from app.domain.analysis.models import ConfigurationVersion
from app.domain.analysis.rules import ANALYSIS_REGISTRY_SHA256
from app.domain.confidence.rules import CONFIDENCE_REGISTRY_SHA256
from app.domain.dispatch.models import DispatchRun
from app.domain.dispatch.rules import (
    DISPATCH_CONFIGURATION_VERSION,
    DISPATCH_CONTRACT_VERSION,
    DISPATCH_REGISTRY_JSON,
    DISPATCH_REGISTRY_SHA256,
    assert_transition,
)
from app.domain.eligibility.policy import EligibilityPolicy
from app.domain.eligibility.rules import (
    ELIGIBILITY_CONFIGURATION,
    ELIGIBILITY_REGISTRY_SHA256,
)
from app.domain.scoring.policy import ScoringPolicy
from app.domain.scoring.rules import (
    SCORING_CONFIGURATION,
    SCORING_REGISTRY_SHA256,
    canonical_json,
)
from app.domain.work_orders.models import IdempotencyRecord


class DispatchRunNotFound(RuntimeError):
    """A dispatch run does not exist."""


class DispatchIdempotencyConflict(RuntimeError):
    """An idempotency key was reused with different input."""


class DispatchRunPersistenceError(RuntimeError):
    """Dispatch evidence could not be retained or reconstructed."""


class DispatchRunExecutionFailed(RuntimeError):
    """A stage failed after the run snapshot was captured."""

    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__()


@dataclass(frozen=True)
class ExecuteDispatchRunRequest:
    input: DispatchRunStartV1
    route: str
    idempotency_key: str
    request_id: str


@dataclass(frozen=True)
class ExecuteDispatchRunResult:
    body: dict[str, Any]
    replayed: bool


class DispatchOrchestrator:
    """The only owner of authoritative dispatch-run transitions."""

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

    def execute(self, request: ExecuteDispatchRunRequest) -> ExecuteDispatchRunResult:
        input_payload = request.input.model_dump(mode="json")
        request_json = canonical_json(input_payload)
        request_hash = hashlib.sha256(request_json.encode()).hexdigest()
        try:
            with self._unit_of_work_factory() as unit_of_work:
                retained = unit_of_work.idempotency.get(
                    request.route, request.idempotency_key
                )
                if retained is not None:
                    if retained.request_hash != request_hash:
                        raise DispatchIdempotencyConflict
                    retained_payload = self._json(retained.response_body_json)
                    if retained.response_status == 500:
                        retained_run_id = UUID(retained_payload["run_id"])
                        failed_run = unit_of_work.dispatch_runs.get(
                            str(retained_run_id)
                        )
                        if (
                            failed_run is None
                            or failed_run.state != "FAILED"
                            or DispatchRunResourceV1.model_validate_json(
                                failed_run.resource_json
                            ).failure
                            is None
                        ):
                            raise DispatchRunPersistenceError
                        raise DispatchRunExecutionFailed(retained_run_id)
                    envelope = DispatchRunSuccessEnvelopeV1.model_validate_json(
                        retained.response_body_json
                    )
                    run = unit_of_work.dispatch_runs.get(str(envelope.data.run_id))
                    if run is None or run.resource_json != canonical_json(
                        envelope.data.model_dump(mode="json")
                    ):
                        raise DispatchRunPersistenceError
                    return ExecuteDispatchRunResult(
                        body=envelope.model_dump(mode="json"), replayed=True
                    )
                work_order = unit_of_work.work_orders.get(
                    str(request.input.work_order_id)
                )
                if work_order is None:
                    raise WorkOrderNotFound
                self._ensure_dispatch_registry(unit_of_work)
                work_order_snapshot = {
                    "id": str(work_order.id),
                    "schema_version": work_order.schema_version,
                    "incident_text": work_order.incident_text,
                    "address": work_order.address,
                    "zone": work_order.zone,
                    "context": work_order.context,
                    "created_at": self._format(work_order.created_at),
                }
        except (
            DispatchIdempotencyConflict,
            DispatchRunExecutionFailed,
            DispatchRunPersistenceError,
            WorkOrderNotFound,
        ):
            raise
        except (PersistenceAdapterError, ValidationError, TypeError, ValueError) as error:
            raise DispatchRunPersistenceError from error

        run_id = self._new_uuid()
        created_at = self._now()
        input_snapshot_id = str(self._new_uuid())
        snapshot = self._snapshot_payload(
            request.input, input_payload, work_order_snapshot
        )
        snapshot_json = canonical_json(snapshot)
        snapshot_sha256 = hashlib.sha256(snapshot_json.encode()).hexdigest()
        transitions = [
            self._transition_row(
                run_id, sequence=0, previous=None, following="CAPTURE", at=created_at
            )
        ]
        executions: list[dict[str, Any]] = []
        candidates: tuple[dict[str, Any], ...] = ()
        artifact_refs = {"run_input": input_snapshot_id}
        resource = self._resource(
            run_id=run_id,
            work_order_id=request.input.work_order_id,
            state="CAPTURE",
            captured_at=request.input.captured_at,
            snapshot_sha256=snapshot_sha256,
            executions=executions,
            transitions=transitions,
            candidates=candidates,
            artifact_refs=artifact_refs,
        )
        run = self._run_model(
            resource, snapshot_json, snapshot_sha256, created_at, created_at
        )
        input_snapshot = self._snapshot_row(
            snapshot_id=input_snapshot_id,
            run_id=run_id,
            kind="run_input",
            stage=None,
            payload=snapshot,
            created_at=created_at,
        )
        try:
            with self._unit_of_work_factory() as unit_of_work:
                unit_of_work.dispatch_runs.create(
                    run, snapshot=input_snapshot, transition=transitions[0]
                )
        except PersistenceAdapterError as error:
            raise DispatchRunPersistenceError from error

        authoritative_input = DispatchRunStartV1.model_validate_json(
            canonical_json(
                {
                    "schema_version": "v1",
                    "work_order_id": snapshot["work_order"]["id"],
                    "captured_at": snapshot["captured_at"],
                    "technicians": snapshot["technicians"],
                    "technician_quality": snapshot["technician_quality"],
                    "gps_observations": snapshot["gps_observations"],
                    "traffic_observed_at": snapshot["traffic_observed_at"],
                    "weather_observed_at": snapshot["weather_observed_at"],
                    "active_supporting_episode_count": snapshot[
                        "active_supporting_episode_count"
                    ],
                    "memory_experiment_mode": snapshot[
                        "memory_experiment_mode"
                    ],
                }
            )
        )
        state = "CAPTURE"
        revision = 0
        input_ref = input_snapshot_id
        stages = (
            (
                "CAPTURE",
                lambda: CaptureOutputV1.model_validate(
                    {
                        "schema_version": "v1",
                        "validated_snapshot_sha256": snapshot_sha256,
                    }
                ).model_dump(mode="json"),
            ),
            (
                "ANALYZE",
                lambda: self._analyze_from_snapshot(snapshot),
            ),
        )
        outputs: dict[str, dict[str, Any]] = {}
        for stage_name, action in stages:
            state, revision, input_ref, output = self._execute_stage(
                request=request,
                request_hash=request_hash,
                run_id=run_id,
                created_at=created_at,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                state=state,
                revision=revision,
                stage=stage_name,
                input_ref=input_ref,
                action=action,
                executions=executions,
                transitions=transitions,
                candidates=candidates,
                artifact_refs=artifact_refs,
            )
            outputs[stage_name] = output

        plan_action = lambda: self._plan_from_snapshot(
            authoritative_input, outputs["ANALYZE"]
        )
        try:
            plan_started = self._now()
            start_ns = perf_counter_ns()
            plan_output = plan_action()
            plan_candidates = self._candidate_evidence(
                plan_output["eligibility"],
                plan_output["scoring"],
            )
            state, revision, input_ref, _ = self._commit_success(
                request=request,
                request_hash=request_hash,
                run_id=run_id,
                created_at=created_at,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                state=state,
                revision=revision,
                stage="PLAN",
                input_ref=input_ref,
                output=plan_output,
                started=plan_started,
                start_ns=start_ns,
                executions=executions,
                transitions=transitions,
                candidates=plan_candidates,
                artifact_refs=artifact_refs,
            )
            candidates = plan_candidates
            outputs["PLAN"] = plan_output
        except DispatchRunPersistenceError as persistence_error:
            try:
                self._commit_failure(
                    request,
                    request_hash,
                    run_id,
                    created_at,
                    snapshot_json,
                    snapshot_sha256,
                    state,
                    revision,
                    "PLAN",
                    input_ref,
                    plan_started,
                    start_ns,
                    executions,
                    transitions,
                    candidates,
                    artifact_refs,
                )
            except DispatchRunPersistenceError:
                pass
            raise persistence_error
        except Exception as error:
            self._commit_failure(
                request,
                request_hash,
                run_id,
                created_at,
                snapshot_json,
                snapshot_sha256,
                state,
                revision,
                "PLAN",
                input_ref,
                plan_started,
                start_ns,
                executions,
                transitions,
                candidates,
                artifact_refs,
            )
            raise DispatchRunExecutionFailed(run_id) from error

        evaluate_action = lambda: self._evaluate_from_plan(
            authoritative_input, outputs["PLAN"]
        )
        state, revision, input_ref, evaluate_output = self._execute_stage(
            request=request,
            request_hash=request_hash,
            run_id=run_id,
            created_at=created_at,
            snapshot_json=snapshot_json,
            snapshot_sha256=snapshot_sha256,
            state=state,
            revision=revision,
            stage="EVALUATE",
            input_ref=input_ref,
            action=evaluate_action,
            executions=executions,
            transitions=transitions,
            candidates=candidates,
            artifact_refs=artifact_refs,
            final_idempotency=True,
        )
        resource = self.get(str(run_id))
        envelope = DispatchRunSuccessEnvelopeV1.model_validate(
            {
                "data": resource,
                "meta": {"request_id": UUID(request.request_id)},
            }
        )
        return ExecuteDispatchRunResult(
            body=envelope.model_dump(mode="json"), replayed=False
        )

    def get(self, run_id: str) -> dict[str, Any]:
        try:
            with self._unit_of_work_factory() as unit_of_work:
                run = unit_of_work.dispatch_runs.get(run_id)
                if run is None:
                    raise DispatchRunNotFound
                return DispatchRunResourceV1.model_validate_json(
                    run.resource_json
                ).model_dump(mode="json")
        except DispatchRunNotFound:
            raise
        except (PersistenceAdapterError, ValidationError, ValueError) as error:
            raise DispatchRunPersistenceError from error

    def _execute_stage(
        self,
        *,
        request,
        request_hash,
        run_id,
        created_at,
        snapshot_json,
        snapshot_sha256,
        state,
        revision,
        stage,
        input_ref,
        action,
        executions,
        transitions,
        candidates,
        artifact_refs,
        final_idempotency=False,
    ):
        started = self._now()
        start_ns = perf_counter_ns()
        try:
            output = action()
            return self._commit_success(
                request=request,
                request_hash=request_hash,
                run_id=run_id,
                created_at=created_at,
                snapshot_json=snapshot_json,
                snapshot_sha256=snapshot_sha256,
                state=state,
                revision=revision,
                stage=stage,
                input_ref=input_ref,
                output=output,
                started=started,
                start_ns=start_ns,
                executions=executions,
                transitions=transitions,
                candidates=candidates,
                artifact_refs=artifact_refs,
                final_idempotency=final_idempotency,
            )
        except DispatchRunPersistenceError as persistence_error:
            try:
                self._commit_failure(
                    request,
                    request_hash,
                    run_id,
                    created_at,
                    snapshot_json,
                    snapshot_sha256,
                    state,
                    revision,
                    stage,
                    input_ref,
                    started,
                    start_ns,
                    executions,
                    transitions,
                    candidates,
                    artifact_refs,
                )
            except DispatchRunPersistenceError:
                pass
            raise persistence_error
        except Exception as error:
            self._commit_failure(
                request,
                request_hash,
                run_id,
                created_at,
                snapshot_json,
                snapshot_sha256,
                state,
                revision,
                stage,
                input_ref,
                started,
                start_ns,
                executions,
                transitions,
                candidates,
                artifact_refs,
            )
            raise DispatchRunExecutionFailed(run_id) from error

    def _commit_success(
        self,
        *,
        request,
        request_hash,
        run_id,
        created_at,
        snapshot_json,
        snapshot_sha256,
        state,
        revision,
        stage,
        input_ref,
        output,
        started,
        start_ns,
        executions,
        transitions,
        candidates,
        artifact_refs,
        final_idempotency=False,
    ):
        if stage != state:
            raise ValueError("only the active stage can execute")
        ended = self._now()
        output_id = str(self._new_uuid())
        execution = self._execution_row(
            run_id,
            sequence=len(executions) + 1,
            stage=stage,
            started=started,
            ended=ended,
            duration_ms=max(0, (perf_counter_ns() - start_ns) // 1_000_000),
            input_ref=input_ref,
            run_snapshot_ref=artifact_refs["run_input"],
            output_ref=output_id,
        )
        following = {
            "CAPTURE": "ANALYZE",
            "ANALYZE": "PLAN",
            "PLAN": "EVALUATE",
            "EVALUATE": (
                "NO_FEASIBLE_CANDIDATES"
                if not any(item["eligible"] for item in candidates)
                else "WAIT_FOR_DECISION"
            ),
        }[stage]
        transition = self._transition_row(
            run_id,
            sequence=len(transitions),
            previous=state,
            following=following,
            at=ended,
        )
        next_executions = [*executions, execution]
        next_transitions = [*transitions, transition]
        next_refs = {**artifact_refs, stage.lower(): output_id}
        recommendation = None
        if following == "WAIT_FOR_DECISION":
            confidence_model = ConfidenceOutputV1.model_validate_json(
                canonical_json(output)
            )
            recommendation = {
                "technician_id": confidence_model.recommended_technician_id,
                "confidence_value": confidence_model.confidence_value,
                "confidence_label": confidence_model.confidence_label,
                "explanation": confidence_model.explanation,
                "scoring": confidence_model.scoring_output.eligible_candidates[0],
                "factors": confidence_model.factors,
                "sources": confidence_model.sources,
                "warnings": confidence_model.warnings,
            }
        resource = self._resource(
            run_id=run_id,
            work_order_id=request.input.work_order_id,
            state=following,
            captured_at=request.input.captured_at,
            snapshot_sha256=snapshot_sha256,
            executions=next_executions,
            transitions=next_transitions,
            candidates=candidates,
            artifact_refs=next_refs,
            recommendation=recommendation,
        )
        run = self._run_model(resource, snapshot_json, snapshot_sha256, created_at, ended)
        output_snapshot = self._snapshot_row(
            snapshot_id=output_id,
            run_id=run_id,
            kind="stage_output",
            stage=stage,
            payload=output,
            created_at=ended,
        )
        try:
            with self._unit_of_work_factory() as unit_of_work:
                unit_of_work.dispatch_runs.advance(
                    run,
                    expected_state=state,
                    expected_revision=revision,
                    snapshot=output_snapshot,
                    execution=self._db_execution(execution, run_id),
                    transition=transition,
                )
                if final_idempotency:
                    envelope = DispatchRunSuccessEnvelopeV1.model_validate(
                        {
                            "data": resource,
                            "meta": {"request_id": UUID(request.request_id)},
                        }
                    )
                    unit_of_work.idempotency.add(
                        IdempotencyRecord(
                            route=request.route,
                            idempotency_key=request.idempotency_key,
                            request_hash=request_hash,
                            response_status=201,
                            response_body_json=canonical_json(
                                envelope.model_dump(mode="json")
                            ),
                            created_at=ended,
                        )
                    )
        except (PersistenceAdapterError, ValidationError, ValueError) as error:
            raise DispatchRunPersistenceError from error
        executions[:] = next_executions
        transitions[:] = next_transitions
        artifact_refs.clear()
        artifact_refs.update(next_refs)
        return following, revision + 1, output_id, output

    def _commit_failure(
        self,
        request,
        request_hash,
        run_id,
        created_at,
        snapshot_json,
        snapshot_sha256,
        state,
        revision,
        stage,
        input_ref,
        started,
        start_ns,
        executions,
        transitions,
        candidates,
        artifact_refs,
    ) -> None:
        ended = self._now()
        code = f"{stage}_FAILED"
        execution = self._execution_row(
            run_id,
            sequence=len(executions) + 1,
            stage=stage,
            started=started,
            ended=ended,
            duration_ms=max(0, (perf_counter_ns() - start_ns) // 1_000_000),
            input_ref=input_ref,
            run_snapshot_ref=artifact_refs["run_input"],
            output_ref=None,
            error_code=code,
        )
        transition = self._transition_row(
            run_id,
            sequence=len(transitions),
            previous=state,
            following="FAILED",
            at=ended,
        )
        resource = self._resource(
            run_id=run_id,
            work_order_id=request.input.work_order_id,
            state="FAILED",
            captured_at=request.input.captured_at,
            snapshot_sha256=snapshot_sha256,
            executions=[*executions, execution],
            transitions=[*transitions, transition],
            candidates=candidates,
            artifact_refs=artifact_refs,
            failure={"stage": stage, "code": code, "type": "STAGE_FAILURE"},
        )
        run = self._run_model(resource, snapshot_json, snapshot_sha256, created_at, ended)
        try:
            with self._unit_of_work_factory() as unit_of_work:
                unit_of_work.dispatch_runs.advance(
                    run,
                    expected_state=state,
                    expected_revision=revision,
                    snapshot=None,
                    execution=self._db_execution(execution, run_id),
                    transition=transition,
                )
                unit_of_work.idempotency.add(
                    IdempotencyRecord(
                        route=request.route,
                        idempotency_key=request.idempotency_key,
                        request_hash=request_hash,
                        response_status=500,
                        response_body_json=canonical_json({"run_id": str(run_id)}),
                        created_at=ended,
                    )
                )
        except (PersistenceAdapterError, ValueError) as error:
            raise DispatchRunPersistenceError from error

    def _analyze_from_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        input_model = AnalyzeInputV1.model_validate(
            {
                "schema_version": "v1",
                "configuration_version": "analysis-v1",
                "work_order": {
                    key: snapshot["work_order"][key]
                    for key in ("incident_text", "address", "zone", "context")
                },
            }
        )
        proposed = self._stage.execute(input_model.model_dump(mode="json"))
        return AnalyzeOutputV1.model_validate(proposed).model_dump(mode="json")

    def _plan_from_snapshot(
        self, dispatch_input: DispatchRunStartV1, analyze: dict[str, Any]
    ) -> dict[str, Any]:
        analysis = AnalyzeOutputV1.model_validate(analyze)
        requirements = analysis.requirements
        eligibility_input = EligibilityInputV1.model_validate(
            {
                "schema_version": "v1",
                "configuration_version": "eligibility-v1",
                "requirements": {
                    "priority": requirements.priority,
                    "required_certifications": requirements.required_certifications,
                    "estimated_service_duration_minutes": (
                        requirements.estimated_service_duration_minutes
                    ),
                },
                "captured_at": dispatch_input.captured_at,
                "technicians": [
                    item.model_dump(mode="json")
                    for item in dispatch_input.technicians
                ],
            }
        )
        eligibility_output = EligibilityOutputV1.from_domain(
            EligibilityPolicy(ELIGIBILITY_CONFIGURATION).evaluate(
                requirements=eligibility_input.to_domain_requirements(),
                captured_at=eligibility_input.captured_at,
                technicians=eligibility_input.to_domain_technicians(),
            )
        )
        validate_eligibility(eligibility_input, eligibility_output)
        quality = {
            item.technician_id: item.quality_rating_0_to_5
            for item in dispatch_input.technician_quality
        }
        scoring_input = ScoringInputV1.model_validate(
            {
                "schema_version": "v1",
                "configuration_version": "scoring-v1",
                "eligibility_evaluation_set_id": str(self._new_uuid()),
                "sla_minutes": requirements.sla_target_minutes,
                "eligibility_output": eligibility_output,
                "technicians": tuple(
                    {
                        "technician_id": item.technician_id,
                        "eta_minutes": item.estimated_travel_minutes,
                        "distance_meters": item.distance_meters,
                        "projected_work_minutes": (
                            item.assigned_work_minutes
                            + item.estimated_travel_minutes
                            + requirements.estimated_service_duration_minutes
                        ),
                        "quality_rating_0_to_5": quality[item.technician_id],
                    }
                    for item in dispatch_input.technicians
                ),
            }
        )
        scoring_output = ScoringOutputV1.from_domain(
            ScoringPolicy(SCORING_CONFIGURATION).evaluate(
                sla_minutes=scoring_input.sla_minutes,
                technicians=scoring_input.to_domain_eligible_technicians(),
            ),
            ineligible_candidates=[
                item for item in eligibility_output.candidates if not item.eligible
            ],
        )
        validate_scoring(scoring_input, scoring_output)
        return {
            "schema_version": "v1",
            "eligibility": eligibility_output.model_dump(mode="json"),
            "scoring": scoring_output.model_dump(mode="json"),
        }

    def _evaluate_from_plan(
        self, dispatch_input: DispatchRunStartV1, plan: dict[str, Any]
    ) -> dict[str, Any]:
        scoring = ScoringOutputV1.model_validate_json(
            canonical_json(plan["scoring"])
        )
        scoring_json = canonical_json(scoring.model_dump(mode="json"))
        eligible_ids = {
            item.technician_id for item in scoring.eligible_candidates
        }
        confidence_input = ConfidenceInputV1.model_validate(
            {
                "schema_version": "v1",
                "configuration_version": "confidence-v1",
                "scoring_evaluation_set_id": str(self._new_uuid()),
                "scoring_output_sha256": hashlib.sha256(
                    scoring_json.encode()
                ).hexdigest(),
                "evaluated_at": dispatch_input.captured_at,
                "candidates": tuple(
                    {
                        "technician_id": item.technician_id,
                        "rank": item.rank,
                        "objective_score": item.objective_score,
                    }
                    for item in scoring.eligible_candidates
                ),
                "gps_observations": tuple(
                    item.model_dump(mode="json")
                    for item in dispatch_input.gps_observations
                    if item.technician_id in eligible_ids
                ),
                "traffic": {
                    "observed_at": dispatch_input.traffic_observed_at,
                    "default_fallback": "seeded-normal",
                },
                "weather": {
                    "observed_at": dispatch_input.weather_observed_at,
                    "default_fallback": "seeded-clear",
                },
                "active_supporting_episode_count": (
                    dispatch_input.active_supporting_episode_count
                ),
            }
        )
        output = ConfidenceOutputV1.from_domain(
            evaluate_input(confidence_input), scoring
        )
        validate_confidence(confidence_input, output, scoring)
        return output.model_dump(mode="json")

    def _snapshot_payload(self, dispatch_input, input_payload, work_order):
        return {
            "schema_version": "v1",
            "captured_at": input_payload["captured_at"],
            "work_order": work_order,
            "technicians": input_payload["technicians"],
            "technician_quality": input_payload["technician_quality"],
            "gps_observations": input_payload["gps_observations"],
            "traffic_observed_at": input_payload["traffic_observed_at"],
            "weather_observed_at": input_payload["weather_observed_at"],
            "active_supporting_episode_count": (
                dispatch_input.active_supporting_episode_count
            ),
            "memory_experiment_mode": dispatch_input.memory_experiment_mode,
            "configuration_bundle": {
                "dispatch-v1": DISPATCH_REGISTRY_SHA256,
                "analysis-v1": ANALYSIS_REGISTRY_SHA256,
                "eligibility-v1": ELIGIBILITY_REGISTRY_SHA256,
                "scoring-v1": SCORING_REGISTRY_SHA256,
                "confidence-v1": CONFIDENCE_REGISTRY_SHA256,
            },
            "environment_fallbacks": {
                "traffic": "seeded-normal",
                "weather": "seeded-clear",
            },
        }

    def _resource(
        self,
        *,
        run_id,
        work_order_id,
        state,
        captured_at,
        snapshot_sha256,
        executions,
        transitions,
        candidates,
        artifact_refs,
        recommendation=None,
        failure=None,
    ) -> DispatchRunResourceV1:
        return DispatchRunResourceV1.model_validate(
            {
                "run_id": run_id,
                "work_order_id": work_order_id,
                "state": state,
                "revision": len(transitions) - 1,
                "captured_at": captured_at,
                "memory_experiment_mode": "disabled",
                "configuration_versions": {
                    "dispatch-v1": DISPATCH_REGISTRY_SHA256,
                    "analysis-v1": ANALYSIS_REGISTRY_SHA256,
                    "eligibility-v1": ELIGIBILITY_REGISTRY_SHA256,
                    "scoring-v1": SCORING_REGISTRY_SHA256,
                    "confidence-v1": CONFIDENCE_REGISTRY_SHA256,
                },
                "snapshot_sha256": snapshot_sha256,
                "input_snapshot_ref": artifact_refs["run_input"],
                "stage_executions": tuple(executions),
                "transitions": tuple(
                    self._public_transition(item) for item in transitions
                ),
                "recommendation": recommendation,
                "candidate_evaluations": candidates,
                "artifacts": artifact_refs,
                "failure": failure,
            }
        )

    def _candidate_evidence(self, eligibility, scoring):
        scored = {
            item["technician_id"]: item for item in scoring["eligible_candidates"]
        }
        resources = []
        for candidate in eligibility["candidates"]:
            score = scored.get(candidate["technician_id"])
            score_model = (
                None
                if score is None
                else ScoredTechnicianV1.model_validate_json(
                    canonical_json(score)
                )
            )
            resource = {
                "technician_id": candidate["technician_id"],
                "eligible": candidate["eligible"],
                "eligibility": candidate,
                "objective_score": None if score is None else score["objective_score"],
                "rank": None if score is None else score["rank"],
                "scoring": score_model,
            }
            resources.append(resource)
        return tuple(resources)

    def _execution_row(
        self,
        run_id,
        *,
        sequence,
        stage,
        started,
        ended,
        duration_ms,
        input_ref,
        run_snapshot_ref,
        output_ref,
        error_code=None,
    ):
        failed = error_code is not None
        return {
            "execution_id": str(self._new_uuid()),
            "sequence": sequence,
            "stage": stage,
            "status": "failed" if failed else "completed",
            "started_at": self._format(started),
            "ended_at": self._format(ended),
            "duration_ms": duration_ms,
            "attempt": 1,
            "schema_version": "v1",
            "configuration_version": "dispatch-v1",
            "input_ref": input_ref,
            "run_snapshot_ref": run_snapshot_ref,
            "output_ref": output_ref,
            "error_code": error_code,
            "error_type": "STAGE_FAILURE" if failed else None,
            "safe_message": "Stage failed safely." if failed else None,
        }

    @staticmethod
    def _db_execution(execution, run_id):
        return {
            "id": execution["execution_id"],
            "run_id": str(run_id),
            **{
                key: value
                for key, value in execution.items()
                if key != "execution_id"
            },
        }

    def _transition_row(self, run_id, *, sequence, previous, following, at):
        assert_transition(previous, following)
        return {
            "id": str(self._new_uuid()),
            "run_id": str(run_id),
            "sequence": sequence,
            "from_state": previous,
            "to_state": following,
            "outcome_code": f"{following}_ENTERED",
            "run_revision": sequence,
            "configuration_version": "dispatch-v1",
            "occurred_at": self._format(at),
        }

    @staticmethod
    def _public_transition(transition):
        return {
            key: value
            for key, value in transition.items()
            if key not in {"id", "run_id"}
        }

    def _snapshot_row(
        self, *, snapshot_id, run_id, kind, stage, payload, created_at
    ):
        content_json = canonical_json(payload)
        return {
            "id": snapshot_id,
            "run_id": str(run_id),
            "kind": kind,
            "stage": stage,
            "content_json": content_json,
            "content_sha256": hashlib.sha256(content_json.encode()).hexdigest(),
            "created_at": self._format(created_at),
        }

    @staticmethod
    def _run_model(resource, snapshot_json, snapshot_sha256, created_at, updated_at):
        return DispatchRun(
            id=resource.run_id,
            work_order_id=resource.work_order_id,
            state=resource.state,
            revision=resource.revision,
            snapshot_json=snapshot_json,
            snapshot_sha256=snapshot_sha256,
            resource_json=canonical_json(resource.model_dump(mode="json")),
            created_at=created_at,
            updated_at=updated_at,
        )

    def _ensure_dispatch_registry(self, unit_of_work):
        existing = unit_of_work.configurations.get(DISPATCH_CONFIGURATION_VERSION)
        if existing is None:
            unit_of_work.configurations.add(
                ConfigurationVersion(
                    version=DISPATCH_CONFIGURATION_VERSION,
                    contract_version=DISPATCH_CONTRACT_VERSION,
                    registry_json=DISPATCH_REGISTRY_JSON,
                    registry_sha256=DISPATCH_REGISTRY_SHA256,
                    created_at=datetime(2026, 7, 28, tzinfo=UTC),
                )
            )
        elif (
            existing.contract_version != DISPATCH_CONTRACT_VERSION
            or existing.registry_json != DISPATCH_REGISTRY_JSON
            or existing.registry_sha256 != DISPATCH_REGISTRY_SHA256
        ):
            raise DispatchRunPersistenceError

    def _new_uuid(self) -> UUID:
        value = self._uuid_factory()
        if not isinstance(value, UUID):
            raise DispatchRunPersistenceError
        return value

    def _now(self) -> datetime:
        value = self._clock()
        if type(value) is not datetime or (
            value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
        ):
            raise DispatchRunPersistenceError
        return value

    @staticmethod
    def _format(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("timestamp must be UTC")
        return value.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _json(value: str) -> dict:
        import json

        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("retained JSON must be an object")
        return parsed

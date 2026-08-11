from datetime import UTC, datetime
import hashlib
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Connection, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.persistence.schema import (
    dispatch_runs,
    configuration_versions,
    run_snapshots,
    stage_executions,
    state_transitions,
)
from app.application.ports.persistence import PersistenceAdapterError
from app.contracts.dispatch_runs import DispatchRunResourceV1
from app.contracts.dispatch_runs import (
    CaptureOutputV1,
    DispatchPlanOutputV1,
)
from app.contracts.confidence import ConfidenceOutputV1
from app.contracts.stages.analyze import AnalyzeOutputV1
from app.domain.dispatch.models import DispatchRun
from app.domain.dispatch.rules import assert_transition
from app.domain.dispatch.rules import (
    DISPATCH_REGISTRY_JSON,
    DISPATCH_REGISTRY_SHA256,
)
from app.domain.analysis.rules import ANALYSIS_REGISTRY_SHA256
from app.domain.confidence.rules import CONFIDENCE_REGISTRY_SHA256
from app.domain.eligibility.rules import ELIGIBILITY_REGISTRY_SHA256
from app.domain.scoring.rules import SCORING_REGISTRY_SHA256
from app.domain.scoring.rules import canonical_json


def _format_utc(value: datetime) -> str:
    if type(value) is not datetime or (
        value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value)
    ):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value.isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must use canonical UTC Z form")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if _format_utc(parsed) != value:
        raise ValueError("timestamp is not canonical")
    return parsed


class SqlDispatchRunRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, run_id: str) -> DispatchRun | None:
        try:
            row = self._connection.execute(
                select(dispatch_runs).where(dispatch_runs.c.id == run_id)
            ).mappings().one_or_none()
            if row is None:
                return None
            snapshot_rows = self._connection.execute(
                select(run_snapshots)
                .where(run_snapshots.c.run_id == run_id)
                .order_by(run_snapshots.c.created_at, run_snapshots.c.id)
            ).mappings().all()
            execution_rows = self._connection.execute(
                select(stage_executions)
                .where(stage_executions.c.run_id == run_id)
                .order_by(stage_executions.c.sequence)
            ).mappings().all()
            transition_rows = self._connection.execute(
                select(state_transitions)
                .where(state_transitions.c.run_id == run_id)
                .order_by(state_transitions.c.sequence)
            ).mappings().all()
            resource = DispatchRunResourceV1.model_validate_json(row["resource_json"])
            configuration = self._connection.execute(
                select(configuration_versions).where(
                    configuration_versions.c.version == "dispatch-v1"
                )
            ).mappings().one_or_none()
            if (
                configuration is None
                or configuration["registry_json"] != DISPATCH_REGISTRY_JSON
                or configuration["registry_sha256"] != DISPATCH_REGISTRY_SHA256
            ):
                raise ValueError("dispatch configuration is inconsistent")
            snapshot_by_id = {}
            run_inputs = []
            outputs_by_stage = {}
            for item in snapshot_rows:
                calculated = hashlib.sha256(item["content_json"].encode()).hexdigest()
                if calculated != item["content_sha256"]:
                    raise ValueError("corrupt run snapshot")
                snapshot_by_id[item["id"]] = item
                if item["kind"] == "run_input":
                    run_inputs.append(item)
                else:
                    outputs_by_stage[item["stage"]] = item
            if (
                len(run_inputs) != 1
                or run_inputs[0]["content_json"] != row["snapshot_json"]
                or run_inputs[0]["content_sha256"] != row["snapshot_sha256"]
            ):
                raise ValueError("run input snapshot is inconsistent")
            run_snapshot = self._json(row["snapshot_json"])
            expected_bundle = {
                "dispatch-v1": DISPATCH_REGISTRY_SHA256,
                "analysis-v1": ANALYSIS_REGISTRY_SHA256,
                "eligibility-v1": ELIGIBILITY_REGISTRY_SHA256,
                "scoring-v1": SCORING_REGISTRY_SHA256,
                "confidence-v1": CONFIDENCE_REGISTRY_SHA256,
            }
            if run_snapshot.get("configuration_bundle") != expected_bundle:
                raise ValueError("run configuration bundle is inconsistent")
            plan_output = None
            evaluate_output = None
            for stage, snapshot_row in outputs_by_stage.items():
                if stage == "CAPTURE":
                    capture = CaptureOutputV1.model_validate_json(
                        snapshot_row["content_json"]
                    )
                    if capture.validated_snapshot_sha256 != row["snapshot_sha256"]:
                        raise ValueError("capture output is inconsistent")
                elif stage == "ANALYZE":
                    AnalyzeOutputV1.model_validate_json(snapshot_row["content_json"])
                elif stage == "PLAN":
                    plan_output = DispatchPlanOutputV1.model_validate_json(
                        snapshot_row["content_json"]
                    )
                elif stage == "EVALUATE":
                    evaluate_output = ConfidenceOutputV1.model_validate_json(
                        snapshot_row["content_json"]
                    )
                else:
                    raise ValueError("unknown stage snapshot")
            if (
                plan_output is not None
                and evaluate_output is not None
                and canonical_json(plan_output.scoring.model_dump(mode="json"))
                != canonical_json(
                    evaluate_output.scoring_output.model_dump(mode="json")
                )
            ):
                raise ValueError("evaluate output altered plan scoring")
            reconstructed_executions = []
            for item in execution_rows:
                if item["input_ref"] not in snapshot_by_id:
                    raise ValueError("stage input reference is missing")
                if item["run_snapshot_ref"] != run_inputs[0]["id"]:
                    raise ValueError("stage run snapshot reference is invalid")
                if item["output_ref"] is not None and item["output_ref"] not in snapshot_by_id:
                    raise ValueError("stage output reference is missing")
                if item["output_ref"] is not None:
                    output_snapshot = snapshot_by_id[item["output_ref"]]
                    if (
                        output_snapshot["kind"] != "stage_output"
                        or output_snapshot["stage"] != item["stage"]
                    ):
                        raise ValueError("stage output reference is inconsistent")
                reconstructed_executions.append(
                    {
                        "execution_id": item["id"],
                        **{
                            key: item[key]
                            for key in (
                                "sequence",
                                "stage",
                                "status",
                                "started_at",
                                "ended_at",
                                "duration_ms",
                                "attempt",
                                "schema_version",
                                "configuration_version",
                                "input_ref",
                                "run_snapshot_ref",
                                "output_ref",
                                "error_code",
                                "error_type",
                                "safe_message",
                            )
                        },
                    }
                )
            reconstructed_transitions = [
                {
                    key: item[key]
                    for key in (
                        "sequence",
                        "from_state",
                        "to_state",
                        "outcome_code",
                        "run_revision",
                        "configuration_version",
                        "occurred_at",
                    )
                }
                for item in transition_rows
            ]
            for index, item in enumerate(reconstructed_transitions):
                assert_transition(item["from_state"], item["to_state"])
                if index and item["from_state"] != reconstructed_transitions[index - 1]["to_state"]:
                    raise ValueError("transition chain is broken")
            reconstructed_candidates = []
            if plan_output is not None:
                plan = plan_output.model_dump(mode="json")
                scored = {
                    item["technician_id"]: item
                    for item in plan["scoring"]["eligible_candidates"]
                }
                reconstructed_candidates = [
                    {
                        "technician_id": item["technician_id"],
                        "eligible": item["eligible"],
                        "eligibility": item,
                        "objective_score": (
                            None
                            if item["technician_id"] not in scored
                            else scored[item["technician_id"]]["objective_score"]
                        ),
                        "rank": (
                            None
                            if item["technician_id"] not in scored
                            else scored[item["technician_id"]]["rank"]
                        ),
                        "scoring": scored.get(item["technician_id"]),
                    }
                    for item in plan["eligibility"]["candidates"]
                ]
            expected_artifacts = {
                "run_input": run_inputs[0]["id"],
                "capture": (
                    None
                    if "CAPTURE" not in outputs_by_stage
                    else outputs_by_stage["CAPTURE"]["id"]
                ),
                "analyze": (
                    None
                    if "ANALYZE" not in outputs_by_stage
                    else outputs_by_stage["ANALYZE"]["id"]
                ),
                "plan": (
                    None
                    if "PLAN" not in outputs_by_stage
                    else outputs_by_stage["PLAN"]["id"]
                ),
                "evaluate": (
                    None
                    if "EVALUATE" not in outputs_by_stage
                    else outputs_by_stage["EVALUATE"]["id"]
                ),
            }
            expected_recommendation = None
            if resource.state == "WAIT_FOR_DECISION":
                if evaluate_output is None:
                    raise ValueError("recommendation lacks evaluate output")
                leader = evaluate_output.scoring_output.eligible_candidates[0]
                expected_recommendation = {
                    "technician_id": str(
                        evaluate_output.recommended_technician_id
                    ),
                    "confidence_value": evaluate_output.confidence_value,
                    "confidence_label": evaluate_output.confidence_label,
                    "scoring": leader.model_dump(mode="json"),
                    "factors": [
                        item.model_dump(mode="json")
                        for item in evaluate_output.factors
                    ],
                    "sources": [
                        item.model_dump(mode="json")
                        for item in evaluate_output.sources
                    ],
                    "warnings": [
                        item.model_dump(mode="json")
                        for item in evaluate_output.warnings
                    ],
                    "explanation": evaluate_output.explanation.model_dump(
                        mode="json"
                    ),
                }
            resource_json = canonical_json(resource.model_dump(mode="json"))
            if (
                str(resource.run_id) != row["id"]
                or str(resource.work_order_id) != row["work_order_id"]
                or resource.state != row["state"]
                or resource.revision != row["revision"]
                or resource_json != row["resource_json"]
                or resource.snapshot_sha256 != row["snapshot_sha256"]
                or resource.configuration_versions.model_dump(
                    mode="json", by_alias=True
                )
                != expected_bundle
                or resource.artifacts.model_dump(mode="json")
                != expected_artifacts
                or (
                    None
                    if resource.recommendation is None
                    else resource.recommendation.model_dump(mode="json")
                )
                != expected_recommendation
                or resource.model_dump(mode="json")["stage_executions"]
                != reconstructed_executions
                or resource.model_dump(mode="json")["transitions"]
                != reconstructed_transitions
                or resource.model_dump(mode="json")["candidate_evaluations"]
                != reconstructed_candidates
            ):
                raise ValueError("inconsistent retained dispatch run")
            return DispatchRun(
                id=UUID(row["id"]),
                work_order_id=UUID(row["work_order_id"]),
                state=row["state"],
                revision=row["revision"],
                snapshot_json=row["snapshot_json"],
                snapshot_sha256=row["snapshot_sha256"],
                resource_json=row["resource_json"],
                created_at=_parse_utc(row["created_at"]),
                updated_at=_parse_utc(row["updated_at"]),
            )
        except (
            SQLAlchemyError,
            ValidationError,
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            raise PersistenceAdapterError from error

    def create(self, run: DispatchRun, *, snapshot: dict, transition: dict) -> None:
        try:
            self._connection.execute(
                insert(dispatch_runs), self._run_values(run)
            )
            self._connection.execute(insert(run_snapshots), snapshot)
            self._connection.execute(insert(state_transitions), transition)
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error

    def advance(
        self,
        run: DispatchRun,
        *,
        expected_state: str,
        expected_revision: int,
        snapshot: dict | None,
        execution: dict,
        transition: dict,
    ) -> None:
        try:
            if snapshot is not None:
                self._connection.execute(insert(run_snapshots), snapshot)
            self._connection.execute(insert(stage_executions), execution)
            self._connection.execute(insert(state_transitions), transition)
            result = self._connection.execute(
                update(dispatch_runs)
                .where(
                    dispatch_runs.c.id == str(run.id),
                    dispatch_runs.c.state == expected_state,
                    dispatch_runs.c.revision == expected_revision,
                )
                .values(
                    state=run.state,
                    revision=run.revision,
                    resource_json=run.resource_json,
                    updated_at=_format_utc(run.updated_at),
                )
            )
            if result.rowcount != 1:
                raise ValueError("dispatch run revision conflict")
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error

    @staticmethod
    def _run_values(run: DispatchRun) -> dict:
        return {
            "id": str(run.id),
            "work_order_id": str(run.work_order_id),
            "schema_version": "v1",
            "configuration_version": "dispatch-v1",
            "state": run.state,
            "revision": run.revision,
            "snapshot_json": run.snapshot_json,
            "snapshot_sha256": run.snapshot_sha256,
            "resource_json": run.resource_json,
            "created_at": _format_utc(run.created_at),
            "updated_at": _format_utc(run.updated_at),
        }

    @staticmethod
    def _json(value: str) -> dict:
        import json

        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("candidate evidence must be an object")
        return parsed

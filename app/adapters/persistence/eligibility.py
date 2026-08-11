from datetime import UTC, datetime
import hashlib
import re
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.persistence.schema import eligibility_evaluation_sets
from app.application.ports.persistence import PersistenceAdapterError
from app.contracts.eligibility import (
    EligibilityInputV1,
    EligibilityOutputV1,
    validate_output_against_input,
)
from app.domain.eligibility.models import EligibilityEvaluationSet
from app.domain.eligibility.rules import canonical_json


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value.isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("stored timestamp must use canonical UTC Z form")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("stored timestamp must be UTC")
    if parsed.isoformat().replace("+00:00", "Z") != value:
        raise ValueError("stored timestamp is not canonical")
    return parsed


class SqlEligibilityEvaluationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(
        self,
        work_order_analysis_id: str,
        configuration_version: str,
        input_hash: str,
    ) -> EligibilityEvaluationSet | None:
        try:
            row = self._connection.execute(
                select(eligibility_evaluation_sets).where(
                    eligibility_evaluation_sets.c.work_order_analysis_id
                    == work_order_analysis_id,
                    eligibility_evaluation_sets.c.configuration_version
                    == configuration_version,
                    eligibility_evaluation_sets.c.input_hash == input_hash,
                )
            ).mappings().one_or_none()
            return None if row is None else self._to_model(row)
        except (
            SQLAlchemyError,
            ValidationError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            raise PersistenceAdapterError from error

    def get_by_input_json(
        self,
        work_order_analysis_id: str,
        configuration_version: str,
        input_json: str,
    ) -> EligibilityEvaluationSet | None:
        try:
            row = self._connection.execute(
                select(eligibility_evaluation_sets).where(
                    eligibility_evaluation_sets.c.work_order_analysis_id
                    == work_order_analysis_id,
                    eligibility_evaluation_sets.c.configuration_version
                    == configuration_version,
                    eligibility_evaluation_sets.c.input_json == input_json,
                )
            ).mappings().one_or_none()
            return None if row is None else self._to_model(row)
        except (
            SQLAlchemyError,
            ValidationError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            raise PersistenceAdapterError from error

    def get_by_id(self, evaluation_id: str) -> EligibilityEvaluationSet | None:
        try:
            row = self._connection.execute(
                select(eligibility_evaluation_sets).where(
                    eligibility_evaluation_sets.c.id == evaluation_id
                )
            ).mappings().one_or_none()
            return None if row is None else self._to_model(row)
        except (
            SQLAlchemyError,
            ValidationError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            raise PersistenceAdapterError from error

    @staticmethod
    def _to_model(row) -> EligibilityEvaluationSet:
        input_model = EligibilityInputV1.model_validate_json(row["input_json"])
        output_model = EligibilityOutputV1.model_validate_json(
            row["output_json"]
        )
        validate_output_against_input(input_model, output_model)
        input_json = canonical_json(input_model.model_dump(mode="json"))
        output_json = canonical_json(output_model.model_dump(mode="json"))
        calculated_hash = hashlib.sha256(input_json.encode("utf-8")).hexdigest()
        if (
            row["input_json"] != input_json
            or row["output_json"] != output_json
            or row["input_hash"] != calculated_hash
            or re.fullmatch(r"[0-9a-f]{64}", row["input_hash"]) is None
            or row["schema_version"] != output_model.schema_version
            or row["configuration_version"] != output_model.configuration_version
            or row["configuration_version"] != input_model.configuration_version
            or row["candidate_count"] != len(output_model.candidates)
            or row["candidate_count"] != len(input_model.technicians)
            or row["eligible_count"] != len(output_model.eligible_technician_ids)
            or row["ineligible_count"]
            != len(output_model.ineligible_technician_ids)
            or bool(row["no_feasible_candidates"])
            != output_model.no_feasible_candidates
        ):
            raise ValueError("inconsistent retained eligibility evidence")
        return EligibilityEvaluationSet(
            id=UUID(row["id"]),
            work_order_id=row["work_order_id"],
            work_order_analysis_id=row["work_order_analysis_id"],
            schema_version=row["schema_version"],
            configuration_version=row["configuration_version"],
            input_hash=row["input_hash"],
            input_json=row["input_json"],
            output_json=row["output_json"],
            candidate_count=row["candidate_count"],
            eligible_count=row["eligible_count"],
            ineligible_count=row["ineligible_count"],
            no_feasible_candidates=bool(row["no_feasible_candidates"]),
            created_at=_parse_utc(row["created_at"]),
        )

    def add(self, evaluation: EligibilityEvaluationSet) -> None:
        try:
            self._connection.execute(
                insert(eligibility_evaluation_sets),
                {
                    "id": str(evaluation.id),
                    "work_order_id": evaluation.work_order_id,
                    "work_order_analysis_id": evaluation.work_order_analysis_id,
                    "schema_version": evaluation.schema_version,
                    "configuration_version": evaluation.configuration_version,
                    "input_hash": evaluation.input_hash,
                    "input_json": evaluation.input_json,
                    "output_json": evaluation.output_json,
                    "candidate_count": evaluation.candidate_count,
                    "eligible_count": evaluation.eligible_count,
                    "ineligible_count": evaluation.ineligible_count,
                    "no_feasible_candidates": int(
                        evaluation.no_feasible_candidates
                    ),
                    "created_at": _format_utc(evaluation.created_at),
                },
            )
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error

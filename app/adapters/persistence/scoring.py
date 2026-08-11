from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import re
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.persistence.schema import scoring_evaluation_sets
from app.application.ports.persistence import PersistenceAdapterError
from app.contracts.scoring import (
    ScoringInputV1,
    ScoringOutputV1,
    validate_output_against_input,
)
from app.domain.scoring.models import ScoringEvaluationSet
from app.domain.scoring.rules import canonical_decimal, canonical_json


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value.isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("stored timestamp must use canonical UTC Z form")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() != UTC.utcoffset(parsed)
        or parsed.isoformat().replace("+00:00", "Z") != value
    ):
        raise ValueError("stored timestamp is not canonical UTC")
    return parsed


class SqlScoringEvaluationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(
        self,
        eligibility_evaluation_set_id: str,
        configuration_version: str,
        input_hash: str,
    ) -> ScoringEvaluationSet | None:
        return self._find(
            scoring_evaluation_sets.c.eligibility_evaluation_set_id
            == eligibility_evaluation_set_id,
            scoring_evaluation_sets.c.configuration_version
            == configuration_version,
            scoring_evaluation_sets.c.input_hash == input_hash,
        )

    def get_by_input_json(
        self,
        eligibility_evaluation_set_id: str,
        configuration_version: str,
        input_json: str,
    ) -> ScoringEvaluationSet | None:
        return self._find(
            scoring_evaluation_sets.c.eligibility_evaluation_set_id
            == eligibility_evaluation_set_id,
            scoring_evaluation_sets.c.configuration_version
            == configuration_version,
            scoring_evaluation_sets.c.input_json == input_json,
        )

    def get_by_id(self, evaluation_id: str) -> ScoringEvaluationSet | None:
        return self._find(scoring_evaluation_sets.c.id == evaluation_id)

    def _find(self, *criteria) -> ScoringEvaluationSet | None:
        try:
            row = self._connection.execute(
                select(scoring_evaluation_sets).where(*criteria)
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
    def _to_model(row) -> ScoringEvaluationSet:
        input_model = ScoringInputV1.model_validate_json(row["input_json"])
        output_model = ScoringOutputV1.model_validate_json(row["output_json"])
        validate_output_against_input(input_model, output_model)
        input_json = canonical_json(input_model.model_dump(mode="json"))
        output_json = canonical_json(output_model.model_dump(mode="json"))
        calculated_hash = hashlib.sha256(input_json.encode("utf-8")).hexdigest()
        top = (
            output_model.eligible_candidates[0]
            if output_model.eligible_candidates
            else None
        )
        expected_top_id = None if top is None else str(top.technician_id)
        expected_top_score = None if top is None else top.objective_score
        if (
            row["input_json"] != input_json
            or row["output_json"] != output_json
            or row["input_hash"] != calculated_hash
            or re.fullmatch(r"[0-9a-f]{64}", row["input_hash"]) is None
            or row["eligibility_evaluation_set_id"]
            != str(input_model.eligibility_evaluation_set_id)
            or row["schema_version"] != output_model.schema_version
            or row["configuration_version"] != input_model.configuration_version
            or row["configuration_version"] != output_model.configuration_version
            or row["candidate_count"] != len(input_model.technicians)
            or row["eligible_count"] != len(output_model.eligible_candidates)
            or row["ineligible_count"] != len(output_model.ineligible_candidates)
            or row["top_technician_id"] != expected_top_id
            or row["top_objective_score"] != expected_top_score
        ):
            raise ValueError("inconsistent retained scoring evidence")
        if expected_top_score is not None:
            if canonical_decimal(Decimal(expected_top_score)) != expected_top_score:
                raise ValueError("top score is not canonical")
        return ScoringEvaluationSet(
            id=UUID(row["id"]),
            eligibility_evaluation_set_id=UUID(
                row["eligibility_evaluation_set_id"]
            ),
            schema_version=row["schema_version"],
            configuration_version=row["configuration_version"],
            input_hash=row["input_hash"],
            input_json=row["input_json"],
            output_json=row["output_json"],
            candidate_count=row["candidate_count"],
            eligible_count=row["eligible_count"],
            ineligible_count=row["ineligible_count"],
            top_technician_id=(
                None
                if row["top_technician_id"] is None
                else UUID(row["top_technician_id"])
            ),
            top_objective_score=row["top_objective_score"],
            created_at=_parse_utc(row["created_at"]),
        )

    def add(self, evaluation: ScoringEvaluationSet) -> None:
        try:
            self._connection.execute(
                insert(scoring_evaluation_sets),
                {
                    "id": str(evaluation.id),
                    "eligibility_evaluation_set_id": str(
                        evaluation.eligibility_evaluation_set_id
                    ),
                    "schema_version": evaluation.schema_version,
                    "configuration_version": evaluation.configuration_version,
                    "input_hash": evaluation.input_hash,
                    "input_json": evaluation.input_json,
                    "output_json": evaluation.output_json,
                    "candidate_count": evaluation.candidate_count,
                    "eligible_count": evaluation.eligible_count,
                    "ineligible_count": evaluation.ineligible_count,
                    "top_technician_id": (
                        None
                        if evaluation.top_technician_id is None
                        else str(evaluation.top_technician_id)
                    ),
                    "top_objective_score": evaluation.top_objective_score,
                    "created_at": _format_utc(evaluation.created_at),
                },
            )
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error

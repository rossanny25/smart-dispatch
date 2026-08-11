from datetime import UTC, datetime
import hashlib
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.persistence.schema import confidence_evaluation_sets
from app.application.ports.persistence import PersistenceAdapterError
from app.contracts.confidence import (
    ConfidenceInputV1,
    ConfidenceOutputV1,
    validate_output_against_input,
)
from app.domain.confidence.models import ConfidenceEvaluationSet
from app.domain.scoring.rules import canonical_json


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value.isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("timestamp must use canonical UTC Z form")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.isoformat().replace("+00:00", "Z") != value:
        raise ValueError("timestamp is not canonical")
    return parsed


class SqlConfidenceEvaluationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, scoring_id, configuration_version, input_hash):
        return self._find(
            confidence_evaluation_sets.c.scoring_evaluation_set_id == scoring_id,
            confidence_evaluation_sets.c.configuration_version
            == configuration_version,
            confidence_evaluation_sets.c.input_hash == input_hash,
        )

    def get_by_input_json(self, scoring_id, configuration_version, input_json):
        return self._find(
            confidence_evaluation_sets.c.scoring_evaluation_set_id == scoring_id,
            confidence_evaluation_sets.c.configuration_version
            == configuration_version,
            confidence_evaluation_sets.c.input_json == input_json,
        )

    def _find(self, *criteria):
        try:
            row = self._connection.execute(
                select(confidence_evaluation_sets).where(*criteria)
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
    def _to_model(row) -> ConfidenceEvaluationSet:
        input_model = ConfidenceInputV1.model_validate_json(row["input_json"])
        output_model = ConfidenceOutputV1.model_validate_json(row["output_json"])
        validate_output_against_input(input_model, output_model)
        input_json = canonical_json(input_model.model_dump(mode="json"))
        output_json = canonical_json(output_model.model_dump(mode="json"))
        calculated_hash = hashlib.sha256(input_json.encode()).hexdigest()
        if (
            row["input_json"] != input_json
            or row["output_json"] != output_json
            or row["input_hash"] != calculated_hash
            or row["scoring_evaluation_set_id"]
            != str(input_model.scoring_evaluation_set_id)
            or row["schema_version"] != output_model.schema_version
            or row["configuration_version"] != input_model.configuration_version
            or row["configuration_version"] != output_model.configuration_version
            or row["eligible_count"] != len(input_model.candidates)
            or row["source_count"] != len(output_model.sources)
            or row["warning_count"] != len(output_model.warnings)
            or row["recommended_technician_id"]
            != (
                None
                if output_model.recommended_technician_id is None
                else str(output_model.recommended_technician_id)
            )
            or row["confidence_value"] != output_model.confidence_value
            or row["confidence_label"] != output_model.confidence_label
        ):
            raise ValueError("inconsistent retained confidence evidence")
        return ConfidenceEvaluationSet(
            id=UUID(row["id"]),
            scoring_evaluation_set_id=UUID(row["scoring_evaluation_set_id"]),
            schema_version=row["schema_version"],
            configuration_version=row["configuration_version"],
            input_hash=row["input_hash"],
            input_json=row["input_json"],
            output_json=row["output_json"],
            eligible_count=row["eligible_count"],
            source_count=row["source_count"],
            warning_count=row["warning_count"],
            recommended_technician_id=(
                None
                if row["recommended_technician_id"] is None
                else UUID(row["recommended_technician_id"])
            ),
            confidence_value=row["confidence_value"],
            confidence_label=row["confidence_label"],
            created_at=_parse_utc(row["created_at"]),
        )

    def add(self, evaluation: ConfidenceEvaluationSet) -> None:
        try:
            self._connection.execute(
                insert(confidence_evaluation_sets),
                {
                    "id": str(evaluation.id),
                    "scoring_evaluation_set_id": str(
                        evaluation.scoring_evaluation_set_id
                    ),
                    "schema_version": evaluation.schema_version,
                    "configuration_version": evaluation.configuration_version,
                    "input_hash": evaluation.input_hash,
                    "input_json": evaluation.input_json,
                    "output_json": evaluation.output_json,
                    "eligible_count": evaluation.eligible_count,
                    "source_count": evaluation.source_count,
                    "warning_count": evaluation.warning_count,
                    "recommended_technician_id": (
                        None
                        if evaluation.recommended_technician_id is None
                        else str(evaluation.recommended_technician_id)
                    ),
                    "confidence_value": evaluation.confidence_value,
                    "confidence_label": evaluation.confidence_label,
                    "created_at": _format_utc(evaluation.created_at),
                },
            )
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error

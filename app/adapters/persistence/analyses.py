from datetime import UTC, datetime
import json
import re

from pydantic import ValidationError
from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.persistence.schema import (
    configuration_versions,
    work_order_analyses,
)
from app.application.ports.persistence import PersistenceAdapterError
from app.contracts.stages.analyze import AnalyzeOutputV1
from app.domain.analysis.models import ConfigurationVersion, WorkOrderAnalysis
from app.domain.analysis.rules import canonical_json


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


class SqlConfigurationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, version: str) -> ConfigurationVersion | None:
        try:
            row = self._connection.execute(
                select(configuration_versions).where(
                    configuration_versions.c.version == version
                )
            ).mappings().one_or_none()
            if row is None:
                return None
            return ConfigurationVersion(
                version=row["version"],
                contract_version=row["contract_version"],
                registry_json=row["registry_json"],
                registry_sha256=row["registry_sha256"],
                created_at=_parse_utc(row["created_at"]),
            )
        except (SQLAlchemyError, TypeError, ValueError) as error:
            raise PersistenceAdapterError from error

    def add(self, configuration: ConfigurationVersion) -> None:
        try:
            self._connection.execute(
                insert(configuration_versions),
                {
                    "version": configuration.version,
                    "contract_version": configuration.contract_version,
                    "registry_json": configuration.registry_json,
                    "registry_sha256": configuration.registry_sha256,
                    "created_at": _format_utc(configuration.created_at),
                },
            )
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error


class SqlWorkOrderAnalysisRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(
        self,
        work_order_id: str,
        configuration_version: str,
    ) -> WorkOrderAnalysis | None:
        try:
            row = self._connection.execute(
                select(work_order_analyses).where(
                    work_order_analyses.c.work_order_id == work_order_id,
                    work_order_analyses.c.configuration_version
                    == configuration_version,
                )
            ).mappings().one_or_none()
            return None if row is None else self._to_model(row)
        except (
            SQLAlchemyError,
            ValidationError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            raise PersistenceAdapterError from error

    def get_by_id(self, analysis_id: str) -> WorkOrderAnalysis | None:
        try:
            row = self._connection.execute(
                select(work_order_analyses).where(
                    work_order_analyses.c.id == analysis_id
                )
            ).mappings().one_or_none()
            return None if row is None else self._to_model(row)
        except (
            SQLAlchemyError,
            ValidationError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
            RecursionError,
        ) as error:
            raise PersistenceAdapterError from error

    @staticmethod
    def _to_model(row) -> WorkOrderAnalysis:
        from uuid import UUID

        output = AnalyzeOutputV1.model_validate_json(
            row["output_json"]
        ).model_dump(mode="json")
        requirements = output["requirements"]
        certifications = json.loads(row["required_certifications_json"])
        if (
            row["output_json"] != canonical_json(output)
            or row["required_certifications_json"]
            != canonical_json(certifications)
            or row["schema_version"] != output["schema_version"]
            or row["configuration_version"] != output["configuration_version"]
            or row["category"] != requirements["category"]
            or row["priority"] != requirements["priority"]
            or row["sla_target_minutes"] != requirements["sla_target_minutes"]
            or certifications != requirements["required_certifications"]
            or row["estimated_service_duration_minutes"]
            != requirements["estimated_service_duration_minutes"]
            or re.fullmatch(r"[0-9a-f]{64}", row["input_hash"]) is None
        ):
            raise ValueError("inconsistent retained analysis")
        return WorkOrderAnalysis(
            id=UUID(row["id"]),
            work_order_id=row["work_order_id"],
            schema_version=row["schema_version"],
            configuration_version=row["configuration_version"],
            input_hash=row["input_hash"],
            output_json=row["output_json"],
            category=row["category"],
            priority=row["priority"],
            sla_target_minutes=row["sla_target_minutes"],
            required_certifications_json=row["required_certifications_json"],
            estimated_service_duration_minutes=row[
                "estimated_service_duration_minutes"
            ],
            created_at=_parse_utc(row["created_at"]),
        )

    def add(self, analysis: WorkOrderAnalysis) -> None:
        try:
            self._connection.execute(
                insert(work_order_analyses),
                {
                    "id": str(analysis.id),
                    "work_order_id": analysis.work_order_id,
                    "schema_version": analysis.schema_version,
                    "configuration_version": analysis.configuration_version,
                    "input_hash": analysis.input_hash,
                    "output_json": analysis.output_json,
                    "category": analysis.category,
                    "priority": analysis.priority,
                    "sla_target_minutes": analysis.sla_target_minutes,
                    "required_certifications_json": (
                        analysis.required_certifications_json
                    ),
                    "estimated_service_duration_minutes": (
                        analysis.estimated_service_duration_minutes
                    ),
                    "created_at": _format_utc(analysis.created_at),
                },
            )
        except (SQLAlchemyError, ValueError) as error:
            raise PersistenceAdapterError from error

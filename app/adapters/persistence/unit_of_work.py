from pathlib import Path
from threading import Lock
from types import TracebackType

from sqlalchemy import Connection, Engine
from sqlalchemy.exc import SQLAlchemyError

from app.adapters.persistence.database import create_sqlite_engine
from app.adapters.persistence.analyses import (
    SqlConfigurationRepository,
    SqlWorkOrderAnalysisRepository,
)
from app.adapters.persistence.eligibility import (
    SqlEligibilityEvaluationRepository,
)
from app.adapters.persistence.scoring import SqlScoringEvaluationRepository
from app.adapters.persistence.confidence import SqlConfidenceEvaluationRepository
from app.adapters.persistence.dispatch_runs import SqlDispatchRunRepository
from app.adapters.persistence.work_orders import (
    SqlIdempotencyRepository,
    SqlWorkOrderRepository,
)
from app.application.ports.persistence import PersistenceAdapterError


class SqliteUnitOfWork:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None

    def __enter__(self) -> "SqliteUnitOfWork":
        try:
            self._connection = self._engine.connect()
            # One local writer is the binding deployment model. Acquiring the
            # writer lock before the idempotency read avoids deferred-upgrade
            # snapshot races while preserving a single atomic transaction.
            self._connection.exec_driver_sql("BEGIN IMMEDIATE")
            self.work_orders = SqlWorkOrderRepository(self._connection)
            self.idempotency = SqlIdempotencyRepository(self._connection)
            self.configurations = SqlConfigurationRepository(self._connection)
            self.analyses = SqlWorkOrderAnalysisRepository(self._connection)
            self.eligibility_evaluations = SqlEligibilityEvaluationRepository(
                self._connection
            )
            self.scoring_evaluations = SqlScoringEvaluationRepository(
                self._connection
            )
            self.confidence_evaluations = SqlConfidenceEvaluationRepository(
                self._connection
            )
            self.dispatch_runs = SqlDispatchRunRepository(self._connection)
            return self
        except SQLAlchemyError as error:
            if self._connection is not None:
                self._connection.close()
            raise PersistenceAdapterError from error

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        assert self._connection is not None
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        except SQLAlchemyError as error:
            if self._connection.in_transaction():
                self._connection.rollback()
            raise PersistenceAdapterError from error
        finally:
            self._connection.close()
        return False


class SqliteUnitOfWorkFactory:
    """Lazily owns one Engine without performing import-time I/O."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self._database_path = database_path
        self._engine: Engine | None = None
        self._engine_lock = Lock()

    def _get_engine(self) -> Engine:
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    self._engine = create_sqlite_engine(self._database_path)
        return self._engine

    def __call__(self) -> SqliteUnitOfWork:
        return SqliteUnitOfWork(self._get_engine())

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

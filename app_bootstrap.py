"""
Application bootstrap for the personal performance OS.

Responsible for:
- initializing the SQLite database
- constructing storage implementations
- constructing service layer objects
- exposing a single AppContainer for use by UI / CLI / scripts
"""

from __future__ import annotations

from dataclasses import dataclass

from .storage.sqlite_db import Database
from .storage.sqlite_sleep_storage import SqliteSleepStorage
from .storage.sqlite_session_storage import SqliteSessionStorage
from .storage.sqlite_task_storage import SqliteTaskStorage
from .storage.base import SleepStorage, SessionStorage
from .services.sleep_service import SleepService
from .services.session_service import SessionService
from .services.day_service import DayService
from .services.analytics_service import AnalyticsService
from .services.intake_service import IntakeService
from .services.work_type_classifier import WorkTypeClassifier



@dataclass
class AppContainer:
    """
    Aggregates core infrastructure objects for the app.

    This keeps wiring in one place and makes it easy to pass dependencies
    into UI layers, CLI tools, or tests without recreating everything.
    """

    db: Database

    sleep_storage: SleepStorage
    session_storage: SessionStorage

    sleep_service: SleepService
    session_service: SessionService
    day_service: DayService
    analytics_service: AnalyticsService
    intake_service: IntakeService
    task_storage: SqliteTaskStorage
    work_type_classifier: WorkTypeClassifier

    def close(self) -> None:
        """
        Cleanly close underlying resources (e.g. database connection).
        """
        self.db.close()


def create_app() -> AppContainer:
    """
    Initialize the full application stack and return an AppContainer.

    This is the central composition root; everything else should call this
    instead of manually wiring dependencies.
    """
    # Core infrastructure
    db = Database()

    # Storage implementations
    sleep_storage: SleepStorage = SqliteSleepStorage(db)
    session_storage: SessionStorage = SqliteSessionStorage(db)
    intake_service = IntakeService(db)
    task_storage = SqliteTaskStorage(db)

    # Services
    sleep_service = SleepService(sleep_storage)
    session_service = SessionService(session_storage)
    day_service = DayService(sleep_storage, session_storage)
    analytics_service = AnalyticsService(day_service, session_service)
    work_type_classifier = WorkTypeClassifier()

    return AppContainer(
        db=db,
        sleep_storage=sleep_storage,
        session_storage=session_storage,
        task_storage=task_storage,
        sleep_service=sleep_service,
        session_service=session_service,
        day_service=day_service,
        analytics_service=analytics_service,
        intake_service=intake_service,
        work_type_classifier=work_type_classifier,
    )

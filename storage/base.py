"""
Abstract storage interfaces for persisting core domain models.

Concrete implementations (e.g. SQLite) must implement these contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from ..core.models import PerformanceSession, SleepNight


SessionId = int


class SleepStorage(ABC):
    """
    Persistence interface for SleepNight records.
    """

    @abstractmethod
    def save_sleep(self, sleep: SleepNight) -> None:
        """
        Create or update a SleepNight record for the given date.
        """
        raise NotImplementedError

    @abstractmethod
    def get_sleep_by_date(self, day: date) -> Optional[SleepNight]:
        """
        Retrieve the SleepNight for a specific calendar date, if any.
        """
        raise NotImplementedError

    @abstractmethod
    def list_sleep(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[SleepNight]:
        """
        List SleepNight records in the given date range (inclusive).

        If both start_date and end_date are None, returns all records.
        """
        raise NotImplementedError


class SessionStorage(ABC):
    """
    Persistence interface for PerformanceSession records.
    """

    @abstractmethod
    def create_session(self, session: PerformanceSession) -> PerformanceSession:
        """
        Persist a new PerformanceSession and return it with an assigned id.
        """
        raise NotImplementedError

    @abstractmethod
    def update_session(self, session: PerformanceSession) -> None:
        """
        Persist changes to an existing PerformanceSession.
        """
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: SessionId) -> Optional[PerformanceSession]:
        """
        Retrieve a single PerformanceSession by its id, if it exists.
        """
        raise NotImplementedError

    @abstractmethod
    def list_sessions_by_date(self, day: date) -> List[PerformanceSession]:
        """
        List all sessions whose start date matches the given calendar date.
        """
        raise NotImplementedError

    @abstractmethod
    def list_sessions_between(
        self,
        start_date: date,
        end_date: date,
    ) -> List[PerformanceSession]:
        """
        List all sessions whose start date falls within the given range (inclusive).
        """
        raise NotImplementedError

    @abstractmethod
    def list_all_sessions(self) -> List[PerformanceSession]:
        """
        List all stored sessions, ordered in a stable, deterministic way
        (e.g. by date then start time).
        """
        raise NotImplementedError

"""
Service layer for aggregating daily performance data.

Responsibilities:
- combine sleep and session data for a given day
- compute DaySummary objects
- provide range-based access to daily summaries
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

from ..core.enums import Domain, WorkType
from ..core.models import DaySummary, PerformanceSession, SleepNight
from ..storage.base import SessionStorage, SleepStorage


class DayService:
    """
    High-level operations for building daily summaries of performance.

    Uses:
    - SleepStorage for sleep data
    - SessionStorage for performance sessions
    """

    def __init__(
        self,
        sleep_storage: SleepStorage,
        session_storage: SessionStorage,
    ) -> None:
        self._sleep_storage = sleep_storage
        self._session_storage = session_storage

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def build_day_summary(self, day: date) -> DaySummary:
        """
        Build a DaySummary for a single calendar date.

        - SleepNight is looked up by that date.
        - Sessions are those whose start date matches that date.
        """
        sleep: Optional[SleepNight] = self._sleep_storage.get_sleep_by_date(day)
        sessions: List[PerformanceSession] = self._session_storage.list_sessions_by_date(day)

        if not sessions and sleep is None:
            # Nothing recorded for this day yet
            return DaySummary.empty(day)

        total_sessions = len(sessions)

        deep_minutes, shallow_minutes, maintenance_minutes = self._aggregate_minutes_by_work_type(
            sessions
        )
        minutes_by_domain = self._aggregate_minutes_by_domain(sessions)

        avg_focus_quality = self._compute_average_focus(sessions)
        avg_progress_rating = self._compute_average_progress(sessions)
        avg_quality_rating = self._compute_average_quality(sessions)

        # Sleep-related fields
        if sleep is not None:
            sleep_duration_minutes = sleep.duration_minutes()
            sleep_quality = sleep.sleep_quality
            energy_morning = sleep.energy_morning
        else:
            sleep_duration_minutes = None
            sleep_quality = None
            energy_morning = None

        return DaySummary(
            date=day,
            total_sessions=total_sessions,
            deep_minutes=deep_minutes,
            shallow_minutes=shallow_minutes,
            maintenance_minutes=maintenance_minutes,
            minutes_by_domain=minutes_by_domain,
            avg_focus_quality=avg_focus_quality,
            avg_progress_rating=avg_progress_rating,
            avg_quality_rating=avg_quality_rating,
            sleep_duration_minutes=sleep_duration_minutes,
            sleep_quality=sleep_quality,
            energy_morning=energy_morning,
        )

    def list_day_summaries(self, start_date: date, end_date: date) -> List[DaySummary]:
        """
        Build DaySummary objects for each date in the given range (inclusive).

        This loops per day and delegates to build_day_summary(). For the
        expected personal-scale dataset, this is sufficient and keeps the
        logic simple.
        """
        if end_date < start_date:
            # Swap if range is reversed
            start_date, end_date = end_date, start_date

        days: List[DaySummary] = []
        current = start_date
        while current <= end_date:
            days.append(self.build_day_summary(current))
            current += timedelta(days=1)

        return days

    # ------------------------------------------------------------------ #
    # Internal aggregation helpers
    # ------------------------------------------------------------------ #

    def _aggregate_minutes_by_work_type(
        self,
        sessions: List[PerformanceSession],
    ) -> tuple[int, int, int]:
        """
        Compute total minutes spent in deep, shallow, and maintenance work.

        Only counts sessions that have a valid duration.
        """
        deep = 0
        shallow = 0
        maintenance = 0

        for session in sessions:
            duration = session.duration_minutes
            if duration is None or duration <= 0:
                continue

            wt = session.context.work_type
            if wt == WorkType.DEEP:
                deep += duration
            elif wt == WorkType.SHALLOW:
                shallow += duration
            elif wt == WorkType.MAINTENANCE:
                maintenance += duration

        return deep, shallow, maintenance

    def _aggregate_minutes_by_domain(
        self,
        sessions: List[PerformanceSession],
    ) -> Dict[Domain, int]:
        """
        Compute total minutes spent per domain.

        Only counts sessions that have a valid duration.
        """
        result: Dict[Domain, int] = {}

        for session in sessions:
            duration = session.duration_minutes
            if duration is None or duration <= 0:
                continue

            domain = session.context.domain
            if domain not in result:
                result[domain] = 0
            result[domain] += duration

        return result

    def _compute_average_focus(
        self,
        sessions: List[PerformanceSession],
    ) -> Optional[float]:
        """
        Average focus_quality over sessions that have an outcome.
        """
        values: List[int] = []

        for session in sessions:
            if session.outcome is not None:
                values.append(session.outcome.focus_quality)

        return self._safe_mean(values)

    def _compute_average_progress(
        self,
        sessions: List[PerformanceSession],
    ) -> Optional[float]:
        """
        Average progress_rating over sessions that have an outcome.
        """
        values: List[int] = []

        for session in sessions:
            if session.outcome is not None:
                values.append(session.outcome.progress_rating)

        return self._safe_mean(values)

    def _compute_average_quality(
        self,
        sessions: List[PerformanceSession],
    ) -> Optional[float]:
        """
        Average quality_rating over sessions that have an outcome.
        """
        values: List[int] = []

        for session in sessions:
            if session.outcome is not None:
                values.append(session.outcome.quality_rating)

        return self._safe_mean(values)

    @staticmethod
    def _safe_mean(values: List[int]) -> Optional[float]:
        """
        Return the arithmetic mean of values, or None if the list is empty.
        """
        if not values:
            return None
        return sum(values) / len(values)

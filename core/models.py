"""
Core domain models for the personal performance OS.

These dataclasses are pure domain objects:
- no database logic
- no UI logic
- minimal, focused methods
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

from .enums import CompletionStatus, Domain, WorkType


# ---------------------------------------------------------------------------
# Sleep
# ---------------------------------------------------------------------------


@dataclass
class SleepNight:
    """
    Represents one night of sleep and the state on waking.
    """

    date: date
    sleep_start: datetime
    sleep_end: datetime

    sleep_quality: int  # 1–5
    awakenings_count: int

    energy_morning: int  # 1–10
    mood_morning: int    # 1–10

    # Optional behaviour-related flags (you can choose to use or ignore)
    screen_last_hour: Optional[bool] = None
    caffeine_after_17: Optional[bool] = None
    bedtime_consistent: Optional[bool] = None

    def duration_minutes(self) -> int:
        """
        Total sleep duration in whole minutes.
        """
        delta = self.sleep_end - self.sleep_start
        return int(delta.total_seconds() // 60)


# ---------------------------------------------------------------------------
# Session components
# ---------------------------------------------------------------------------


@dataclass
class BeforeState:
    """
    State immediately before starting a performance session.
    """

    energy: int       # 1–10
    stress: int       # 1–10
    resistance: int   # 1–5 (how hard it was to start)


@dataclass
class AfterState:
    """
    State immediately after finishing a performance session.
    """

    energy: int       # 1–10
    stress: int       # 1–10
    feel_tag: str     # e.g. "clear", "drained", "anxious", "satisfied"


@dataclass
class SessionContext:
    """
    Intent and context for a performance session.
    """

    domain: Domain
    project_name: str
    activity_description: str
    work_type: WorkType

    planned_duration_min: Optional[int] = None


@dataclass
class SessionOutcome:
    """
    Outcome and self-evaluation of a performance session.
    """

    completion_status: CompletionStatus
    progress_rating: int    # 1–5 (how much you moved the needle)
    quality_rating: int     # 1–5 (how good the work is)
    focus_quality: int      # 1–5 (how focused you were)

    moves_main_goal: bool
    evidence_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Performance session
# ---------------------------------------------------------------------------


@dataclass
class PerformanceSession:
    """
    A single, intentional block of time where you worked on something.

    It has:
    - context  (what you planned and in which domain)
    - before   (your state at the start)
    - after    (your state at the end, optional until finished)
    - outcome  (what happened, optional until finished)
    """

    id: Optional[int]
    start_time: datetime

    context: SessionContext
    before: BeforeState

    end_time: Optional[datetime] = None
    after: Optional[AfterState] = None
    outcome: Optional[SessionOutcome] = None

    @property
    def date(self) -> date:
        """
        Calendar date for this session (based on start_time).
        """
        return self.start_time.date()

    @property
    def is_finished(self) -> bool:
        """
        Whether the session has been completed (end_time set).
        """
        return self.end_time is not None

    @property
    def duration_minutes(self) -> Optional[int]:
        """
        Session duration in minutes, or None if not yet finished.
        """
        if self.start_time is None or self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() // 60)

    @property
    def energy_delta(self) -> Optional[int]:
        """
        Change in energy (after - before), or None if after state is missing.
        """
        if self.after is None:
            return None
        return self.after.energy - self.before.energy

    @property
    def stress_delta(self) -> Optional[int]:
        """
        Change in stress (after - before), or None if after state is missing.
        """
        if self.after is None:
            return None
        return self.after.stress - self.before.stress

    @property
    def is_deep_work(self) -> bool:
        """
        Whether this session is classified as deep work.
        """
        return self.context.work_type == WorkType.DEEP

    @property
    def is_on_main_goal(self) -> Optional[bool]:
        """
        Whether this session was aligned with a main goal, if outcome exists.
        """
        if self.outcome is None:
            return None
        return self.outcome.moves_main_goal


# ---------------------------------------------------------------------------
# Daily summary
# ---------------------------------------------------------------------------


@dataclass
class DaySummary:
    """
    Aggregated view of a single calendar day.

    This is typically computed from:
    - one SleepNight (optional)
    - zero or more PerformanceSession objects
    """

    date: date

    total_sessions: int
    deep_minutes: int
    shallow_minutes: int
    maintenance_minutes: int

    minutes_by_domain: Dict[Domain, int]

    avg_focus_quality: Optional[float]
    avg_progress_rating: Optional[float]
    avg_quality_rating: Optional[float]

    # Sleep-related aggregates (optional if no sleep data)
    sleep_duration_minutes: Optional[int] = None
    sleep_quality: Optional[int] = None
    energy_morning: Optional[int] = None

    # Could be extended later with additional stats (e.g. stress trends)

    @classmethod
    def empty(cls, day: date) -> "DaySummary":
        """
        Create an empty summary for a day with no sessions or sleep yet.
        """
        return cls(
            date=day,
            total_sessions=0,
            deep_minutes=0,
            shallow_minutes=0,
            maintenance_minutes=0,
            minutes_by_domain={},
            avg_focus_quality=None,
            avg_progress_rating=None,
            avg_quality_rating=None,
            sleep_duration_minutes=None,
            sleep_quality=None,
            energy_morning=None,
        )


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """
    A planned activity that hasn't happened yet.
    """
    id: Optional[int]
    domain: Domain
    project_name: str
    activity_description: str
    work_type: WorkType
    created_at: datetime
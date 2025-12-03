"""
Service layer for working with PerformanceSession records.

Responsibilities:
- construct PerformanceSession objects from raw input
- validate ranges and logical flow (start vs end)
- delegate persistence to SessionStorage
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from ..core.enums import CompletionStatus, Domain, WorkType
from ..core.models import (
    AfterState,
    BeforeState,
    PerformanceSession,
    SessionContext,
    SessionOutcome,
)
from ..storage.base import SessionId, SessionStorage


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SessionValidationError(ValueError):
    """
    Raised when invalid session data is provided.
    """
    pass


class SessionNotFoundError(LookupError):
    """
    Raised when attempting to load a session that does not exist.
    """
    pass


class SessionAlreadyFinishedError(RuntimeError):
    """
    Raised when attempting to end a session that is already finished.
    """
    pass


# ---------------------------------------------------------------------------
# Input DTOs
# ---------------------------------------------------------------------------


@dataclass
class StartSessionInput:
    """
    Raw input for starting a new performance session.
    """

    domain: Domain
    project_name: str
    activity_description: str
    work_type: WorkType

    planned_duration_min: Optional[int]

    energy_before: int       # 1–10
    stress_before: int       # 1–10
    resistance_before: int   # 1–5


@dataclass
class EndSessionInput:
    """
    Raw input for ending an existing performance session.
    """

    completion_status: CompletionStatus
    progress_rating: int     # 1–5
    quality_rating: int      # 1–5
    focus_quality: int       # 1–5

    moves_main_goal: bool
    evidence_note: Optional[str]

    energy_after: int        # 1–10
    stress_after: int        # 1–10
    feel_tag: str            # e.g. "clear", "drained", "anxious"

@dataclass
class UpdateWorkTypeInput:
    """
    Input for updating a session's work type.
    """

    work_type: WorkType


@dataclass
class ManualSessionInput:
    """
    Raw input for logging a fully completed session with manual
    start/end times and before/after state.
    """

    # Timing
    start_time: datetime
    end_time: datetime

    # Context (same fields as StartSessionInput)
    domain: Domain
    project_name: str
    activity_description: str
    work_type: WorkType
    planned_duration_min: Optional[int]

    # Before-state (same fields as StartSessionInput)
    energy_before: int       # 1–10
    stress_before: int       # 1–10
    resistance_before: int   # 1–5

    # Outcome + after-state (same fields as EndSessionInput)
    completion_status: CompletionStatus
    progress_rating: int     # 1–5
    quality_rating: int      # 1–5
    focus_quality: int       # 1–5

    moves_main_goal: bool
    evidence_note: Optional[str]

    energy_after: int        # 1–10
    stress_after: int        # 1–10
    feel_tag: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SessionService:
    """
    High-level operations on performance sessions.

    This is the main API for:
    - starting a session
    - ending a session
    - querying sessions by date or id
    """

    def __init__(self, storage: SessionStorage) -> None:
        self._storage = storage

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def start_session(self, start_input: StartSessionInput) -> PerformanceSession:
        """
        Create, validate, and persist a new PerformanceSession.

        Returns the newly created session with an assigned id.
        """
        now = datetime.now()
        context = self._build_context(start_input)
        before = self._build_before_state(start_input)

        session = PerformanceSession(
            id=None,
            start_time=now,
            context=context,
            before=before,
            end_time=None,
            after=None,
            outcome=None,
        )

        self._validate_start(session)
        session_with_id = self._storage.create_session(session)
        return session_with_id

    def delete_session(self, session_id: SessionId) -> None:
        self._storage.delete_session(session_id)

    def end_session(self, session_id: SessionId, end_input: EndSessionInput) -> PerformanceSession:
        """
        Finish an existing session by attaching outcome and after-state,
        validating it, and persisting the changes.

        Returns the updated session.
        """
        existing = self._storage.get_session(session_id)
        if existing is None:
            raise SessionNotFoundError(f"Session with id {session_id} not found.")

        if existing.is_finished:
            raise SessionAlreadyFinishedError(f"Session with id {session_id} is already finished.")

        now = datetime.now()
        after = self._build_after_state(end_input)
        outcome = self._build_outcome(end_input)

        existing.end_time = now
        existing.after = after
        existing.outcome = outcome

        self._validate_full_session(existing)
        self._storage.update_session(existing)
        return existing

    def log_manual_session(self, manual_input: ManualSessionInput) -> PerformanceSession:
        """
        Log a fully completed session with explicit start/end times and
        both before/after data in one step.

        This is useful for sessions that already happened (e.g. 07:30–09:00)
        that you are logging after the fact.
        """
        # Reuse existing builders; ManualSessionInput has compatible fields
        context = self._build_context(manual_input)
        before = self._build_before_state(manual_input)
        after = self._build_after_state(manual_input)
        outcome = self._build_outcome(manual_input)

        session = PerformanceSession(
            id=None,
            start_time=manual_input.start_time,
            context=context,
            before=before,
            end_time=manual_input.end_time,
            after=after,
            outcome=outcome,
        )

        self._validate_full_session(session)
        session_with_id = self._storage.create_session(session)
        return session_with_id

    def get_latest_open_session(self) -> Optional[PerformanceSession]:
        """
        Return the most recently started session that has not been finished,
        or None if there is no such session.

        This lets the UI/CLI find the "active" session, including ones that
        were started from a different entry point.
        """
        sessions = self._storage.list_all_sessions()
        open_sessions = [s for s in sessions if not s.is_finished]
        if not open_sessions:
            return None
        return max(open_sessions, key=lambda s: s.start_time)



    def get_session(self, session_id: SessionId) -> PerformanceSession:
        """
        Retrieve a single session by id, or raise if not found.
        """
        session = self._storage.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session with id {session_id} not found.")
        return session

    def get_sessions_for_date(self, day: date) -> List[PerformanceSession]:
        """
        Retrieve all sessions whose start date matches the given date.
        """
        return self._storage.list_sessions_by_date(day)

    def get_sessions_between(
        self,
        start_date: date,
        end_date: date,
    ) -> List[PerformanceSession]:
        """
        Retrieve all sessions whose start date falls within the given range (inclusive).
        """
        return self._storage.list_sessions_between(start_date, end_date)

    def get_all_sessions(self) -> List[PerformanceSession]:
        """
        Retrieve all stored sessions.
        """
        return self._storage.list_all_sessions()

    def update_session_work_type(
        self,
        session_id: SessionId,
        update_input: UpdateWorkTypeInput
    ) -> PerformanceSession:
        """
        Update the work type of an existing session.
        """
        # Get existing session
        session = self.get_session(session_id)

        # Create updated context with new work type
        old_context = session.context
        updated_context = SessionContext(
            domain=old_context.domain,
            project_name=old_context.project_name,
            activity_description=old_context.activity_description,
            work_type=update_input.work_type,
            planned_duration_min=old_context.planned_duration_min
        )

        # Create updated session
        updated_session = PerformanceSession(
            id=session.id,
            start_time=session.start_time,
            context=updated_context,
            before=session.before,
            end_time=session.end_time,
            after=session.after,
            outcome=session.outcome
        )

        # Validate context and save
        self._validate_start(updated_session)
        self._storage.update_session(updated_session)

        return updated_session

    # ------------------------------------------------------------------ #
    # Builders
    # ------------------------------------------------------------------ #

    def _build_context(self, data: StartSessionInput) -> SessionContext:
        return SessionContext(
            domain=data.domain,
            project_name=data.project_name.strip(),
            activity_description=data.activity_description.strip(),
            work_type=data.work_type,
            planned_duration_min=data.planned_duration_min,
        )

    def _build_before_state(self, data: StartSessionInput) -> BeforeState:
        return BeforeState(
            energy=data.energy_before,
            stress=data.stress_before,
            resistance=data.resistance_before,
        )

    def _build_after_state(self, data: EndSessionInput) -> AfterState:
        return AfterState(
            energy=data.energy_after,
            stress=data.stress_after,
            feel_tag=data.feel_tag.strip(),
        )

    def _build_outcome(self, data: EndSessionInput) -> SessionOutcome:
        return SessionOutcome(
            completion_status=data.completion_status,
            progress_rating=data.progress_rating,
            quality_rating=data.quality_rating,
            focus_quality=data.focus_quality,
            moves_main_goal=data.moves_main_goal,
            evidence_note=data.evidence_note.strip() if data.evidence_note else None,
        )

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def _validate_start(self, session: PerformanceSession) -> None:
        """
        Validate the initial part of a session (before it is persisted).
        """
        errors: list[str] = []

        ctx = session.context
        before = session.before

        # Strings
        if not ctx.project_name:
            errors.append("project_name cannot be empty.")
        if not ctx.activity_description:
            errors.append("activity_description cannot be empty.")

        # Planned duration (if provided)
        if ctx.planned_duration_min is not None:
            if ctx.planned_duration_min <= 0:
                errors.append("planned_duration_min must be positive if provided.")
            if ctx.planned_duration_min > 16 * 60:
                errors.append("planned_duration_min appears unrealistically large (> 16 hours).")

        # Ranges for before-state
        if not (1 <= before.energy <= 10):
            errors.append("energy_before must be between 1 and 10.")
        if not (1 <= before.stress <= 10):
            errors.append("stress_before must be between 1 and 10.")
        if not (1 <= before.resistance <= 5):
            errors.append("resistance_before must be between 1 and 5.")

        if errors:
            raise SessionValidationError("\n".join(errors))

    def create_task(self, domain: Domain, project: str, activity: str, work_type: WorkType) -> Task:
        now = _now_iso() 
        pass

    def list_tasks(self) -> List[Task]:
        pass

    def delete_task(self, task_id: int) -> None:
        pass

    def _validate_full_session(self, session: PerformanceSession) -> None:
        """
        Validate a fully-formed session (with end_time, after, outcome).
        """
        errors: list[str] = []

        # Validate start part again (in case it was never checked)
        try:
            self._validate_start(session)
        except SessionValidationError as e:
            errors.append(str(e))

        if session.end_time is None:
            errors.append("end_time must be set when ending a session.")
        else:
            if session.end_time <= session.start_time:
                errors.append("end_time must be after start_time.")

            # Optional sanity check on duration
            if session.duration_minutes is not None:
                if session.duration_minutes < 5:
                    errors.append("Session duration appears too short (< 5 minutes).")
                if session.duration_minutes > 16 * 60:
                    errors.append("Session duration appears unrealistically long (> 16 hours).")

        if session.after is None:
            errors.append("after-state must be provided when ending a session.")
        if session.outcome is None:
            errors.append("outcome must be provided when ending a session.")

        after = session.after
        outcome = session.outcome

        if after is not None:
            if not (1 <= after.energy <= 10):
                errors.append("energy_after must be between 1 and 10.")
            if not (1 <= after.stress <= 10):
                errors.append("stress_after must be between 1 and 10.")
            if not after.feel_tag:
                errors.append("feel_tag cannot be empty.")

        if outcome is not None:
            if not (1 <= outcome.progress_rating <= 5):
                errors.append("progress_rating must be between 1 and 5.")
            if not (1 <= outcome.quality_rating <= 5):
                errors.append("quality_rating must be between 1 and 5.")
            if not (1 <= outcome.focus_quality <= 5):
                errors.append("focus_quality must be between 1 and 5.")

        if errors:
            # Join messages with newlines for a compact but readable error
            raise SessionValidationError("\n".join(errors))

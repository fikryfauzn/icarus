"""
SQLite-backed implementation of SessionStorage.

Responsible for:
- mapping PerformanceSession objects to/from the `sessions` table
- basic CRUD and range queries over session records
"""

from __future__ import annotations

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
from .base import SessionStorage, SessionId
from .sqlite_db import Database


# ---------------------------------------------------------------------------
# Helpers for date/datetime and basic conversions
# ---------------------------------------------------------------------------


def _date_to_str(d: date) -> str:
    return d.isoformat()  # "YYYY-MM-DD"


def _str_to_date(s: str) -> date:
    return date.fromisoformat(s)


def _dt_to_str(dt: datetime) -> str:
    # Truncate microseconds for cleaner storage
    return dt.replace(microsecond=0).isoformat()  # "YYYY-MM-DDTHH:MM:SS"


# In storage/sqlite_session_storage.py

def _str_to_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt

def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _bool_to_int(value: Optional[bool]) -> Optional[int]:
    if value is None:
        return None
    return 1 if value else 0


def _int_to_bool(value: Optional[int]) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


# ---------------------------------------------------------------------------
# Concrete storage implementation
# ---------------------------------------------------------------------------


class SqliteSessionStorage(SessionStorage):
    """
    SQLite implementation of SessionStorage using the `sessions` table.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def create_session(self, session: PerformanceSession) -> PerformanceSession:
        """
        Persist a new PerformanceSession and return it with an assigned id.
        """
        params = self._session_to_insert_params(session)
        sql = """
        INSERT INTO sessions (
            date,
            start_time,
            end_time,
            domain,
            project_name,
            activity_description,
            work_type,
            planned_duration_min,
            energy_before,
            stress_before,
            resistance_before,
            completion_status,
            progress_rating,
            quality_rating,
            focus_quality,
            moves_main_goal,
            energy_after,
            stress_after,
            feel_tag,
            evidence_note,
            created_at,
            updated_at
        )
        VALUES (
            :date,
            :start_time,
            :end_time,
            :domain,
            :project_name,
            :activity_description,
            :work_type,
            :planned_duration_min,
            :energy_before,
            :stress_before,
            :resistance_before,
            :completion_status,
            :progress_rating,
            :quality_rating,
            :focus_quality,
            :moves_main_goal,
            :energy_after,
            :stress_after,
            :feel_tag,
            :evidence_note,
            :created_at,
            :updated_at
        )
        """
        cur = self._db.execute(sql, params)
        new_id = cur.lastrowid

        # Return a new PerformanceSession with the assigned id
        return PerformanceSession(
            id=new_id,
            start_time=session.start_time,
            context=session.context,
            before=session.before,
            end_time=session.end_time,
            after=session.after,
            outcome=session.outcome,
        )

    def update_session(self, session: PerformanceSession) -> None:
        """
        Persist changes to an existing PerformanceSession.
        """
        if session.id is None:
            raise ValueError("Cannot update a session without an id.")

        params = self._session_to_update_params(session)
        sql = """
        UPDATE sessions
        SET
            date                 = :date,
            start_time           = :start_time,
            end_time             = :end_time,
            domain               = :domain,
            project_name         = :project_name,
            activity_description = :activity_description,
            work_type            = :work_type,
            planned_duration_min = :planned_duration_min,
            energy_before        = :energy_before,
            stress_before        = :stress_before,
            resistance_before    = :resistance_before,
            completion_status    = :completion_status,
            progress_rating      = :progress_rating,
            quality_rating       = :quality_rating,
            focus_quality        = :focus_quality,
            moves_main_goal      = :moves_main_goal,
            energy_after         = :energy_after,
            stress_after         = :stress_after,
            feel_tag             = :feel_tag,
            evidence_note        = :evidence_note,
            updated_at           = :updated_at
        WHERE id = :id
        """
        self._db.execute(sql, params)

    def get_session(self, session_id: SessionId) -> Optional[PerformanceSession]:
        """
        Retrieve a single PerformanceSession by its id, if it exists.
        """
        sql = """
        SELECT *
        FROM sessions
        WHERE id = ?
        """
        row = self._db.fetch_one(sql, (session_id,))
        if row is None:
            return None
        return self._row_to_session(row)

    def delete_session(self, session_id: SessionId) -> None:
        sql = "DELETE FROM sessions WHERE id = ?"
        self._db.execute(sql, (session_id,))

    def list_sessions_by_date(self, day: date) -> List[PerformanceSession]:
        """
        List all sessions whose start date matches the given calendar date.
        """
        sql = """
        SELECT *
        FROM sessions
        WHERE date = ?
        ORDER BY start_time ASC
        """
        rows = self._db.fetch_all(sql, (_date_to_str(day),))
        return [self._row_to_session(row) for row in rows]

    def list_sessions_between(
        self,
        start_date: date,
        end_date: date,
    ) -> List[PerformanceSession]:
        """
        List all sessions whose start date falls within the given range (inclusive).
        """
        sql = """
        SELECT *
        FROM sessions
        WHERE date BETWEEN ? AND ?
        ORDER BY date ASC, start_time ASC
        """
        rows = self._db.fetch_all(
            sql,
            (_date_to_str(start_date), _date_to_str(end_date)),
        )
        return [self._row_to_session(row) for row in rows]

    def list_all_sessions(self) -> List[PerformanceSession]:
        """
        List all stored sessions, ordered by date then start time.
        """
        sql = """
        SELECT *
        FROM sessions
        ORDER BY date ASC, start_time ASC
        """
        rows = self._db.fetch_all(sql)
        return [self._row_to_session(row) for row in rows]

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _session_to_insert_params(self, session: PerformanceSession) -> dict:
        """
        Convert a PerformanceSession into a dict for INSERT named parameters.
        """
        now = _now_iso()
        context = session.context
        before = session.before
        after = session.after
        outcome = session.outcome

        return {
            "date": _date_to_str(session.date),
            "start_time": _dt_to_str(session.start_time),
            "end_time": _dt_to_str(session.end_time) if session.end_time else None,

            "domain": context.domain.value,
            "project_name": context.project_name,
            "activity_description": context.activity_description,
            "work_type": context.work_type.value,
            "planned_duration_min": context.planned_duration_min,

            "energy_before": before.energy,
            "stress_before": before.stress,
            "resistance_before": before.resistance,

            "completion_status": (
                outcome.completion_status.value if outcome is not None else None
            ),
            "progress_rating": outcome.progress_rating if outcome is not None else None,
            "quality_rating": outcome.quality_rating if outcome is not None else None,
            "focus_quality": outcome.focus_quality if outcome is not None else None,
            "moves_main_goal": _bool_to_int(
                outcome.moves_main_goal if outcome is not None else None
            ),

            "energy_after": after.energy if after is not None else None,
            "stress_after": after.stress if after is not None else None,
            "feel_tag": after.feel_tag if after is not None else None,
            "evidence_note": outcome.evidence_note if outcome is not None else None,

            "created_at": now,
            "updated_at": now,
        }

    def _session_to_update_params(self, session: PerformanceSession) -> dict:
        """
        Convert a PerformanceSession into a dict for UPDATE named parameters.
        """
        if session.id is None:
            raise ValueError("Cannot build update params for session without id.")

        base = self._session_to_insert_params(session)
        base["id"] = session.id
        # created_at is not updated during UPDATE; DB keeps original value.
        # We do not send created_at here; only updated_at matters.
        return base

    def _row_to_session(self, row) -> PerformanceSession:
        """
        Convert a SQLite row into a fully populated PerformanceSession model.
        """
        # Context
        context = SessionContext(
            domain=Domain(row["domain"]),
            project_name=row["project_name"],
            activity_description=row["activity_description"],
            work_type=WorkType(row["work_type"]),
            planned_duration_min=(
                int(row["planned_duration_min"])
                if row["planned_duration_min"] is not None
                else None
            ),
        )

        # Before state
        before = BeforeState(
            energy=int(row["energy_before"]),
            stress=int(row["stress_before"]),
            resistance=int(row["resistance_before"]),
        )

        # Outcome (may be None)
        if row["completion_status"] is not None:
            outcome = SessionOutcome(
                completion_status=CompletionStatus(row["completion_status"]),
                progress_rating=int(row["progress_rating"]),
                quality_rating=int(row["quality_rating"]),
                focus_quality=int(row["focus_quality"]),
                moves_main_goal=_int_to_bool(row["moves_main_goal"]) or False,
                evidence_note=row["evidence_note"],
            )
        else:
            outcome = None

        # After state (may be None)
        if row["energy_after"] is not None:
            after = AfterState(
                energy=int(row["energy_after"]),
                stress=int(row["stress_after"]),
                feel_tag=row["feel_tag"] or "",
            )
        else:
            after = None

        return PerformanceSession(
            id=int(row["id"]),
            start_time=_str_to_dt(row["start_time"]),
            end_time=_str_to_dt(row["end_time"]) if row["end_time"] is not None else None,
            context=context,
            before=before,
            after=after,
            outcome=outcome,
        )

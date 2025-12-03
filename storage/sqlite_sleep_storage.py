"""
SQLite-backed implementation of SleepStorage.

Responsible for:
- mapping SleepNight objects to/from the `sleep_nights` table
- basic range queries over sleep records
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from ..core.models import SleepNight
from .base import SleepStorage
from .sqlite_db import Database


# ---------------------------------------------------------------------------
# Helpers for date/datetime serialization
# ---------------------------------------------------------------------------


def _date_to_str(d: date) -> str:
    return d.isoformat()  # "YYYY-MM-DD"


def _str_to_date(s: str) -> date:
    return date.fromisoformat(s)


def _dt_to_str(dt: datetime) -> str:
    # Truncate microseconds for cleaner storage
    return dt.replace(microsecond=0).isoformat()  # "YYYY-MM-DDTHH:MM:SS"


def _str_to_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)
    return dt


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Concrete storage implementation
# ---------------------------------------------------------------------------


class SqliteSleepStorage(SleepStorage):
    """
    SQLite implementation of SleepStorage using the `sleep_nights` table.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def save_sleep(self, sleep: SleepNight) -> None:
        """
        Create or update the SleepNight record for the given date.

        Uses INSERT ... ON CONFLICT(date) DO UPDATE to upsert.
        """
        params = self._sleep_to_params(sleep)
        sql = """
        INSERT INTO sleep_nights (
            date,
            sleep_start,
            sleep_end,
            sleep_quality,
            awakenings_count,
            energy_morning,
            mood_morning,
            screen_last_hour,
            caffeine_after_17,
            bedtime_consistent,
            created_at,
            updated_at
        )
        VALUES (
            :date,
            :sleep_start,
            :sleep_end,
            :sleep_quality,
            :awakenings_count,
            :energy_morning,
            :mood_morning,
            :screen_last_hour,
            :caffeine_after_17,
            :bedtime_consistent,
            :created_at,
            :updated_at
        )
        ON CONFLICT(date) DO UPDATE SET
            sleep_start        = excluded.sleep_start,
            sleep_end          = excluded.sleep_end,
            sleep_quality      = excluded.sleep_quality,
            awakenings_count   = excluded.awakenings_count,
            energy_morning     = excluded.energy_morning,
            mood_morning       = excluded.mood_morning,
            screen_last_hour   = excluded.screen_last_hour,
            caffeine_after_17  = excluded.caffeine_after_17,
            bedtime_consistent = excluded.bedtime_consistent,
            updated_at         = excluded.updated_at;
        """
        self._db.execute(sql, params)

    def get_sleep_by_date(self, day: date) -> Optional[SleepNight]:
        """
        Retrieve the SleepNight for a specific calendar date, if any.
        """
        sql = """
        SELECT *
        FROM sleep_nights
        WHERE date = ?
        """
        row = self._db.fetch_one(sql, (_date_to_str(day),))
        if row is None:
            return None
        return self._row_to_sleep(row)

    def list_sleep(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[SleepNight]:
        """
        List SleepNight records in the given date range (inclusive).

        If both start_date and end_date are None, returns all records ordered by date.
        """
        params: list[str] = []
        conditions: list[str] = []

        if start_date is not None:
            conditions.append("date >= ?")
            params.append(_date_to_str(start_date))

        if end_date is not None:
            conditions.append("date <= ?")
            params.append(_date_to_str(end_date))

        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)
        else:
            where_clause = ""

        sql = f"""
        SELECT *
        FROM sleep_nights
        {where_clause}
        ORDER BY date ASC
        """

        rows = self._db.fetch_all(sql, tuple(params))
        return [self._row_to_sleep(row) for row in rows]

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _sleep_to_params(self, sleep: SleepNight) -> dict:
        """
        Convert a SleepNight model into a dict suitable for named SQL parameters.
        """
        now = _now_iso()
        return {
            "date": _date_to_str(sleep.date),
            "sleep_start": _dt_to_str(sleep.sleep_start),
            "sleep_end": _dt_to_str(sleep.sleep_end),
            "sleep_quality": sleep.sleep_quality,
            "awakenings_count": sleep.awakenings_count,
            "energy_morning": sleep.energy_morning,
            "mood_morning": sleep.mood_morning,
            "screen_last_hour": self._bool_to_int(sleep.screen_last_hour),
            "caffeine_after_17": self._bool_to_int(sleep.caffeine_after_17),
            "bedtime_consistent": self._bool_to_int(sleep.bedtime_consistent),
            # created_at is only meaningful on first insert, but we store "now"
            # in both fields; ON CONFLICT keeps updated_at fresh.
            "created_at": now,
            "updated_at": now,
        }

    def _row_to_sleep(self, row) -> SleepNight:
        """
        Convert a SQLite row into a SleepNight model.
        """
        return SleepNight(
            date=_str_to_date(row["date"]),
            sleep_start=_str_to_dt(row["sleep_start"]),
            sleep_end=_str_to_dt(row["sleep_end"]),
            sleep_quality=int(row["sleep_quality"]),
            awakenings_count=int(row["awakenings_count"]),
            energy_morning=int(row["energy_morning"]),
            mood_morning=int(row["mood_morning"]),
            screen_last_hour=self._int_to_bool(row["screen_last_hour"]),
            caffeine_after_17=self._int_to_bool(row["caffeine_after_17"]),
            bedtime_consistent=self._int_to_bool(row["bedtime_consistent"]),
        )

    @staticmethod
    def _bool_to_int(value: Optional[bool]) -> Optional[int]:
        if value is None:
            return None
        return 1 if value else 0

    @staticmethod
    def _int_to_bool(value: Optional[int]) -> Optional[bool]:
        if value is None:
            return None
        return bool(value)

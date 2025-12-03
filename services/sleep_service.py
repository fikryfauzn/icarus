"""
Service layer for working with SleepNight records.

Responsibilities:
- construct SleepNight objects from raw input
- validate ranges and basic consistency
- delegate persistence to SleepStorage
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import List, Optional

from ..core.models import SleepNight
from ..storage.base import SleepStorage


class SleepValidationError(ValueError):
    """
    Raised when an invalid SleepNight payload is provided.
    """
    pass


@dataclass
class SleepInput:
    """
    Raw input data for creating or updating a SleepNight.

    This is what the UI or other callers should build and pass
    into SleepService instead of constructing SleepNight directly.
    """

    date: date
    sleep_start: datetime
    sleep_end: datetime

    sleep_quality: int          # 1–5
    awakenings_count: int       # >= 0

    energy_morning: int         # 1–10
    mood_morning: int           # 1–10

    screen_last_hour: Optional[bool] = None
    caffeine_after_17: Optional[bool] = None
    bedtime_consistent: Optional[bool] = None


class SleepService:
    """
    High-level operations on sleep data.

    This is the main API the rest of the app should use for sleep-related
    operations, rather than talking to storage directly.
    """

    def __init__(self, storage: SleepStorage) -> None:
        self._storage = storage

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def log_sleep(self, sleep_input: SleepInput) -> SleepNight:
        """
        Create or update a SleepNight from the given raw input,
        validate it, persist it, and return the resulting model.
        """
        sleep = self._build_sleep_night(sleep_input)
        self._validate_sleep(sleep)
        self._storage.save_sleep(sleep)
        return sleep

    def get_sleep_by_date(self, day: date) -> Optional[SleepNight]:
        """
        Retrieve the SleepNight for a specific date, if any.
        """
        return self._storage.get_sleep_by_date(day)

    def get_recent_sleep(self, days: int = 7, inclusive_of_today: bool = True) -> List[SleepNight]:
        """
        Retrieve sleep records for the most recent N days.

        If inclusive_of_today is True, the range ends at today.
        Otherwise it ends at yesterday.
        """
        if days <= 0:
            return []

        end = date.today() if inclusive_of_today else date.today() - timedelta(days=1)
        start = end - timedelta(days=days - 1)
        return self._storage.list_sleep(start_date=start, end_date=end)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_sleep_night(self, data: SleepInput) -> SleepNight:
        """
        Construct a SleepNight model from raw input.
        """
        return SleepNight(
            date=data.date,
            sleep_start=data.sleep_start,
            sleep_end=data.sleep_end,
            sleep_quality=data.sleep_quality,
            awakenings_count=data.awakenings_count,
            energy_morning=data.energy_morning,
            mood_morning=data.mood_morning,
            screen_last_hour=data.screen_last_hour,
            caffeine_after_17=data.caffeine_after_17,
            bedtime_consistent=data.bedtime_consistent,
        )

    def _validate_sleep(self, sleep: SleepNight) -> None:
        """
        Validate basic invariants and ranges for a SleepNight.

        Raises SleepValidationError if anything is invalid.
        """
        errors: list[str] = []

        # Time consistency
        if sleep.sleep_end <= sleep.sleep_start:
            errors.append("sleep_end must be after sleep_start.")

        # Guard against obviously wrong durations (e.g. 30-hour 'sleep')
        duration_min = sleep.duration_minutes()
        if duration_min < 60:
            errors.append("Sleep duration appears too short (< 1 hour).")
        if duration_min > 14 * 60:
            errors.append("Sleep duration appears too long (> 14 hours).")

        # Ranges
        if not (1 <= sleep.sleep_quality <= 5):
            errors.append("sleep_quality must be between 1 and 5.")

        if sleep.awakenings_count < 0:
            errors.append("awakenings_count must be >= 0.")

        if not (1 <= sleep.energy_morning <= 10):
            errors.append("energy_morning must be between 1 and 10.")

        if not (1 <= sleep.mood_morning <= 10):
            errors.append("mood_morning must be between 1 and 10.")

        if errors:
            raise SleepValidationError("\n".join(errors))

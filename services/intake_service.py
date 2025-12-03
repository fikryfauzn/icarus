"""
Service for managing biological inputs (Water and Meals).
"""
from __future__ import annotations
from datetime import date, datetime
from dataclasses import dataclass
from typing import Optional
from ..storage.sqlite_db import Database

@dataclass
class DailyIntake:
    date: date
    water_count: int
    breakfast_time: Optional[datetime]
    lunch_time: Optional[datetime]
    dinner_time: Optional[datetime]

class IntakeService:
    def __init__(self, db: Database):
        self._db = db

    def get_intake(self, day: date) -> DailyIntake:
        row = self._db.fetch_one("SELECT * FROM daily_intake WHERE date = ?", (day.isoformat(),))
        if not row:
            return DailyIntake(day, 0, None, None, None)
        
        return DailyIntake(
            date=day,
            water_count=row['water_count'],
            breakfast_time=datetime.fromisoformat(row['breakfast_time']) if row['breakfast_time'] else None,
            lunch_time=datetime.fromisoformat(row['lunch_time']) if row['lunch_time'] else None,
            dinner_time=datetime.fromisoformat(row['dinner_time']) if row['dinner_time'] else None,
        )

    def add_water(self, day: date) -> DailyIntake:
        """Increment water count for the day."""
        now = datetime.now().replace(microsecond=0).isoformat()
        # Upsert logic
        sql = """
        INSERT INTO daily_intake (date, water_count, created_at, updated_at) 
        VALUES (?, 1, ?, ?)
        ON CONFLICT(date) DO UPDATE SET 
            water_count = water_count + 1,
            updated_at = excluded.updated_at
        """
        self._db.execute(sql, (day.isoformat(), now, now))
        return self.get_intake(day)

    def log_meal(self, day: date, meal_type: str) -> DailyIntake:
        """Log a meal (breakfast, lunch, dinner) at the current time."""
        now_dt = datetime.now().replace(microsecond=0)
        now_str = now_dt.isoformat()
        
        col_name = f"{meal_type}_time" # e.g. breakfast_time
        
        # We only update if it's currently NULL (don't overwrite unless we want to support edits, keep simple for now)
        sql = f"""
        INSERT INTO daily_intake (date, {col_name}, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            {col_name} = excluded.{col_name},
            updated_at = excluded.updated_at
        """
        self._db.execute(sql, (day.isoformat(), now_str, now_str, now_str))
        return self.get_intake(day)
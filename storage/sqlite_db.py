"""
SQLite database helper and schema initialization for the performance OS.

This module is responsible for:
- opening the SQLite connection
- enforcing basic pragmas
- creating tables if they do not exist
- providing thin helpers around execute/fetch operations

All higher-level storage logic should live in dedicated storage classes
(e.g. SqliteSleepStorage, SqliteSessionStorage), not here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from ..config.settings import DB_PATH


# ---------------------------------------------------------------------------
# SQL schema definitions
# ---------------------------------------------------------------------------

CREATE_TASKS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    project_name TEXT NOT NULL,
    activity_description TEXT NOT NULL,
    work_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

CREATE_INTAKE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_intake (
    date TEXT PRIMARY KEY,
    
    water_count INTEGER NOT NULL DEFAULT 0,
    
    breakfast_time TEXT,
    lunch_time TEXT,
    dinner_time TEXT,
    
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_SLEEP_NIGHTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sleep_nights (
    date TEXT PRIMARY KEY,

    sleep_start TEXT NOT NULL,
    sleep_end   TEXT NOT NULL,

    sleep_quality     INTEGER NOT NULL,
    awakenings_count  INTEGER NOT NULL DEFAULT 0,

    energy_morning    INTEGER NOT NULL,
    mood_morning      INTEGER NOT NULL,

    screen_last_hour   INTEGER,
    caffeine_after_17  INTEGER,
    bedtime_consistent INTEGER,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CHECK (sleep_quality BETWEEN 1 AND 5),
    CHECK (awakenings_count >= 0),
    CHECK (energy_morning BETWEEN 1 AND 10),
    CHECK (mood_morning BETWEEN 1 AND 10),
    CHECK (screen_last_hour IN (0, 1) OR screen_last_hour IS NULL),
    CHECK (caffeine_after_17 IN (0, 1) OR caffeine_after_17 IS NULL),
    CHECK (bedtime_consistent IN (0, 1) OR bedtime_consistent IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_sleep_nights_date
    ON sleep_nights (date);
"""


CREATE_SESSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity / timing
    date       TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time   TEXT,

    -- Context
    domain               TEXT NOT NULL,
    project_name         TEXT NOT NULL,
    activity_description TEXT NOT NULL,
    work_type            TEXT NOT NULL,
    planned_duration_min INTEGER,

    -- Before state
    energy_before     INTEGER NOT NULL,
    stress_before     INTEGER NOT NULL,
    resistance_before INTEGER NOT NULL,

    -- Outcome (optional until finished)
    completion_status TEXT,
    progress_rating   INTEGER,
    quality_rating    INTEGER,
    focus_quality     INTEGER,
    moves_main_goal   INTEGER,

    -- After state (optional until finished)
    energy_after  INTEGER,
    stress_after  INTEGER,
    feel_tag      TEXT,
    evidence_note TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CHECK (energy_before BETWEEN 1 AND 10),
    CHECK (stress_before BETWEEN 1 AND 10),
    CHECK (resistance_before BETWEEN 1 AND 5),

    CHECK (progress_rating BETWEEN 1 AND 5 OR progress_rating IS NULL),
    CHECK (quality_rating BETWEEN 1 AND 5 OR quality_rating IS NULL),
    CHECK (focus_quality BETWEEN 1 AND 5 OR focus_quality IS NULL),

    CHECK (energy_after BETWEEN 1 AND 10 OR energy_after IS NULL),
    CHECK (stress_after BETWEEN 1 AND 10 OR stress_after IS NULL),

    CHECK (moves_main_goal IN (0, 1) OR moves_main_goal IS NULL)
);


CREATE INDEX IF NOT EXISTS idx_sessions_date
    ON sessions (date);

CREATE INDEX IF NOT EXISTS idx_sessions_domain_date
    ON sessions (domain, date);

CREATE INDEX IF NOT EXISTS idx_sessions_work_type_date
    ON sessions (work_type, date);
"""


# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------


class Database:
    """
    Thin wrapper around a single SQLite connection.

    Responsibilities:
    - open/close the connection
    - initialize the schema
    - expose simple execute/fetch helpers
    """

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else Path(DB_PATH)

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row


        self._enable_foreign_keys()
        self._initialize_schema()

    @property
    def connection(self) -> sqlite3.Connection:
        """
        Expose the raw connection if needed by storage classes.
        """
        return self._conn

    def close(self) -> None:
        """
        Close the underlying SQLite connection.
        """
        if self._conn is not None:
            self._conn.close()

    # ------------------------------------------------------------------ #
    # Schema initialization
    # ------------------------------------------------------------------ #

    def _enable_foreign_keys(self) -> None:
        """
        Ensure foreign key constraints are enforced (future-proofing).
        """
        self._conn.execute("PRAGMA foreign_keys = ON;")

    def _initialize_schema(self) -> None:
        """
        Create required tables and indexes if they do not already exist.
        """
        with self._conn:
            self._conn.executescript(CREATE_SLEEP_NIGHTS_TABLE_SQL)
            self._conn.executescript(CREATE_SESSIONS_TABLE_SQL)
            self._conn.executescript(CREATE_TASKS_TABLE_SQL)
            self._conn.executescript(CREATE_INTAKE_TABLE_SQL)

    # ------------------------------------------------------------------ #
    # Convenience methods
    # ------------------------------------------------------------------ #

    def execute(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> sqlite3.Cursor:
        """
        Execute a single SQL statement with optional parameters.

        Commits the transaction automatically.
        """
        if params is None:
            params = ()
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur

    def executemany(
        self,
        sql: str,
        seq_of_params: Iterable[Sequence[Any]],
    ) -> sqlite3.Cursor:
        """
        Execute a parameterized SQL statement against all parameter sets.

        Commits the transaction automatically.
        """
        cur = self._conn.executemany(sql, seq_of_params)
        self._conn.commit()
        return cur

    def fetch_one(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> Optional[sqlite3.Row]:
        """
        Execute a query and return a single row, or None if no results.
        """
        if params is None:
            params = ()
        cur = self._conn.execute(sql, params)
        row = cur.fetchone()
        return row

    def fetch_all(
        self,
        sql: str,
        params: Sequence[Any] | None = None,
    ) -> list[sqlite3.Row]:
        """
        Execute a query and return all resulting rows as a list.
        """
        if params is None:
            params = ()
        cur = self._conn.execute(sql, params)
        rows = cur.fetchall()
        return list(rows)

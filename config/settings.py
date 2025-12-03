"""
Global configuration for the personal performance OS.

This module should contain constants and simple configuration values only.
No I/O, no side effects.
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Base directory of the project (performance_os/)
BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Directory for all persisted data (can be extended later for exports, etc.)
DATA_DIR: Path = BASE_DIR / "data"

# Path to the SQLite database file
DB_PATH: Path = DATA_DIR / "icarus.db"


# ---------------------------------------------------------------------------
# Date / time formats
# ---------------------------------------------------------------------------

# These are mainly for UI / reporting, not for internal storage. Internally
# we store dates/times using .isoformat() in the database.
DATE_FORMAT: str = "%Y-%m-%d"            # e.g. 2025-11-28
DATETIME_FORMAT: str = "%Y-%m-%d %H:%M"  # e.g. 2025-11-28 13:45

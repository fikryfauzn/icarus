"""
Enums for core domain concepts used throughout the performance OS.
"""

from __future__ import annotations

from enum import Enum


class Domain(str, Enum):
    """
    High-level life areas a session can belong to.
    """

    COLLEGE = "College"
    WORK = "Work"
    PERSONAL_PROJECT = "Personal Project"
    HEALTH = "Health"
    RELATIONSHIPS = "Relationships"
    ADMIN = "Admin"
    LEARNING = "Learning"

    def __str__(self) -> str:
        return self.value


class WorkType(str, Enum):
    """
    Type of work done during a session.
    """

    DEEP = "Deep"
    SHALLOW = "Shallow"
    MAINTENANCE = "Maintenance"
    RECOVERY = "Recovery"
    UNKNOWN = "Unknown"

    def __str__(self) -> str:
        return self.value


class CompletionStatus(str, Enum):
    """
    How a session ended in terms of outcome.
    """

    COMPLETED = "Completed"
    GOOD_PROGRESS = "Good progress"
    MINOR_PROGRESS = "Minor progress"
    BLOCKED = "Blocked"
    ABANDONED = "Abandoned"

    def __str__(self) -> str:
        return self.value

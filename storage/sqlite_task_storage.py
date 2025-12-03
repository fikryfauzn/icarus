from __future__ import annotations
from datetime import datetime
from ..core.models import Task
from ..core.enums import Domain, WorkType
from .sqlite_db import Database

class SqliteTaskStorage:
    def __init__(self, db: Database):
        self._db = db

    def create(self, task: Task) -> Task:
        sql = """INSERT INTO tasks (domain, project_name, activity_description, work_type, created_at) 
                 VALUES (?, ?, ?, ?, ?)"""
        cur = self._db.execute(sql, (
            task.domain.value, task.project_name, task.activity_description, task.work_type.value, datetime.now().isoformat()
        ))
        return Task(id=cur.lastrowid, domain=task.domain, project_name=task.project_name, 
                   activity_description=task.activity_description, work_type=task.work_type, created_at=task.created_at)

    def list(self) -> list[Task]:
        # Simple list all for now
        rows = self._db.fetch_all("SELECT * FROM tasks ORDER BY id DESC")
        return [Task(
            id=row['id'], domain=Domain(row['domain']), project_name=row['project_name'],
            activity_description=row['activity_description'], work_type=WorkType(row['work_type']),
            created_at=datetime.fromisoformat(row['created_at'])
        ) for row in rows]

    def delete(self, task_id: int):
        self._db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
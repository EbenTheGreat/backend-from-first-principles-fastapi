from uuid import uuid4
from datetime import datetime, UTC

task_1_id = str(uuid4())
task_2_id = str(uuid4())

tasks_db = {
    task_1_id: {
        "task_id": task_1_id,
        "title": "fastapi",
        "description": "practice lecture 1",
        "priority": "high",
        "status": "in_progress",
        "due_date": datetime(2026, 2, 14, tzinfo=UTC),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    },

    task_2_id: {
        "task_id": task_2_id,
        "title": "church preparation",
        "description": "iron church clothes",
        "priority": "high",
        "status": "in_progress",
        "due_date": datetime(2026, 2, 14, tzinfo=UTC),
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    },
}
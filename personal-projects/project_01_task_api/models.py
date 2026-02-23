from pydantic import BaseModel, Field, field_validator, model_validator
from uuid import UUID
from datetime import datetime, UTC, date

from enum import Enum
from typing import Optional, List


class Status(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class Priority(str, Enum):
    low = "low"
    high = "high"
    medium = "medium"


class Sort(str, Enum):
    asc = "asc"
    desc = "desc"


class TaskCreate(BaseModel):
    title: str= Field(..., min_length=2, max_length=100)
    description: Optional[str]=Field(None, min_length=2, max_length=5000)
    status: Optional[Status]= Status.pending
    priority: Optional[Priority]= Priority.medium
    due_date: datetime= Field(..., alias="dueDate")

    @field_validator("due_date")
    @classmethod
    def validate_due_date_not_in_the_past(cls, v):
        if v.date() < date.today():
            raise ValueError("due date cannot be in the past")
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    due_date: Optional[datetime] = Field(alias="dueDate", default=None)


class TaskResponse(BaseModel):
    task_id: UUID
    title: str
    description: Optional[str] = None
    status: Status
    priority: Priority
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    due_date: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    totalPages: int   

    model_config = {
        "json_schema_extra": {
            "example": {
                "tasks": [
                    {
                        "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "title": "Study FastAPI lecture 12",
                        "description": "Complete the validation section",
                        "status": "pending",
                        "priority": "high",
                        "created_at": "2026-02-23T10:00:00Z",
                        "updated_at": "2026-02-23T10:00:00Z",
                        "due_date": "2026-02-28T23:59:59Z"
                    }
                ],
                "total": 25,
                "page": 1,
                "totalPages": 3
            }
        }
    }


class BulkCompleteRequest(BaseModel):
    task_ids: List[UUID]

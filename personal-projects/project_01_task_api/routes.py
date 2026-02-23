from fastapi import APIRouter, status, Depends, HTTPException, Query
from db import tasks_db
from models import TaskCreate, TaskResponse, TaskListResponse, TaskUpdate, Status, Priority, Sort, BulkCompleteRequest
from uuid import uuid4
from datetime import datetime, UTC
from typing import Optional, List
import math
from collections import Counter

v1 = APIRouter(prefix="/v1", tags=["v1"])

@v1.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate):
    """
    creates new task
    Returns 201 Created status code
    """
    new_task_id = str(uuid4())
    new_task = {
        "task_id":new_task_id,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        **task.model_dump()
    }

    tasks_db[new_task_id] = new_task
    return new_task



@v1.get("/tasks/stats/", status_code=status.HTTP_200_OK)
async def get_task_stats():
    """
    Returns counts of tasks grouped by status and priority
    """
    tasks = tasks_db.values()
    status_count= Counter(t["status"] for t in tasks)
    priority_count= Counter(t["priority"] for t in tasks)

    return {
        "total_tasks": len(tasks),
        "by_status": status_count,
        "by_priority": priority_count
    }
        

@v1.get("/tasks/{task_id}", response_model=TaskResponse, status_code=status.HTTP_200_OK)
async def get_task_by_id(task_id: str):
    """
    get single task
    Returns 200 OK if found, 404 Not Found if missing
    """
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"task with id {task_id} not found"
        )
    return tasks_db[task_id]

    
@v1.get("/tasks", status_code=status.HTTP_200_OK, response_model=TaskListResponse)
async def get_all_tasks(
    page: int =Query(1, ge=1, description="page number"),
    limit: int = Query(5, ge=1, le=100, description="items per page, Max=100"),
    priority: Optional[Priority]= Query(None, description="Filter by priority"),
    status: Optional[Status]= Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="search in title and description"),
    due_before: Optional[datetime] = Query(None, description="Filter tasks due before this date"),
    overdue: Optional[bool] = Query(None, description="Filter tasks that are overdue"),
    sort_by: str = Query("created_at", description="Field to use in sorting"),
    sort_order: Sort = Query(Sort.asc, description="Sort by ascending or descending order")) -> TaskListResponse:
    """
    list all tasks 
    """

    tasks = list(tasks_db.values())

    if status:
        tasks= [t for t in tasks if t["status"] == status]

    if priority:
        tasks= [t for t in tasks if t["priority"] == priority]

    if due_before:
        if due_before.tzinfo is None:
            due_before = due_before.replace(tzinfo=UTC)
        tasks = [t for t in tasks if t["due_date"] <= due_before]

    now = datetime.now(UTC)
    if overdue is True:
        tasks = [t for t in tasks if t["due_date"] < now and
        t["status"] != Status.completed]
    elif overdue is False:
        tasks = [t for t in tasks if t["due_date"] >= now]

    if search:
        search_lower = search.strip().lower()
        tasks= [t for t in tasks if search_lower in t["title"].lower()
        or (t["description"] and search_lower in t["description"].lower())]

    tasks = sorted(tasks,
    key=lambda t: t.get(sort_by, ""),
    reverse=(sort_order == Sort.desc))

    total = len(tasks)
    start = (page-1) * limit
    end = start + limit
    paginated_tasks = tasks[start:end]
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return {
        "tasks": paginated_tasks,
        "total": total,
        "page": page,
        "totalPages": total_pages
    }


@v1.patch("/tasks/{task_id}", status_code=status.HTTP_200_OK, response_model=TaskResponse)
async def update_task(task_id: str, task_update: TaskUpdate):
    """
    Update task fields
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
        detail=f"Task with task_id: {task_id} not found")

    updated_data= task_update.model_dump(exclude_unset=True)

    task = tasks_db[task_id]

    for field, value in updated_data.items():
        task[field] = value

    task["updated_at"] = datetime.now(UTC)

    return task

    
@v1.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """
    delete task
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id: {task_id} not found")

    del tasks_db[task_id]
    return 

    
@v1.post("/tasks/{task_id}/complete", status_code=status.HTTP_200_OK, response_model=TaskResponse)
async def mark_as_complete(task_id: str):
    """
    mark task as completed
    """
    if task_id not in tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id: {task_id} not found")

    task = tasks_db[task_id]
    if task["status"] == Status.completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
        detail="status is already completed")

    task["status"] = Status.completed
    task["updated_at"] = datetime.now(UTC)

    return task

    
@v1.post("/tasks/bulk-complete")
async def bulk_complete_tasks(payload: BulkCompleteRequest):
    """
    To mark multiple tasks as completed
    """
    completed_ids = []
    errors = []

    for task_id in payload.task_ids:
        task_id_to_string = str(task_id)

        if task_id_to_string not in tasks_db:
            errors.append({"task_id": task_id_to_string,
            "detail": "Not found"})
            continue

        task = tasks_db[task_id_to_string]
        if task["status"] == Status.completed:
            errors.append({
                "task_id": task_id_to_string,
                "detail": "already completed"
            })
            continue

        task["status"] = Status.completed
        task["updated_at"] = datetime.now(UTC)

        completed_ids.append(task_id_to_string)

    return {
        "message": f"successfully completed {len(completed_ids)} tasks",
        "completed_count": len(completed_ids),
        "errors": errors
    }


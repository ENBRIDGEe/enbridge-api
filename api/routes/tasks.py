from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from core.database import SessionLocal
from .auth import get_current_active_user

router = APIRouter()


class TaskCreate(BaseModel):
    title: str | None = None
    milestone_id: UUID | None = None
    due_date: datetime
    completed: bool = False


class TaskUpdate(BaseModel):
    title: str | None = None
    due_date: datetime | None = None
    completed: bool | None = None


def get_user_id(current_user_data: dict):
    return current_user_data["user"]["id"]


def user_owns_milestone(db, milestone_id: UUID, user_id):
    return db.execute(
        text(
            """
            SELECT milestones.id
            FROM milestones
            JOIN goals ON goals.id = milestones.goal_id
            WHERE milestones.id = :milestone_id AND goals.user_id = :user_id
            """
        ),
        {"milestone_id": str(milestone_id), "user_id": str(user_id)},
    ).first()


def get_milestone_title(db, milestone_id: UUID, user_id):
    row = db.execute(
        text(
            """
            SELECT milestones.title
            FROM milestones
            JOIN goals ON goals.id = milestones.goal_id
            WHERE milestones.id = :milestone_id AND goals.user_id = :user_id
            """
        ),
        {"milestone_id": str(milestone_id), "user_id": str(user_id)},
    ).mappings().first()
    return row["title"] if row else None


def user_owns_task(db, task_id: UUID, user_id):
    task = db.execute(
        text(
            """
            SELECT tasks.*
            FROM tasks
            WHERE tasks.id = :task_id AND tasks.user_id = :user_id
            """
        ),
        {"task_id": str(task_id), "user_id": str(user_id)},
    ).mappings().first()
    return dict(task) if task else None


@router.post("/tasks")
async def create_task(
    task_data: TaskCreate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        title = task_data.title
        milestone_id = str(task_data.milestone_id) if task_data.milestone_id else None

        if task_data.milestone_id:
            if not user_owns_milestone(db, task_data.milestone_id, user_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
            if not title:
                title = get_milestone_title(db, task_data.milestone_id, user_id)

        if not title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task title is required when no milestone is provided",
            )

        task = db.execute(
            text(
                """
                INSERT INTO tasks (
                    id,
                    user_id,
                    milestone_id,
                    title,
                    due_date,
                    completed,
                    created_at,
                    completed_at
                )
                VALUES (
                    :id,
                    :user_id,
                    :milestone_id,
                    :title,
                    :due_date,
                    :completed,
                    CURRENT_TIMESTAMP,
                    :completed_at
                )
                RETURNING *
                """
            ),
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "milestone_id": milestone_id,
                "title": title,
                "due_date": task_data.due_date,
                "completed": task_data.completed,
                "completed_at": datetime.now() if task_data.completed else None,
            },
        ).mappings().first()
        db.commit()
        return dict(task)
    finally:
        db.close()


@router.get("/tasks")
async def list_tasks(current_user_data: Annotated[dict, Depends(get_current_active_user)]):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        tasks = db.execute(
            text(
                """
                SELECT tasks.*
                FROM tasks
                WHERE tasks.user_id = :user_id
                ORDER BY tasks.due_date
                """
            ),
            {"user_id": str(user_id)},
        ).mappings().all()
        return {"tasks": [dict(task) for task in tasks]}
    finally:
        db.close()


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_task(db, task_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        task = db.execute(
            text(
                """
                UPDATE tasks
                SET title = COALESCE(:title, title),
                    due_date = COALESCE(:due_date, due_date),
                    completed = COALESCE(:completed, completed),
                    completed_at = CASE
                        WHEN :completed IS NULL THEN completed_at
                        WHEN :completed = TRUE THEN COALESCE(completed_at, CURRENT_TIMESTAMP)
                        ELSE NULL
                    END
                WHERE id = :task_id AND user_id = :user_id
                RETURNING *
                """
            ),
            {
                "task_id": str(task_id),
                "user_id": str(user_id),
                "title": task_data.title,
                "due_date": task_data.due_date,
                "completed": task_data.completed,
            },
        ).mappings().first()
        db.commit()
        return dict(task)
    finally:
        db.close()


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_task(db, task_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        db.execute(text("DELETE FROM tasks WHERE id = :task_id AND user_id = :user_id"), {"task_id": str(task_id), "user_id": str(user_id)})
        db.commit()
        return {"message": "Task deleted"}
    finally:
        db.close()

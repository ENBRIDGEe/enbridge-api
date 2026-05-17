from datetime import datetime, date
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from core.database import SessionLocal
from .auth import get_current_active_user

router = APIRouter()


class GoalCreate(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    target_date: datetime | None = None
    status: str = "active"
    progress_percentage: float = 0.0
    deadline: datetime | None = None


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    target_date: datetime | None = None
    deadline: datetime | None = None
    status: str | None = None
    progress_percentage: float | None = None


class GoalActivityCreate(BaseModel):
    activity_date: date


def get_user_id(current_user_data: dict):
    return current_user_data["user"]["id"]


def get_goal_for_user(db, goal_id: UUID, user_id):
    goal = db.execute(
        text("SELECT * FROM goals WHERE id = :goal_id AND user_id = :user_id"),
        {"goal_id": str(goal_id), "user_id": str(user_id)},
    ).mappings().first()
    return dict(goal) if goal else None


def user_owns_goal(db, goal_id: UUID, user_id):
    return db.execute(
        text("SELECT id FROM goals WHERE id = :goal_id AND user_id = :user_id"),
        {"goal_id": str(goal_id), "user_id": str(user_id)},
    ).first()


@router.post("/goals")
async def create_goal(
    goal_data: GoalCreate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        goal = db.execute(
            text(
                """
                INSERT INTO goals (
                    id,
                    user_id,
                    title,
                    description,
                    category,
                    target_date,
                    status,
                    progress_percentage,
                    created_at,
                    updated_at,
                    deadline
                )
                VALUES (
                    :id,
                    :user_id,
                    :title,
                    :description,
                    :category,
                    :target_date,
                    :status,
                    :progress_percentage,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    :deadline
                )
                RETURNING *
                """
            ),
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "title": goal_data.title,
                "description": goal_data.description,
                "category": goal_data.category,
                "target_date": goal_data.target_date or goal_data.deadline,
                "status": goal_data.status,
                "progress_percentage": goal_data.progress_percentage,
                "deadline": goal_data.deadline or goal_data.target_date,
            },
        ).mappings().first()
        db.commit()
        return dict(goal)
    finally:
        db.close()


@router.get("/goals")
async def list_goals(current_user_data: Annotated[dict, Depends(get_current_active_user)]):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        goals = db.execute(
            text("SELECT * FROM goals WHERE user_id = :user_id ORDER BY COALESCE(target_date, deadline), created_at"),
            {"user_id": str(user_id)},
        ).mappings().all()
        return {"goals": [dict(goal) for goal in goals]}
    finally:
        db.close()


@router.get("/goals/{goal_id}")
async def read_goal(
    goal_id: UUID,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        goal = get_goal_for_user(db, goal_id, user_id)
        if not goal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
        return goal
    finally:
        db.close()


@router.patch("/goals/{goal_id}")
async def update_goal(
    goal_id: UUID,
    goal_data: GoalUpdate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        goal = get_goal_for_user(db, goal_id, user_id)
        if not goal:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        updated = db.execute(
            text(
                """
                UPDATE goals
                SET title = COALESCE(:title, title),
                    description = COALESCE(:description, description),
                    category = COALESCE(:category, category),
                    target_date = COALESCE(:target_date, target_date),
                    deadline = COALESCE(:deadline, deadline),
                    status = COALESCE(:status, status),
                    progress_percentage = COALESCE(:progress_percentage, progress_percentage),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :goal_id AND user_id = :user_id
                RETURNING *
                """
            ),
            {
                "goal_id": str(goal_id),
                "user_id": str(user_id),
                "title": goal_data.title,
                "description": goal_data.description,
                "category": goal_data.category,
                "target_date": goal_data.target_date,
                "deadline": goal_data.deadline,
                "status": goal_data.status,
                "progress_percentage": goal_data.progress_percentage,
            },
        ).mappings().first()
        db.commit()
        return dict(updated)
    finally:
        db.close()


@router.delete("/goals/{goal_id}")
async def delete_goal(
    goal_id: UUID,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        result = db.execute(
            text("DELETE FROM goals WHERE id = :goal_id AND user_id = :user_id RETURNING id"),
            {"goal_id": str(goal_id), "user_id": str(user_id)},
        ).first()
        db.commit()
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
        return {"message": "Goal deleted"}
    finally:
        db.close()


@router.post("/goals/{goal_id}/activity")
async def add_goal_activity(
    goal_id: UUID,
    activity_data: GoalActivityCreate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_goal(db, goal_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        existing = db.execute(
            text(
                """
                SELECT * FROM goal_activity
                WHERE goal_id = :goal_id AND activity_date = :activity_date
                """
            ),
            {"goal_id": str(goal_id), "activity_date": activity_data.activity_date},
        ).mappings().first()
        if existing:
            return dict(existing)

        activity = db.execute(
            text(
                """
                INSERT INTO goal_activity (id, goal_id, activity_date, created_at)
                VALUES (:id, :goal_id, :activity_date, CURRENT_TIMESTAMP)
                RETURNING *
                """
            ),
            {"id": str(uuid4()), "goal_id": str(goal_id), "activity_date": activity_data.activity_date},
        ).mappings().first()
        db.commit()
        return dict(activity)
    finally:
        db.close()


@router.get("/goals/{goal_id}/activity")
async def list_goal_activity(
    goal_id: UUID,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_goal(db, goal_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        rows = db.execute(
            text("SELECT * FROM goal_activity WHERE goal_id = :goal_id ORDER BY activity_date"),
            {"goal_id": str(goal_id)},
        ).mappings().all()
        return {"activity": [dict(row) for row in rows]}
    finally:
        db.close()


@router.delete("/goals/{goal_id}/activity")
async def delete_goal_activity(
    goal_id: UUID,
    activity_date: date,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_goal(db, goal_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        db.execute(
            text("DELETE FROM goal_activity WHERE goal_id = :goal_id AND activity_date = :activity_date"),
            {"goal_id": str(goal_id), "activity_date": activity_date},
        )
        db.commit()
        return {"message": "Goal activity deleted"}
    finally:
        db.close()

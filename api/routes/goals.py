from datetime import datetime
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
    category: str
    deadline: datetime
    status: str = "active"


class GoalUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    deadline: datetime | None = None
    status: str | None = None


def get_user_id(current_user_data: dict):
    return current_user_data["user"]["id"]


def get_goal_for_user(db, goal_id: UUID, user_id):
    goal = db.execute(
        text("SELECT * FROM goals WHERE id = :goal_id AND user_id = :user_id"),
        {"goal_id": str(goal_id), "user_id": str(user_id)},
    ).mappings().first()
    return dict(goal) if goal else None


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
                INSERT INTO goals (id, user_id, title, category, deadline, status)
                VALUES (:id, :user_id, :title, :category, :deadline, :status)
                RETURNING *
                """
            ),
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "title": goal_data.title,
                "category": goal_data.category,
                "deadline": goal_data.deadline,
                "status": goal_data.status,
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
            text("SELECT * FROM goals WHERE user_id = :user_id ORDER BY deadline"),
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
                    category = COALESCE(:category, category),
                    deadline = COALESCE(:deadline, deadline),
                    status = COALESCE(:status, status)
                WHERE id = :goal_id AND user_id = :user_id
                RETURNING *
                """
            ),
            {
                "goal_id": str(goal_id),
                "user_id": str(user_id),
                "title": goal_data.title,
                "category": goal_data.category,
                "deadline": goal_data.deadline,
                "status": goal_data.status,
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

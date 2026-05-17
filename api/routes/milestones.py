from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from core.database import SessionLocal
from .auth import get_current_active_user

router = APIRouter()


class MilestoneCreate(BaseModel):
    goal_id: UUID
    title: str | None = None
    description: str | None = None
    target_date: datetime
    order_index: int
    completed: bool = False


def get_user_id(current_user_data: dict):
    return current_user_data["user"]["id"]


def user_owns_goal(db, goal_id: UUID, user_id):
    return db.execute(
        text("SELECT id FROM goals WHERE id = :goal_id AND user_id = :user_id"),
        {"goal_id": str(goal_id), "user_id": str(user_id)},
    ).first()


@router.post("/milestones")
async def create_milestone(
    milestone_data: MilestoneCreate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_goal(db, milestone_data.goal_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        milestone = db.execute(
            text(
                """
                INSERT INTO milestones (
                    id,
                    goal_id,
                    title,
                    description,
                    order_index,
                    target_date,
                    completed,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :goal_id,
                    :title,
                    :description,
                    :order_index,
                    :target_date,
                    :completed,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                RETURNING *
                """
            ),
            {
                "id": str(uuid4()),
                "goal_id": str(milestone_data.goal_id),
                "title": milestone_data.title or f"Milestone {milestone_data.order_index}",
                "description": milestone_data.description,
                "target_date": milestone_data.target_date,
                "order_index": milestone_data.order_index,
                "completed": milestone_data.completed,
            },
        ).mappings().first()
        db.commit()
        return dict(milestone)
    finally:
        db.close()


@router.get("/milestones/goal/{goal_id}")
async def list_goal_milestones(
    goal_id: UUID,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        if not user_owns_goal(db, goal_id, user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")

        milestones = db.execute(
            text("SELECT * FROM milestones WHERE goal_id = :goal_id ORDER BY order_index"),
            {"goal_id": str(goal_id)},
        ).mappings().all()
        return {"milestones": [dict(milestone) for milestone in milestones]}
    finally:
        db.close()

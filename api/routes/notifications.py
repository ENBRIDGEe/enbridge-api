from datetime import datetime
from typing import Annotated
from uuid import uuid4
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from core.database import SessionLocal
from .auth import get_current_active_user

router = APIRouter()


class NotificationUpdate(BaseModel):
    push_enabled: bool | None = None
    remainder: datetime | None = None


def get_user_id(current_user_data: dict):
    return current_user_data["user"]["id"]


def get_or_create_settings(db, user_id):
    settings = db.execute(
        text("SELECT * FROM notification_settings WHERE user_id = :user_id"),
        {"user_id": str(user_id)},
    ).mappings().first()

    if settings:
        return dict(settings)

    settings = db.execute(
        text(
            """
            INSERT INTO notification_settings (id, user_id, push_enabled, remainder)
            VALUES (:id, :user_id, TRUE, NULL)
            RETURNING *
            """
        ),
        {"id": str(uuid4()), "user_id": str(user_id)},
    ).mappings().first()
    db.commit()
    return dict(settings)


@router.get("/notifications/settings")
async def read_notification_settings(
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        return get_or_create_settings(db, user_id)
    finally:
        db.close()


@router.patch("/notifications/settings")
async def update_notification_settings(
    settings_data: NotificationUpdate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        get_or_create_settings(db, user_id)
        settings = db.execute(
            text(
                """
                UPDATE notification_settings
                SET push_enabled = COALESCE(:push_enabled, push_enabled),
                    remainder = COALESCE(:remainder, remainder)
                WHERE user_id = :user_id
                RETURNING *
                """
            ),
            {
                "user_id": str(user_id),
                "push_enabled": settings_data.push_enabled,
                "remainder": settings_data.remainder,
            },
        ).mappings().first()
        db.commit()
        return dict(settings)
    finally:
        db.close()

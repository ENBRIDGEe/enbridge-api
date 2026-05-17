from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from core.database import SessionLocal
from .auth import get_current_active_user


router = APIRouter()


class FocusSessionCreate(BaseModel):
    session_duration_minutes: int = Field(gt=0)
    completed_at: datetime
    date: date


class FocusRange(str, Enum):
    day = "day"
    week = "week"
    month = "month"


def get_user_id(current_user_data: dict):
    return current_user_data["user"]["id"]


def build_focus_time_display(total_minutes: int) -> str:
    hours, minutes = divmod(int(total_minutes), 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes or not parts:
        parts.append(f"{minutes}m")
    return " ".join(parts)


def get_period_bounds(target_date: date, focus_range: FocusRange) -> tuple[date, date]:
    if focus_range == FocusRange.day:
        return target_date, target_date + timedelta(days=1)

    if focus_range == FocusRange.week:
        start_date = target_date - timedelta(days=6)
        return start_date, target_date + timedelta(days=1)

    # month
    start_date = target_date.replace(day=1)
    if target_date.month == 12:
        end_date = target_date.replace(year=target_date.year + 1, month=1, day=1)
    else:
        end_date = target_date.replace(month=target_date.month + 1, day=1)
    return start_date, end_date


def get_daily_total_minutes(db, user_id, day: date) -> int:
    row = db.execute(
        text(
            """
            SELECT COALESCE(SUM(session_duration_minutes), 0) AS total_minutes
            FROM focus_sessions
            WHERE user_id = :user_id AND date = :day
            """
        ),
        {"user_id": str(user_id), "day": day},
    ).mappings().first()
    return int(row["total_minutes"] or 0) if row else 0


@router.post("/analytics/focus-sessions", status_code=status.HTTP_201_CREATED)
async def record_focus_session(
    session_data: FocusSessionCreate,
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
):
    user_id = get_user_id(current_user_data)
    db = SessionLocal()
    try:
        session_id = str(uuid4())
        inserted = db.execute(
            text(
                """
                INSERT INTO focus_sessions (
                    id,
                    user_id,
                    session_duration_minutes,
                    completed_at,
                    date,
                    created_at
                )
                VALUES (
                    :id,
                    :user_id,
                    :session_duration_minutes,
                    :completed_at,
                    :date,
                    CURRENT_TIMESTAMP
                )
                RETURNING id
                """
            ),
            {
                "id": session_id,
                "user_id": str(user_id),
                "session_duration_minutes": session_data.session_duration_minutes,
                "completed_at": session_data.completed_at,
                "date": session_data.date,
            },
        ).mappings().first()

        if not inserted:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not record session")

        daily_total_minutes = get_daily_total_minutes(db, user_id, session_data.date)
        db.commit()

        return {
            "message": "Session recorded",
            "session_id": str(inserted["id"]),
            "daily_total_minutes": daily_total_minutes,
        }
    finally:
        db.close()


@router.get("/analytics/focus-time")
async def get_focus_time(
    current_user_data: Annotated[dict, Depends(get_current_active_user)],
    date: date | None = Query(default=None),
    range: FocusRange = Query(default=FocusRange.day),
):
    user_id = get_user_id(current_user_data)
    target_date = date or datetime.now(timezone.utc).date()
    start_date, end_date = get_period_bounds(target_date, range)

    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT
                    COALESCE(SUM(session_duration_minutes), 0) AS total_minutes,
                    COUNT(*) AS sessions_count
                FROM focus_sessions
                WHERE user_id = :user_id
                  AND date >= :start_date
                  AND date < :end_date
                """
            ),
            {
                "user_id": str(user_id),
                "start_date": start_date,
                "end_date": end_date,
            },
        ).mappings().first()

        total_minutes = int(row["total_minutes"] or 0) if row else 0
        sessions_count = int(row["sessions_count"] or 0) if row else 0
        avg_session_minutes = round(total_minutes / sessions_count, 2) if sessions_count else 0.0

        return {
            "date": target_date.isoformat(),
            "total_minutes": total_minutes,
            "sessions_count": sessions_count,
            "avg_session_minutes": avg_session_minutes,
            "focus_time_display": build_focus_time_display(total_minutes),
        }
    finally:
        db.close()

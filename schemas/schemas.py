from pydantic import BaseModel, Field
from datetime import datetime, date
from uuid import UUID
from typing import Literal

class Token(BaseModel):
    access_token: str
    token_type: str

class Goals(BaseModel):
    id: UUID | None = None
    user_id: UUID
    title: str
    category: str
    deadline: date
    status: str

class Milestones(BaseModel):
    id: UUID | None = None
    goal_id: UUID
    target_date: date
    order_index: int

class Notification_settings(BaseModel):
    id: UUID | None = None
    user_id: UUID
    push_enabled: bool
    remainder: datetime | None = None

class Progress_logs(BaseModel):
    id: UUID | None = None
    completion_percent: float
    logged_at: datetime


class FocusSessionCreate(BaseModel):
    session_duration_minutes: int = Field(gt=0)
    completed_at: datetime
    date: date


class FocusSessionRecord(BaseModel):
    id: UUID
    user_id: UUID
    session_duration_minutes: int
    completed_at: datetime
    date: date
    created_at: datetime


class FocusTimeResponse(BaseModel):
    date: date
    total_minutes: int
    sessions_count: int
    avg_session_minutes: float
    focus_time_display: str


FocusTimeRange = Literal["day", "week", "month"]

class Subscriptions(BaseModel):
    id: UUID | None = None
    plan: str

class Tasks(BaseModel):
    id: UUID | None = None
    milestone_id: UUID
    due_date: date
    completed: bool

class Users(BaseModel):
    id: UUID
    name: str
    email: str
    password_hash: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
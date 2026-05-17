from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime, date, time
from uuid import UUID
from typing import Literal

class Token(BaseModel):
    access_token: str
    token_type: str
    auth_method: str | None = None

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: UUID
    name: str | None
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

class UserPublic(BaseModel):
    id: UUID
    name: str | None

class UserUpdate(BaseModel):
    name: str | None = None

class Goals(BaseModel):
    id: UUID | None = None
    user_id: UUID
    title: str
    description: str | None = None
    category: str | None = None
    target_date: datetime | None = None
    status: str
    progress_percentage: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deadline: datetime | None = None

class Milestones(BaseModel):
    id: UUID | None = None
    goal_id: UUID
    title: str
    description: str | None = None
    target_date: datetime
    order_index: int
    completed: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GoalActivity(BaseModel):
    id: UUID | None = None
    goal_id: UUID
    activity_date: date
    created_at: datetime | None = None


class RefreshToken(BaseModel):
    id: UUID | None = None
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime | None = None

class Notification_settings(BaseModel):
    id: UUID | None = None
    user_id: UUID
    push_enabled: bool
    email_enabled: bool
    reminder_time: time | datetime | None = Field(default=None, alias="remainder")
    timezone: str = "UTC"

    model_config = ConfigDict(populate_by_name=True)

class Progress_logs(BaseModel):
    id: UUID | None = None
    goal_id: UUID
    completion_percentage: float
    streak_days: int
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
    user_id: UUID
    title: str
    due_date: datetime
    completed: bool
    created_at: datetime | None = None
    completed_at: datetime | None = None
    milestone_id: UUID | None = None


class Users(BaseModel):
    id: UUID | None = None
    name: str | None = None
    email: EmailStr
    password_hash: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

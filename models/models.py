from sqlalchemy.orm import declarative_base
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Float, func, Integer, Date, Text, Time
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class Goals(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True, index=True)
    target_date = Column(DateTime, nullable=True, index=True)
    status = Column(String, nullable=False, index=True)
    progress_percentage = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, index=True, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, index=True, server_default=func.now(), onupdate=func.now())
    deadline = Column(DateTime, nullable=True, index=True)


class Milestones(Base):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, index=True)
    target_date = Column(DateTime, nullable=True, index=True)
    completed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, index=True, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, index=True, server_default=func.now(), onupdate=func.now())


class Goal_activity(Base):
    __tablename__ = "goal_activity"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    activity_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True, server_default=func.now())


class Notification_settings(Base):
    __tablename__ = "notification_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    push_enabled = Column(Boolean, nullable=False, default=True)
    email_enabled = Column(Boolean, nullable=False, default=True)
    reminder_time = Column(Time, nullable=True)
    timezone = Column(String, nullable=False, default="UTC")


class Progress_logs(Base):
    __tablename__ = "progress_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    completion_percentage = Column(Float, nullable=False, index=True)
    streak_days = Column(Integer, nullable=False)
    logged_at = Column(DateTime, nullable=False, index=True)


class Focus_sessions(Base):
    __tablename__ = "focus_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_duration_minutes = Column(Integer, nullable=False)
    completed_at = Column(DateTime, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, nullable=True, index=True, server_default=func.now())


class Refresh_tokens(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, index=True, unique=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=True, index=True, server_default=func.now())


class Subscriptions(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    plan = Column(String, index=True)


class Tasks(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    completed = Column(Boolean, nullable=False, default=False)
    title = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, index=True, server_default=func.now())
    completed_at = Column(DateTime, nullable=True, index=True)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=True, index=True)


class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name = Column(String, nullable=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, index=True, server_default=func.now())
    updated_at = Column(DateTime, index=True, server_default=func.now(), onupdate=func.now())

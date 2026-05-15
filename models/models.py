from sqlalchemy.orm import declarative_base
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Float, func, Integer, Date
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


class Goals(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, index=True)
    category = Column(String, index=True)
    deadline = Column(DateTime, index=True)
    status = Column(String, index=True)


class Milestones(Base):
    __tablename__ = "milestones"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id"), nullable=False)
    target_date = Column(DateTime, index=True)
    order_index = Column(Integer, index=True)


class Notification_settings(Base):
    __tablename__ = "notification_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    push_enabled = Column(Boolean, default=True)
    remainder = Column(DateTime, nullable=True)


class Progress_logs(Base):
    __tablename__ = "progress_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    completion_percent = Column(Float, index=True)
    logged_at = Column(DateTime, index=True)


class Focus_sessions(Base):
    __tablename__ = "focus_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_duration_minutes = Column(Integer, nullable=False)
    completed_at = Column(DateTime, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, index=True, server_default=func.now())


class Subscriptions(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    plan = Column(String, index=True)


class Tasks(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"), nullable=False)
    due_date = Column(DateTime, index=True)
    completed = Column(Boolean, default=False)


class Users(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid4)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, index=True, server_default=func.now())
    updated_at = Column(DateTime, index=True, server_default=func.now(), onupdate=func.now())

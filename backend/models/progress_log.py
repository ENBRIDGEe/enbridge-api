from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class Progress_logs(Base):
    __tablename__ = "progress_logs"

    id = Column(Integer, primary_key=True, index=True)
    completion_percent = Column(Float, index=True)
    logged_at = Column(DateTime, index=True)

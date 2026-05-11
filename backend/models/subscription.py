from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class Subscriptions(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    plan = Column(String, index=True)

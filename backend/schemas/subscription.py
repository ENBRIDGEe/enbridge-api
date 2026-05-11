from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Subscriptions(BaseModel):
    plan: str

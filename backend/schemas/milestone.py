from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Milestones(BaseModel):
    goal_id: int
    target_date: date
    order_index: int
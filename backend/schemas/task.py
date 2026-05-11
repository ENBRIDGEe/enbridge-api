from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Tasks(BaseModel):
    milestone_id: int
    due_date: date
    completed: bool
from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Goals(BaseModel):
    user_id: int
    title: str
    category: str
    deadline: date
    status: str

from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Users(BaseModel):
    id: int
    name: str
    email: str
    password_hash: str
    created_at: datetime
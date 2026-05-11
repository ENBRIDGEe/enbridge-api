from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Progress_logs(BaseModel):
    completion_percent: float
    logged_at: datetime

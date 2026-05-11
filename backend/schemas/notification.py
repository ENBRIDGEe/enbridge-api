from uuid import uuid
from datetime import datetime, date
from pydantic import BaseModel

class Notification_settings(BaseModel):
    push_enabled: bool
    remainder: time
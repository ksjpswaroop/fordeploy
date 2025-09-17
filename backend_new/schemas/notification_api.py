from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.schemas.base import NotificationType, Priority


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: Priority
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    updated_at: datetime
    read_at: Optional[datetime] = None
    dismissed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

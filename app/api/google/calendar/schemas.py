from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class EventDetails(BaseModel):
    summary: str
    location: str
    description: str
    start: datetime
    end: datetime
    attendees: List[EmailStr]
    create_meet_link: Optional[bool] = False

class EventResponse(BaseModel):
    message: str
    event_id: str
    hangoutLink: Optional[str] = None

class EventAttendeeSchema(BaseModel):
    id: int
    email: EmailStr
    class Config:
        orm_mode = True

class ScheduledEventSchema(BaseModel):
    id: UUID
    user_id: UUID
    event_id: str
    summary: str
    location: Optional[str]
    description: Optional[str]
    start: datetime
    end: datetime
    hangout_link: Optional[str]
    created_at: datetime
    attendees: List[EventAttendeeSchema]
    class Config:
        orm_mode = True

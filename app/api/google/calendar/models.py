from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
import uuid

class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    start = Column(DateTime, nullable=False)
    end = Column(DateTime, nullable=False)
    hangout_link = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    user = relationship("User", back_populates="scheduled_events")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")

class EventAttendee(Base):
    __tablename__ = "event_attendees"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("scheduled_events.id", ondelete="CASCADE"), nullable=False)
    email = Column(String, nullable=False)
    event = relationship("ScheduledEvent", back_populates="attendees")
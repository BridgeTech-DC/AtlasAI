from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    recipient_name = Column(String, nullable=False)
    user_prompt = Column(Text, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    conversation = relationship("Conversation", back_populates="email_drafts")
    sent_emails = relationship("SentEmail", back_populates="email_draft", cascade="all, delete-orphan")

class SentEmail(Base):
    __tablename__ = "sent_emails"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    email_draft_id = Column(Integer, ForeignKey("email_drafts.id", ondelete="CASCADE"), nullable=False)
    recipient_email = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=False, server_default=func.now())

    conversation = relationship("Conversation", back_populates="sent_emails")
    email_draft = relationship("EmailDraft", back_populates="sent_emails")
    
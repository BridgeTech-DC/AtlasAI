from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime
from uuid import UUID

class EmailDraftSchema(BaseModel):
    subject: str
    body: str

    class Config:
        orm_mode = True

class SentEmailResponse(BaseModel):
    id: int
    conversation_id: UUID
    recipient_email: EmailStr
    sent_at: datetime
    email_draft: EmailDraftSchema

    class Config:
        orm_mode = True

class DraftEmailRequest(BaseModel):
    user_prompt: str

class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str
    message_body: str

class ContactSearchRequest(BaseModel):
    recipient_name: List[str]

class RecipientSchema(BaseModel):
    name: str
    email: EmailStr

class ContactSearchResponse(BaseModel):
    suggested_recipients: List[RecipientSchema]

from pydantic import BaseModel, EmailStr
from typing import List

class DraftEmailRequest(BaseModel):
    """Request schema for drafting an email."""
    user_prompt: str

class SendEmailRequest(BaseModel):
    """Request schema for sending an email."""
    to: EmailStr
    subject: str
    message_body: str

class ContactSearchRequest(BaseModel):  # New schema for contact search
    """Request schema for searching contacts."""
    recipient_name: List[str]  # Corrected type: List of strings

class RecipientSchema(BaseModel):  # New schema for a recipient with name and email
    """Schema for a recipient with name and email."""
    name: str
    email: EmailStr

class ContactSearchResponse(BaseModel):
    """Response schema for contact search."""
    suggested_recipients: List[RecipientSchema]
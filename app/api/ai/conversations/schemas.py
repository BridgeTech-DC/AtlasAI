from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from app.api.persona.schemas import PersonaSchema  # Import the PersonaSchema
from uuid import UUID

class MessageSchema(BaseModel):
    """Schema for a message in the conversation history."""
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

class ConversationHistorySchema(BaseModel):
    """Schema for conversation history."""
    id: int
    user_id: UUID
    persona: PersonaSchema  # Include persona details
    created_at: datetime
    messages: List[MessageSchema]

    class Config:
        orm_mode = True

class MessageCreate(BaseModel):
    role: str
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
from app.api.persona.schemas import PersonaSchema  # Import the PersonaSchema
from uuid import UUID

class MessageResponse(BaseModel):
    id: int
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode: True

class ConversationHistorySchema(BaseModel):
    id: UUID
    user_id: UUID
    persona_id: int
    created_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        orm_mode: True

class MessageCreate(BaseModel):
    role: str
    content: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True
from pydantic import BaseModel
from typing import List
from datetime import datetime
from uuid import UUID

# Assuming PersonaSchema is defined elsewhere and imported correctly
from app.api.persona.schemas import PersonaSchema

class MessageResponse(BaseModel):
    id: int
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        orm_mode = True

class ConversationHistorySchema(BaseModel):
    id: UUID
    user_id: UUID
    persona_id: int
    title: str  # Include the title field
    created_at: datetime
    updated_at: datetime  # Include the updated_at field
    messages: List[MessageResponse] = []

    class Config:
        orm_mode: True

class MessageCreate(BaseModel):
    role: str
    content: str

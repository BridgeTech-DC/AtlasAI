from pydantic import BaseModel
from uuid import UUID

class PromptSchema(BaseModel):
    prompt: str
    conversation_id: UUID = None

class AIResponseSchema(BaseModel):
    response: str
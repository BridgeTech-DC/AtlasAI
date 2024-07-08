from pydantic import BaseModel

class PromptSchema(BaseModel):
    prompt: str
    conversation_id: int = None

class AIResponseSchema(BaseModel):
    response: str
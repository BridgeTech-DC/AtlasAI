#app\api\persona\schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List

class PersonaBaseSchema(BaseModel):
    """Base schema for AI Persona, excluding the id."""
    name: str
    gender: str
    country: str
    role: str
    characteristic: str
    expertise: str

class PersonaSchema(PersonaBaseSchema):
    """Schema for AI Persona, including the id."""
    id: int = Field(...)  

    class Config:
        orm_mode = True  # Allow creation from SQLAlchemy models

class UserPersonaSchema(BaseModel):
    """Schema for a user, including their selected persona."""
    id: str  
    selected_persona: Optional[PersonaSchema] = None

    class Config:
        orm_mode = True
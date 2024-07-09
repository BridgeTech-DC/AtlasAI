#app\api\persona\routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database import get_async_session
from app.models import User
from app.api.persona.models import Persona
from app.api.auth.manager import get_current_user 
from app.api.persona.schemas import PersonaSchema, UserPersonaSchema # Import schemas

router = APIRouter(tags=["AI Personas"])

@router.get("/personas/", response_model=List[PersonaSchema])
async def list_personas(db: AsyncSession = Depends(get_async_session), user: User = Depends(get_current_user),):
    """Lists all available AI personas."""
    result = await db.execute(select(Persona))
    personas = result.scalars().all()
    return personas

@router.post("/personas/select/{persona_id}", response_model=UserPersonaSchema)
async def select_persona(
    persona_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user),
):
    print("Persona ID",persona_id)
    """Allows a user to select an AI persona."""
    persona = await db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found")

    # Associate persona with user 
    user.selected_persona_id = persona.id  
    await db.commit()

    return {"id": str(persona.id), "selected_persona": persona}  # Return the updated user object (including the selected persona) 
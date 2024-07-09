from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.api.ai.schemas import PromptSchema, AIResponseSchema
from app.api.ai.openai_utils import get_ai_response
from app.api.auth.manager import get_current_user
from app.models import User

router = APIRouter(tags=["AI Interaction"])

@router.post("/ai/respond", response_model=AIResponseSchema)
async def get_response(
    prompt: PromptSchema,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user),
):
    if not user.selected_persona_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select a persona first."
        )
    ai_response = await get_ai_response(prompt.prompt, user, db, prompt.conversation_id)
    return {"response": ai_response}

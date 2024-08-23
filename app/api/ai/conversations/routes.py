from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from typing import List
from app.database import get_async_session
from app.models import User
from .models import Conversation, Message
from app.api.auth.manager import get_current_user
from app.api.ai.conversations.schemas import (
    ConversationHistorySchema,
    MessageCreate,
    MessageResponse
)
from uuid import UUID
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["AI Conversation History"])

@router.get("/ai/conversations/", response_model=List[ConversationHistorySchema])
async def get_conversation_history(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(get_current_user),
    skip: int = Query(0, alias="skip"),
    limit: int = Query(10, alias="limit")
):
    statements = select(Conversation).where(Conversation.user_id == user.id).options(
        joinedload(Conversation.persona),
        joinedload(Conversation.messages)
    ).offset(skip).limit(limit)
    result = await db.execute(statements)
    conversations = result.unique().scalars().all()
    for conversation in conversations:
        await db.refresh(conversation, attribute_names=["persona", "messages"])
    return conversations

@router.post("/ai/conversations/", response_model=ConversationHistorySchema)
async def create_conversation_endpoint(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if not user.selected_persona_id:
        user.selected_persona_id = 1  # or any default value logic
    conversation = Conversation(
        user_id=user.id,
        persona_id=user.selected_persona_id
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    # Eagerly load related objects
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.persona), selectinload(Conversation.messages))
        .filter(Conversation.id == conversation.id)
    )
    conversation = result.scalars().first()
    return conversation  # Return the conversation object

@router.post("/ai/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def add_message_to_conversation_endpoint(
    conversation_id: UUID,
    message_data: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    message = Message(
        conversation_id=conversation_id,
        role=message_data.role,
        content=message_data.content
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message

@router.get("/ai/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages_for_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Use joinedload to include persona details in the message response
    # Add order_by to sort by message ID in ascending order
    messages = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(joinedload(Message.conversation).joinedload(Conversation.persona))
        .order_by(Message.id.asc())  # Sort by message ID ascending
    )
    return messages.scalars().all()

# Serve the main HTML page for any URL that matches /conversation/{conversation_id}
@router.get("/conversation/{conversation_id}", response_class=HTMLResponse)
async def get_conversation_page(request: Request, conversation_id: str):
    return templates.TemplateResponse("main.html", {"request": request})

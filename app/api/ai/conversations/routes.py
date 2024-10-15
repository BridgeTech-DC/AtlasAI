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
from app.config import settings
import openai
from datetime import datetime,timezone

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(tags=["AI Conversation History"])

# Set your OpenAI API key
openai.api_key = settings.OPENAI_API_KEY

@router.post('/ai/conversations/{conversation_id}/generate-title')
async def generate_title_from_message(message_content: str, conversation_id: UUID, db: AsyncSession = Depends(get_async_session)) -> str:
    # Use OpenAI's GPT-4 to generate a title
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Generate a concise and relevant title for the following message within 5-6 words."},
            {"role": "user", "content": message_content}
        ],
        max_tokens=10
    )
    # Extract the generated title from the response
    title = response.choices[0].message.content.strip()
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation.title = title
    await db.commit()
    return title

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
    ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statements)
    conversations = result.unique().scalars().all()
    for conversation in conversations:
        await db.refresh(conversation, attribute_names=["persona", "messages"])
    return conversations

@router.post("/ai/conversations/", response_model=ConversationHistorySchema)
async def create_conversation_endpoint(
    title: str = "New Conversation",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if not user.selected_persona_id:
        user.selected_persona_id = 1  # or any default value logic
    conversation = Conversation(
        user_id=user.id,
        persona_id=user.selected_persona_id,
        title = title
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
    return conversation

@router.post("/ai/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def add_message_to_conversation_endpoint(
    conversation_id: UUID,
    message_data: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    # Add the new message to the conversation
    message = Message(
        conversation_id=conversation_id,
        role=message_data.role,
        content=message_data.content
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Fetch the conversation to update
    conversation = await db.get(Conversation, conversation_id)
    print("Conversation is present", conversation)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        print("Current date and time is: ",datetime.now())
        conversation.updated_at = datetime.now()

    # Check if this is the first message in the conversation
    existing_messages = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    is_first_message = existing_messages.scalars().first() is None

    if is_first_message:
        # Generate a title from the first message
        title = await generate_title_from_message(message_data.content)
        print("Title is....",title)
        conversation.title = title

    # Commit the updates to the conversation
    await db.commit()
    await db.refresh(conversation)

    return message


@router.get("/ai/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages_for_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    messages = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(joinedload(Message.conversation).joinedload(Conversation.persona))
        .order_by(Message.id.asc())
    )
    return messages.scalars().all()

@router.get("/conversation/{conversation_id}", response_class=HTMLResponse)
async def get_conversation_page(request: Request, conversation_id: str):
    return templates.TemplateResponse("main.html", {"request": request})

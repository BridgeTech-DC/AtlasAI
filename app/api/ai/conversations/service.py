# app/api/ai/conversation/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.ai.conversations.models import Conversation, Message
from uuid import UUID

async def create_conversation(db: AsyncSession, user_id: UUID, persona_id: int):
    """Creates a new conversation in the database."""
    conversation = Conversation(user_id=user_id, persona_id=persona_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

async def add_message_to_conversation(db: AsyncSession, conversation_id: UUID, role: str, content: str):
    """Adds a new message to an existing conversation."""
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    await db.commit()
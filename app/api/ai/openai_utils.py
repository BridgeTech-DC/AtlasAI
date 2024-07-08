import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
from app.models import User
from app.api.persona.models import Persona
from .conversations.models import Message, Conversation
from app.config import settings
from fastapi import HTTPException
from sqlalchemy.future import select
from app.api.persona.utils import get_persona_system_message
# Load environment variables from .env file
load_dotenv() 

# Get OpenAI API key from environment variables
openai.api_key = settings.OPENAI_API_KEY
print("OPEN AI KEY",openai.api_key)
if not openai.api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

# Create an OpenAI client instance
client = OpenAI(api_key=openai.api_key)

async def get_ai_response(prompt: str, user: User, db, conversation_id: int = None):
    try:
        conversation_history = []

        # Only append persona system message if there's no existing context
        if not conversation_history and user.selected_persona_id:
            persona = await db.get(Persona, user.selected_persona_id)
            if persona:
                system_message = get_persona_system_message(persona)
                conversation_history.append({"role": "system", "content": system_message})

        conversation_history.append({"role": "user", "content": prompt})
        if conversation_id is None:
            conversation = Conversation(user_id=user.id, persona_id=user.selected_persona_id)
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            conversation_id = conversation.id
        else:
            conversation = await db.get(Conversation, conversation_id)
            try:
                conversation_stmt = select(Message).where(
                    Message.conversation_id == conversation_id
                ).order_by(Message.created_at)
                result = await db.execute(conversation_stmt)
                messages = result.scalars().all()
                if messages:
                    context = "\n".join([f"{message.role}: {message.content}" for message in messages])
                    context_message = f"Here is the context of the previous conversation for your reference, please keep this conversation in mind for further interactions: {context}"
                    conversation_history.append({"role": "system", "content": context_message})
            except Exception as e:
                print(e)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")

        user_message = Message(conversation_id=conversation_id, role="user", content=prompt)
        db.add(user_message)
        await db.commit()
        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=conversation_history,
            max_tokens=400,
            temperature=0.8
        )
        ai_response = response.choices[0].message.content.strip()
        ai_message = Message(conversation_id=conversation_id, role="assistant", content=ai_response)
        db.add(ai_message)
        await db.commit()
        return ai_response
    except Exception as e:
        return f"An error occurred: {e}"

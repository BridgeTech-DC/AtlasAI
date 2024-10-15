from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .schemas import EventDetails, EventResponse, ScheduledEventSchema
from .services import get_calendar_service, create_event, list_events, delete_event
from app.database import get_async_session
from app.api.auth.manager import get_current_user
from app.models import User
from .models import ScheduledEvent
from typing import List
from app.api.ai.openai_utils import client
from app.api.persona.utils import get_persona_system_message
from app.api.persona.models import Persona

router = APIRouter(tags=["Google Calendar"])

@router.post("/calendar/create_event", response_model=EventResponse)
async def create_event_endpoint(event_details: EventDetails, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    service = await get_calendar_service(user, db)
    event = await create_event(service, event_details, user, db)
    return {"message": "Event created successfully", "event_id": event['id'], "hangoutLink": event.get('hangoutLink')}

@router.get("/calendar/list_events", response_model=List[ScheduledEventSchema])
async def list_events_endpoint(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    events = await db.execute(select(ScheduledEvent).where(ScheduledEvent.user_id == user.id))
    return events.scalars().all()

@router.delete("/calendar/delete_event/{event_id}")
async def delete_event_endpoint(event_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    service = await get_calendar_service(user, db)
    await delete_event(service, event_id, user, db)
    return {"message": "Event deleted successfully"}

# New function to draft event details using OpenAI's GPT model
async def draft_event_details(user_prompt: str, user: User, db: AsyncSession):
    persona = await db.get(Persona, user.selected_persona_id)
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found.")
    
    system_message = get_persona_system_message(persona)
    prompt = f"""
    You are helping a user schedule a meeting.
    Please generate the meeting details including summary, description, and attendees based on the user prompt.
    """
    conversation = [{"role": "system", "content": system_message + "\n" + prompt}, {"role": "user", "content": user_prompt}]
    response = client.chat.completions.create(model="gpt-4-turbo-2024-04-09", messages=conversation, max_tokens=500, temperature=0)
    event_details = response.choices[0].message.content.strip()
    
    # Extract attendee names from the user prompt
    attendee_names = extract_attendee_names(user_prompt)
    attendees_response = await search_contacts(attendee_names, user, db)
    attendees = [attendee["email"] for attendee in attendees_response["suggested_recipients"]]
    
    return {
        "summary": event_details.get("summary"),
        "description": event_details.get("description"),
        "attendees": attendees
    }

def extract_attendee_names(user_prompt: str) -> List[str]:
    # Implement a function to extract attendee names from the user prompt
    # This is a placeholder implementation
    return ["John Doe", "Jane Smith"]

# New endpoint to schedule an event based on user prompt
@router.post("/calendar/schedule_event")
async def schedule_event_endpoint(user_prompt: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    event_details_dict = await draft_event_details(user_prompt, user, db)
    event_details = EventDetails.parse_obj(event_details_dict)
    return await create_event_endpoint(event_details, user, db)

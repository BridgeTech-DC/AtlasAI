from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql.expression import delete
from fastapi import HTTPException, status
from app.models import GoogleCredentials, User
from .models import ScheduledEvent, EventAttendee
from app.config import settings

SCOPES = settings.SCOPES.split(",")

async def get_calendar_service(user: User, db: AsyncSession):
    credentials = await db.execute(select(GoogleCredentials).where(GoogleCredentials.user_id == user.id))
    credentials = credentials.scalar_one_or_none()
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google credentials not found for user.")
    creds_info = {
        "token": credentials.access_token,
        "refresh_token": credentials.refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "scopes": SCOPES
    }
    creds = Credentials.from_authorized_user_info(creds_info)
    service = build('calendar', 'v3', credentials=creds)
    return service

async def create_event(service, event_details, user: User, db: AsyncSession):
    event = {
        'summary': event_details.summary,
        'location': event_details.location,
        'description': event_details.description,
        'start': {
            'dateTime': event_details.start.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': event_details.end.isoformat(),
            'timeZone': 'UTC',
        },
        'attendees': [{'email': email} for email in event_details.attendees],
        'conferenceData': {
            'createRequest': {
                'requestId': 'sample123',
                'conferenceSolutionKey': {
                    'type': 'hangoutsMeet'
                }
            }
        } if event_details.create_meet_link else None
    }
    event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1, sendUpdates='all').execute()
    # Store event details in the database
    scheduled_event = ScheduledEvent(
        user_id=user.id,
        event_id=event['id'],
        summary=event_details.summary,
        location=event_details.location,
        description=event_details.description,
        start=event_details.start.replace(tzinfo=None),
        end=event_details.end.replace(tzinfo=None),      
        hangout_link=event.get('hangoutLink')
    )
    db.add(scheduled_event)
    await db.commit()
    # Store attendees in the database
    for email in event_details.attendees:
        attendee = EventAttendee(
            event_id=scheduled_event.id,
            email=email
        )
        db.add(attendee)
    await db.commit()
    return event

async def list_events(service):
    events_result = service.events().list(calendarId='primary', maxResults=10, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    return events

async def delete_event(service, event_id, user: User, db: AsyncSession):
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    # Remove event details from the database
    await db.execute(delete(ScheduledEvent).where(ScheduledEvent.event_id == event_id))
    await db.commit()

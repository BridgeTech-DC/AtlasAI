import re
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models import User
from app.api.auth.manager import get_current_user
from .schemas import DraftEmailRequest, SendEmailRequest, ContactSearchResponse, SentEmailResponse
from .models import SentEmail
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List, Dict, Tuple
from .services import draft_email, send_email
import spacy
from uuid import UUID
import redis.asyncio as redis
import json
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import asyncio
from app.config import settings
from app.models import GoogleCredentials

router = APIRouter(tags=["Google Gmail"])

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

# Initialize Redis client
redis_client = redis.from_url("redis://localhost")
SCOPES = settings.SCOPES.split(",")

async def cache_contacts(user_id: int, contacts: List[Dict[str, str]]):
    await redis_client.set(f"user:{user_id}:contacts", json.dumps(contacts))

async def get_cached_contacts(user_id: int) -> List[Dict[str, str]]:
    cached = await redis_client.get(f"user:{user_id}:contacts")
    return json.loads(cached) if cached else []

def parse_email_header(header_value: str) -> Tuple[str, str]:
    match = re.match(r'(.*?)(<.*?>)', header_value)
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip('<>')
        return name, email
    return header_value, header_value

def is_valid_email(email: str) -> bool:
    # Simple regex to check if the email is valid
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

async def fetch_messages_in_batch(service, message_ids, suggested_recipients):
    try:
        batch = service.new_batch_http_request()

        def callback(request_id, response, exception):
            if exception is not None:
                print(f"Error fetching message {request_id}: {exception}")
            else:
                headers = response['payload']['headers']
                for header in headers:
                    if header['name'] == 'From':
                        name, email = parse_email_header(header['value'])
                        if is_valid_email(email):
                            suggested_recipients.add((name, email))
                    elif header['name'] == 'To':
                        for recipient in header['value'].split(', '):
                            name, email = parse_email_header(recipient)
                            if is_valid_email(email):
                                suggested_recipients.add((name, email))

        for message_id in message_ids:
            batch.add(service.users().messages().get(userId='me', id=message_id), callback=callback)

        while True:
            try:
                batch.execute()
                break
            except HttpError as error:
                if error.resp.status == 429:
                    print("Rate limit exceeded, retrying...")
                    await asyncio.sleep(2)  # Simple backoff strategy
                else:
                    raise
    except HttpError as error:
        print(f'An error occurred during batch request: {error}')

async def fetch_all_contacts_from_mailbox(service) -> List[Dict[str, str]]:
    suggested_recipients = set()
    next_page_token = None
    try:
        while True:
            response = service.users().messages().list(
                userId='me', maxResults=80, pageToken=next_page_token
            ).execute()
            messages = response.get('messages', [])
            message_ids = [message['id'] for message in messages]
            for i in range(0, len(message_ids), 100):
                chunk = message_ids[i:i + 100]
                await fetch_messages_in_batch(service, chunk, suggested_recipients)
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        return [{"name": name, "email": email} for name, email in suggested_recipients]
    except HttpError as error:
        print(f'An error occurred while fetching messages: {error}')
        return []

@router.post("/caching/search_contacts", response_model=ContactSearchResponse)
async def caching_search_contacts_route(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Route for fetching and caching all contacts."""
    service = await get_gmail_service(user=user, db=db)
    contacts = await fetch_all_contacts_from_mailbox(service)
    await cache_contacts(user.id, contacts)
    return {"message": "Contacts cached successfully", "suggested_recipients": contacts}

@router.get("/caching/auto_complete", response_model=List[Dict[str, str]])
async def auto_complete_suggestions(
    query: str,
    user: User = Depends(get_current_user)
):
    """Route for fetching auto-complete suggestions."""
    cached_contacts = await get_cached_contacts(user.id)
    suggestions = [contact for contact in cached_contacts if query.lower() in contact["name"].lower() or query.lower() in contact["email"].lower()]
    return suggestions

@router.post("/gmail/draft", response_model=dict)
async def draft_email_route(
    draft_request: DraftEmailRequest,
    conversation_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Route for drafting an email."""
    recipient_names = extract_names(draft_request.user_prompt)
    if not recipient_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient name not found in prompt.")
    draft_response = await draft_email(draft_request.user_prompt, user, db, conversation_id)
    return {
        "draft": draft_response,
        "recipient_names": recipient_names
    }

@router.post("/gmail/send")
async def send_email_route(
    send_request: SendEmailRequest,
    email_draft_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    conversation_id: UUID = Query(None),
    request: Request = None
):
    """Route for sending an email."""
    try:
        print(f"Request body: {await request.json()}")
        print(f"User: {user}")
        print(f"DB session: {db}")
        if db is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database session is None")
        return await send_email(
            send_request.to,
            send_request.subject,
            send_request.message_body,
            email_draft_id,
            user,
            db,
            conversation_id
        )
    except Exception as e:
        print(f"Exception occurred: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error sending email: {e}")

@router.get("/ai/conversations/{conversation_id}/sent-emails", response_model=List[SentEmailResponse])
async def get_sent_emails_for_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    sent_emails = await db.execute(
        select(SentEmail)
        .where(SentEmail.conversation_id == conversation_id)
        .options(joinedload(SentEmail.email_draft))
        .order_by(SentEmail.sent_at.asc())
    )
    return sent_emails.scalars().all()

async def get_gmail_service(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    """Gets the Gmail API service for the authenticated user."""
    credentials = await db.execute(select(GoogleCredentials).where(
        GoogleCredentials.user_id == user.id
    ))
    credentials = credentials.scalar_one_or_none()
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google credentials not found for user."
        )
    creds_info = {
        "token": credentials.access_token,
        "refresh_token": credentials.refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "scopes": SCOPES
    }
    creds = Credentials.from_authorized_user_info(creds_info)
    return build('gmail', 'v1', credentials=creds)

def extract_names(prompt):
    doc = nlp(prompt)
    proper_nouns = [token.text for token in doc if token.pos_ == "PROPN"]
    return proper_nouns

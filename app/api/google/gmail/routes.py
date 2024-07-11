from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models import User
from app.api.auth.manager import get_current_user
from .schemas import DraftEmailRequest, SendEmailRequest, ContactSearchResponse, ContactSearchRequest
from .services import draft_email, send_email, search_contacts
import spacy
from uuid import UUID

router = APIRouter(tags=["Google Gmail"])

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_names(prompt):
    doc = nlp(prompt)
    names = [ent.text for ent in doc.ents if ent.label_ in {"PERSON", "ORG"}]
    return names

@router.post("/gmail/search_contacts", response_model=ContactSearchResponse)
async def search_contacts_route(
    contact_search_request: ContactSearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Route for searching contacts."""
    return await search_contacts(contact_search_request.recipient_name, user, db)

@router.post("/gmail/draft", response_model=dict)
async def draft_email_route(
    draft_request: DraftEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    conversation_id: UUID = None
):
    """Route for drafting an email."""
    # Extract recipient names from user prompt using spaCy NER
    recipient_names = extract_names(draft_request.user_prompt)

    if not recipient_names:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient name not found in prompt.")

    # Draft the email
    draft_response = await draft_email(draft_request.user_prompt, user, db, conversation_id)

    return {
        "draft": draft_response,
        "recipient_names": recipient_names  # Include recipient names in the response
    }

@router.post("/gmail/send")
async def send_email_route(
    send_request: SendEmailRequest,
    email_draft_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
    conversation_id: UUID = None
):
    """Route for sending an email."""
    return await send_email(
        send_request.to,
        send_request.subject,
        send_request.message_body,
        email_draft_id,
        user,
        db,
        conversation_id
    )


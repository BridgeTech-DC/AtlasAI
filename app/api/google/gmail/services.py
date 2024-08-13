import base64
import json
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request as GoogleRequest
from app.models import GoogleCredentials
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status, Depends, Request
from app.api.auth.manager import get_current_user
from app.api.auth.routes import refresh_google_token
from app.models import User
from .models import SentEmail, EmailDraft
from app.api.ai.openai_utils import client
from app.database import get_async_session
from app.config import settings
from app.api.persona.utils import get_persona_system_message
from app.api.persona.models import Persona
from app.api.ai.conversations.models import Conversation
from uuid import UUID
import re
from functools import lru_cache, wraps
import time
import datetime

# If modifying these scopes, delete the file token.pickle.
SCOPES = settings.SCOPES.split(",")

# Cache settings
CACHE_TIMEOUT = 10800  # Cache for 3 hours (10800 seconds)
cache_data = {
    "expiration": 0,
    "senders": [],
    "recipients": []
}

def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper_cache(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + func.lifetime
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if time.time() >= func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)
        return wrapped_func
    return wrapper_cache

async def get_gmail_service(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), token: str = Depends(refresh_google_token)):
    """Gets the Gmail API service for the authenticated user."""
    try:
        print("Starting get_gmail_service function")
        # if db is None:
        #     print("Database session is None")
        #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database session is None")
        
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
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        from traceback import print_exc; print_exc()
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting Gmail service: {e}")

def parse_email_header(header_value: str):
    """Parses an email header value and extracts the name and email address using regex."""
    match = re.match(r'(.*?)(<.*?>)', header_value)
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip('<>')
        return name, email
    return header_value, header_value

@timed_lru_cache(seconds=CACHE_TIMEOUT)
async def get_all_recipients_and_senders(service, user_email):
    """Retrieves a list of all unique recipients and senders from the user's Gmail inbox."""
    recipients = set()
    senders = set()
    # Get a list of all messages in the inbox (consider pagination if needed)
    results = service.users().messages().list(userId='me', maxResults=500, q='in:inbox').execute()
    messages = results.get('messages', [])
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        headers = msg['payload']['headers']
        for header in headers:
            if (header['name'] == 'From'):
                name, email = parse_email_header(header['value'])
                senders.add((name, email))
            elif (header['name'] == 'To'):
                for recipient in header['value'].split(', '):
                    name, email = parse_email_header(recipient)
                    recipients.add((name, email))
    return list(senders), list(recipients)

async def search_contacts(recipient_names: list, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    """Searches the user's Gmail mailbox for matching names and returns email addresses."""
    try:
        service = await get_gmail_service(user=user, db=db)
        print("Gmail service obtained successfully")
        
        # Check if the cache contains the list or fetch if cache is stale
        current_time = time.time()
        if current_time >= cache_data["expiration"]:
            all_senders, all_recipients = await get_all_recipients_and_senders(service, user.email)
            cache_data["senders"] = all_senders
            cache_data["recipients"] = all_recipients
            cache_data["expiration"] = current_time + CACHE_TIMEOUT
        else:
            all_senders = cache_data["senders"]
            all_recipients = cache_data["recipients"]
        
        suggested_recipients = set()  # Use a set to store unique contacts
        for recipient_name in recipient_names:
            recipient_name_lower = recipient_name.lower()
            for name, email in all_senders + all_recipients:
                name_lower = name.lower()
                email_lower = email.lower()
                # Check for matches in name or email (case-insensitive)
                if (
                    recipient_name_lower == name_lower or
                    recipient_name_lower in name_lower or
                    recipient_name_lower == email_lower or
                    recipient_name_lower in email_lower
                ):
                    suggested_recipients.add((name, email))  # Add tuple to set
        # Convert set of tuples back to list of dictionaries
        suggested_recipients_list = [{"name": name, "email": email} for name, email in suggested_recipients]
        return {"suggested_recipients": suggested_recipients_list}
    except HttpError as error:
        print(f'An error occurred: {error}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error searching Gmail: {error}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error searching contacts: {e}")

async def draft_email(user_prompt: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), conversation_id: UUID = None):
    """Drafts an email using ChatGPT, including subject and body, based on user prompt."""
    try:
        # Fetch the persona details
        persona = await db.get(Persona, user.selected_persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found.")
        # Define clear instructions for ChatGPT
        system_message = get_persona_system_message(persona)
        current_date = datetime.datetime.today().strftime('%d/%m/%Y')
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        prompt = f"""
        You purpose is to helping a user draft an email.
        Please generate a professional and concise email, including the subject and body based on the user given prompt.
        Also you would be using {user.google_username} as the name and {user.email} as the email for signing off your emails.
        Also please don't add any sort of placeholders or dummy text in the email.
        You will have to write your emails assuming your drafted email is the ultimate final one and no changes or edits will be made to it.
        Also remember today's date is {current_date}, in case you wanna mention any date or time related stuff in your email.
        """
        mail_conversation = []
        mail_conversation.append({"role": "system", "content": system_message+"\n"+prompt})
        mail_conversation.append({"role": "user", "content": user_prompt})
        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=mail_conversation,
            max_tokens=500,
            temperature=0
        )
        email_content = response.choices[0].message.content.strip()
        subject, *body_lines = email_content.split("\n")
        body = "\n".join(body_lines)
        # Create or fetch the conversation
        if conversation_id is None:
            conversation = Conversation(user_id=user.id, persona_id=user.selected_persona_id)
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            conversation_id = conversation.id
        else:
            conversation = await db.get(Conversation, conversation_id)
            if not conversation:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        # Create and save the email draft
        email_draft = EmailDraft(
            conversation_id=conversation_id,
            recipient_name="",
            user_prompt=user_prompt,
            subject=subject.replace("Subject: ", ""),
            body=body
        )
        db.add(email_draft)
        await db.commit()
        await db.refresh(email_draft)
        return {
            "message": "Email drafted.",
            "drafted_subject": email_draft.subject,
            "drafted_body": email_draft.body,
            "conversation_id": conversation_id,
            "email_draft_id": email_draft.id
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error drafting email: {e}")

async def send_email(to: str, subject: str, message_body: str, email_draft_id: int, request: Request, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), conversation_id: UUID = None):
    """Sends an email using the Gmail API."""
    try:
        print("Starting send_email function")
        service = await get_gmail_service(user=user, db=db)
        print("Gmail service obtained successfully")
        
        # Ensure we are accessing the email attribute from the user object
        if not hasattr(user, 'email'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User object does not have an email attribute")
        
        message = MIMEText(message_body, 'html')
        message['to'] = to
        message['from'] = user.email
        message['subject'] = subject

        # Encode the message as a base64url string
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send the email
        send_message = (service.users().messages().send(userId='me', body={'raw': raw_message}).execute())
        print(f'Message Id: {send_message["id"]}')

        # Fetch the email draft to get the conversation ID
        email_draft = await db.get(EmailDraft, email_draft_id)
        if not email_draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email draft not found")

        # Get conversation_id from request body (if not provided as path parameter)
        request_body = await request.json()
        conversation_id = request_body.get("conversation_id")

        # Create and save SentEmail object
        sent_email = SentEmail(
            email_draft_id=email_draft_id,
            recipient_email=to,
            conversation_id=conversation_id
        )
        db.add(sent_email)
        await db.commit()
        return {"message": "Email sent successfully!"}

    except Exception as e:
        print(f"Exception occurred: {e}")
        from traceback import print_exc; print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error sending email: {e}")

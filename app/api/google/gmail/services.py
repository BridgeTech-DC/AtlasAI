import asyncio
import base64
import re
from datetime import datetime
from email.mime.text import MIMEText
from typing import List, Dict, Tuple
from uuid import UUID
import time
from fastapi import FastAPI, HTTPException, status, Depends
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import GoogleCredentials
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
from googleapiclient.http import BatchHttpRequest

SCOPES = settings.SCOPES.split(",")

app = FastAPI()

async def get_gmail_service(user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_async_session),
                            token: str = Depends(refresh_google_token)):
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

def parse_email_header(header_value: str) -> Tuple[str, str]:
    """Parses an email header value and extracts the name and email address."""
    match = re.match(r'(.*?)(<.*?>)', header_value)
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip('<>')
        return name, email
    return header_value, header_value

async def fetch_messages_in_batch(service, message_ids, recipient_name_lower, suggested_recipients):
    """Fetches multiple messages in a single batch request."""
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
                        if recipient_name_lower in name.lower() or recipient_name_lower in email.lower():
                            suggested_recipients.add((name, email))
                    elif header['name'] == 'To':
                        for recipient in header['value'].split(', '):
                            name, email = parse_email_header(recipient)
                            if recipient_name_lower in name.lower() or recipient_name_lower in email.lower():
                                suggested_recipients.add((name, email))

        for message_id in message_ids:
            batch.add(service.users().messages().get(userId='me', id=message_id), callback=callback)

        batch.execute()  # Execute the batch request synchronously

    except HttpError as error:
        print(f'An error occurred during batch request: {error}')

async def fetch_and_process_messages(service, query: str, recipient_name_lower: str) -> Tuple[set, int]:
    """Fetches messages and processes them asynchronously using batch requests."""
    suggested_recipients = set()
    total_messages = 0
    next_page_token = None

    try:
        while True:
            response = service.users().messages().list(
                userId='me', q=query, maxResults=500, pageToken=next_page_token
            ).execute()

            messages = response.get('messages', [])
            total_messages += len(messages)

            message_ids = [message['id'] for message in messages]

            # Batch requests in chunks of 100
            for i in range(0, len(message_ids), 100):
                chunk = message_ids[i:i + 100]
                await fetch_messages_in_batch(service, chunk, recipient_name_lower, suggested_recipients)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        return suggested_recipients, total_messages
    except HttpError as error:
        print(f'An error occurred while fetching messages: {error}')
        return suggested_recipients, total_messages

@app.get("/search_contacts")
async def search_contacts(recipient_names: List[str],
                          user: User = Depends(get_current_user),
                          db: AsyncSession = Depends(get_async_session)
                          ) -> Dict[str, List[Dict[str, str]]]:
    """Searches the user's Gmail mailbox for contacts."""
    service = await get_gmail_service(user=user, db=db)
    all_suggested_recipients = set()
    total_messages_async = 0

    # --- Asynchronous Approach ---
    start_time_async = time.time()
    tasks = [fetch_and_process_messages(service, f'to:{name} OR from:{name}', name.lower()) for name in recipient_names]
    results = await asyncio.gather(*tasks)
    for suggested, total in results:
        all_suggested_recipients.update(suggested)
        total_messages_async += total
    end_time_async = time.time()

    print(f"Time taken with asyncio: {end_time_async - start_time_async} seconds")
    print(f"Total unique contacts fetched with asyncio: {len(all_suggested_recipients)}")
    print(f"Total messages iterated with asyncio: {total_messages_async}")

    suggested_recipients_list = [{"name": name, "email": email} for name, email in all_suggested_recipients]
    return {"suggested_recipients": suggested_recipients_list}

async def draft_email(user_prompt: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), conversation_id: UUID = None):
    """Drafts an email using ChatGPT, including subject and body, based on user prompt."""
    try:
        persona = await db.get(Persona, user.selected_persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found.")
        system_message = get_persona_system_message(persona)
        current_date = datetime.today().strftime('%d/%m/%Y')
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

async def send_email(to: str, subject: str, message_body: str, email_draft_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), conversation_id: UUID = None):
    """Sends an email using the Gmail API."""
    try:
        service = await get_gmail_service(user=user, db=db)
        message = MIMEText(message_body, 'html')
        message['to'] = to
        message['from'] = user.email
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = (service.users().messages().send(userId='me', body={'raw': raw_message}).execute())
        email_draft = await db.get(EmailDraft, email_draft_id)
        if not email_draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email draft not found")
        sent_email = SentEmail(
            email_draft_id=email_draft_id,
            recipient_email=to,
            conversation_id=conversation_id
        )
        db.add(sent_email)
        await db.commit()
        return {"message": "Email sent successfully!"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error sending email: {e}")
    
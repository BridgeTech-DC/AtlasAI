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
from fastapi import HTTPException, status, Depends
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

# If modifying these scopes, delete the file token.pickle.
SCOPES = settings.SCOPES.split(",")

async def get_gmail_service(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), token: str = Depends(refresh_google_token)):
    """Gets the Gmail API service for the authenticated user."""
    try:
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

async def draft_email(user_prompt: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), conversation_id: UUID = None):
    """Drafts an email using ChatGPT, including subject and body, based on user prompt."""
    try:
        # Fetch the persona details
        persona = await db.get(Persona, user.selected_persona_id)
        if not persona:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found.")

        # Define clear instructions for ChatGPT
        system_message = get_persona_system_message(persona)
        prompt = f"""
        You purpose is to helping a user draft an email.
        Please generate a professional and concise email, including the subject and body based on the user given prompt.
        """

        mail_conversation = []
        mail_conversation.append({"role": "system", "content": system_message+"\n"+prompt})
        mail_conversation.append({"role": "user", "content": user_prompt})

        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=mail_conversation,
            max_tokens=250,
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


async def search_contacts(recipient_name: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    """Searches the user's Gmail mailbox for matching names and returns email addresses."""
    try:
        service = await get_gmail_service(user=user, db=db)

        # Search for messages containing the recipient name
        query = f"from:{recipient_name} OR to:{recipient_name}"
        print("Service details", service)
        results = service.users().messages().list(userId='me', q=query).execute()

        messages = results.get('messages', [])
        suggested_recipients = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            for header in headers:
                if header['name'] == 'From':
                    from_name, from_email = parse_email_header(header['value'])
                    if recipient_name.lower() in from_name.lower():
                        suggested_recipients.append({"name": from_name, "email": from_email})
                elif header['name'] == 'To':
                    to_addresses = header['value'].split(',')
                    for to_address in to_addresses:
                        to_name, to_email = parse_email_header(to_address)
                        if recipient_name.lower() in to_name.lower():
                            suggested_recipients.append({"name": to_name, "email": to_email})

        # Remove duplicates based on email address
        seen_emails = set()
        unique_recipients = []
        for recipient in suggested_recipients:
            if recipient["email"] not in seen_emails:
                unique_recipients.append(recipient)
                seen_emails.add(recipient["email"])

        return {"suggested_recipients": unique_recipients}
    except HttpError as error:
        print(f'An error occurred: {error}')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error searching Gmail: {error}")
    except Exception as e:
        from traceback import print_exc; print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error searching contacts: {e}")

def parse_email_header(header_value: str):
    """Parses an email header value and extracts the name and email address."""
    name = ""
    email = ""
    if '<' in header_value and '>' in header_value:
        name, email = header_value.split('<')
        email = email.replace('>', '').strip()
        name = name.strip()
    else:
        email = header_value.strip()
    return name, email

async def send_email(to: str, subject: str, message_body: str, email_draft_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session), conversation_id: UUID = None):
    """Sends an email using the Gmail API."""
    try:
        service = await get_gmail_service(user=user, db=db)

        message = MIMEText(message_body)
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error sending email: {e}")

import asyncio
import speech_recognition as sr
import pyttsx3
import requests
import pygame
from gtts import gTTS, lang
from io import BytesIO
from fastapi import HTTPException, status, Depends, WebSocket
import json

# --- OpenAI Setup (You might need to adjust the path) ---
from app.api.ai.openai_utils import get_ai_response, client
from app.models import User
from app.api.persona.models import Persona
from app.database import get_async_session, AsyncSession
from app.api.auth.manager import get_current_user  # Import for authentication
from app.api.ai.conversations.models import Conversation, Message

# --- Get Supported Languages from gTTS ---
languages = lang.tts_langs()  # Get a dictionary of language names and codes

# --- TLD Mapping ---
tld_mapping = {
    "Australia": "com.au",
    "United Kingdom": "co.uk",
    "United States": "us",
    "Canada": "ca",
    "India": "co.in",
    "Ireland": "ie",
    "South Africa": "co.za",
    "Nigeria": "com.ng",
    "France": "fr",
    "China Mainland": "com",  # Defaulting to 'com' for now
    "Taiwan": "com",          # Defaulting to 'com' for now
    "Brazil": "com.br",
    "Portugal": "pt",
    "Mexico": "com.mx",
    "Spain": "es"
}

# --- Helper Functions for Voice Customization ---

def get_language_code(language_name):
    """Returns the language code based on the language name from the Persona model."""
    for code, name in languages.items():
        if name == language_name:
            return code
    return "en"  # Default to English if no match found

def get_tld(country):
    """Returns the top-level domain (tld) for accent based on the country."""
    return tld_mapping.get(country, "com")  # Default to 'com' if no match found

async def handle_voice_interaction(websocket: WebSocket, user: User, db: AsyncSession = Depends(get_async_session)):
    """Handles voice interaction over a WebSocket connection."""

    recognizer = sr.Recognizer()
    engine = pyttsx3.init()
    pygame.mixer.init()

    print(user)
    if not user:
        print("User not authenticated. Closing WebSocket connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return

    async for message in websocket.iter_text():
        try:
            message_data = json.loads(message)
            persona_id = int(message_data['persona_id'])
            token = message_data['token']

            # Get the selected persona from the database
            persona = db.query(Persona).filter_by(id=persona_id).first()

            if not persona:
                print(f"Persona with ID {persona_id} not found.")
                await websocket.send_text(json.dumps({"error": "Persona not found."}))
                continue  # Skip to the next message

            # Record audio using pygame
            print("Listening...")
            tts = gTTS(text="Listening", lang='en')  # You can customize the "listening" voice
            fp = BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            pygame.mixer.music.load(fp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            with sr.Microphone() as source:
                audio = recognizer.listen(source)

                try:
                    text = recognizer.recognize_google(audio)
                    print(f"User said: {text}")

                    # Send text to FastAPI
                    response = requests.post(
                        "http://localhost:8000/api/v1/ai/respond",  # Replace with your FastAPI URL
                        json={"prompt": text},
                        headers={"Authorization": f"Bearer {token}"} 
                    )
                    if response.status_code == 200:
                        ai_response = response.json()["response"]
                        print(f"AI response: {ai_response}")

                        # Customize voice output based on persona
                        language_code = get_language_code(persona.language)
                        accent = get_tld(persona.country)
                        tts = gTTS(text=ai_response, lang=language_code, tld=accent)
                        fp = BytesIO()
                        tts.write_to_fp(fp)
                        fp.seek(0)
                        pygame.mixer.music.load(fp)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)

                    else:
                        print(f"Error from FastAPI: {response.status_code} - {response.text}")
                        await websocket.send_text(json.dumps({"error": "Error getting AI response."}))
                        # Handle error (e.g., speak an error message)

                except sr.UnknownValueError:
                    print("Unable to understand audio")
                    await websocket.send_text(json.dumps({"error": "Unable to understand audio."}))
                    # Handle error (e.g., speak an error message)
                except sr.RequestError as e:
                    print(f"Could not request results: {e}")
                    await websocket.send_text(json.dumps({"error": "Could not request results."}))
                    # Handle error (e.g., speak an error message)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Invalid message: {message} - Error: {e}")
            await websocket.send_text(json.dumps({"error": "Invalid message format."}))
            # Handle invalid messages 
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import os

# Define the required scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.readonly',  # Example existing scope
    'https://www.googleapis.com/auth/userinfo.profile',  # Example existing scope
    # Add any other existing scopes here
]

# Path to your client_secret.json file
CLIENT_SECRET_FILE = 'client_secret.json'

# Run the OAuth2 flow to get new credentials
flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
creds = flow.run_local_server(port=8000)

# Save the credentials to a file or database
with open('secrets.json', 'w') as token:
    token.write(creds.to_json())

# Load the credentials from the file
with open('secrets.json', 'r') as token:
    creds_info = json.load(token)
    creds = Credentials.from_authorized_user_info(creds_info, SCOPES)

# Use the credentials to build the service
service = build('calendar', 'v3', credentials=creds)

# Example: List the next 10 events on the user's calendar
events_result = service.events().list(calendarId='primary', maxResults=10, singleEvents=True, orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    print(start, event['summary'])

# Atlas AI

This repository contains the backend code for an AI Voice Assistant application built with FastAPI. The application allows users to interact with an AI using text or voice, select from different AI personas, and send emails using the Gmail API.

## Features

- User authentication using Google OAuth.
- Selection of pre-defined AI personas with customizable language and accent.
- Text-based and voice-based interaction with the AI.
- Conversation history storage and retrieval.
- Email drafting using ChatGPT and sending using the Gmail API.

## Technologies Used

- FastAPI
- SQLAlchemy
- Pydantic
- WebSockets
- Google OAuth 2.0
- Gmail API
- Google People API
- OpenAI API (ChatGPT)
- Python 3.12

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-username/your-repository-name.git
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate the Virtual Environment:**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create a `.env` File:**
   - Create a file named `.env` in the root directory of the project.
   - Add the following environment variables, replacing the placeholders with your actual values:

     ```
     DATABASE_URL=your_database_url
     JWT_SECRET_KEY=your_jwt_secret_key
     JWT_ALGORITHM=HS256
     ACCESS_TOKEN_EXPIRE_MINUTES=30
     REFRESH_TOKEN_EXPIRE_MINUTES=1440
     GOOGLE_CLIENT_ID=your_google_client_id
     GOOGLE_CLIENT_SECRET=your_google_client_secret
     GOOGLE_REDIRECT_URI=your_google_redirect_uri
     SCOPES=your_comma_separated_list_of_google_scopes
     OPENAI_API_KEY=your_openai_api_key
     ALLOWED_ORIGINS=your_allowed_origins (comma-separated)
     API_PREFIX=/api/v1
     DEBUG=True
     ```

6. **Populate the Database (Optional):**
   - If you have a script to populate the database with initial data (e.g., personas), run it now.

## Running the Application

1. **Start the FastAPI Server:**
   ```bash
   uvicorn app.main:app --reload --ssl-keyfile=localhost.key --ssl-certfile=localhost.crt
   ```

2. **Access the Application:**
   - Open your web browser and go to `https://127.0.0.1:8000` (or the port you specified).

## Deploying
 - For now, just testing I have push access to this repo
## Usage

- **Authentication:** Users can sign up or log in using their Google accounts.
- **Persona Selection:** Select an AI persona from the dropdown menu.
- **Text Interaction:** Type your message in the input field and click "Send."
- **Voice Interaction:** Click the microphone button to start recording, and click it again to stop and send the audio.
- **Email Drafting:** Use the "Send Email" button (you'll need to implement this in the frontend) to initiate the email drafting process.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you have any suggestions or improvements.

## License

This project is licensed under the MIT License.


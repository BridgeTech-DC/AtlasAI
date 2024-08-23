from fastapi import FastAPI, Depends, WebSocket, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.datastructures import MutableHeaders
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api.auth.routes import router as auth_router
from app.api.persona.routes import router as persona_router
from app.api.ai.routes import router as ai_router
from app.api.ai.conversations.routes import router as conversation_router
from app.api.google.gmail.routes import router as gmail_router
from app.api.auth.manager import get_current_user
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .config import settings
from .database import engine, Base, get_async_session
from app.api.auth.routes import current_active_user, fastapi_users, auth_backend, check_and_refresh_token
from app.models import User
from app.api.persona.voices import handle_voice_interaction # Import the function
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Assistant Backend")

logging.basicConfig(level=logging.DEBUG)

# Define JWTAuthMiddleware
class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("Authorization")
        if token:
            headers = MutableHeaders(request.headers)
            headers["Authorization"] = token
            request._headers = headers
        response = await call_next(request)
        return response

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/app/auth/jwt/login")

# Add middleware to the FastAPI instance
app.add_middleware(JWTAuthMiddleware)

@app.middleware("https")
async def check_and_refresh_token_middleware(request: Request, call_next):
    response = await check_and_refresh_token(request, call_next)
    return response

# Include API routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(persona_router, prefix=settings.API_PREFIX)
app.include_router(ai_router, prefix=settings.API_PREFIX)
app.include_router(conversation_router, prefix=settings.API_PREFIX)
app.include_router(gmail_router, prefix=settings.API_PREFIX)

templates = Jinja2Templates(directory="app/templates")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="app/templates"), name="static")

@app.on_event("startup")
async def startup():
    # This will create all tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()

# CORS Configuration
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,  # Allow cookies
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )

@app.get("/", response_class=HTMLResponse)
def root(request: Request, user: User = Depends(get_current_user)):
    if user:
        return templates.TemplateResponse("home.html", {"request": request})
    else:
        return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket connections for voice interaction."""
    try:
        logger.debug("WebSocket connection attempt")
        await websocket.accept()
        logger.debug("WebSocket connection accepted")
        await handle_voice_interaction(websocket)
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}", exc_info=True)  # Log the error with stack trace

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))  # Use the PORT environment variable if available
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
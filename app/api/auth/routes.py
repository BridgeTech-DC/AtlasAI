# auth/routes.py
from fastapi import APIRouter, Request, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from app.config import settings
from .manager import get_user_manager
from app.database import get_async_session
from app.models import User, GoogleCredentials
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import UUID
from typing import Optional
from app.database import connect_to_db, close_db_connection
from traceback import print_exc
from urllib.parse import parse_qs, urlencode
import httpx
from sqlalchemy.sql import select
from fastapi_users.jwt import generate_jwt, decode_jwt
from datetime import datetime, timedelta
from app.api.auth.manager import get_current_user
from sqlalchemy.orm import joinedload
import json

SECRET = settings.JWT_SECRET_KEY

bearer_transport = BearerTransport(tokenUrl="/app/auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(superuser=True)

router = APIRouter(tags=["Authentication"])

@router.on_event("startup")
async def startup():
    await connect_to_db()

@router.on_event("shutdown")
async def shutdown():
    await close_db_connection()

def get_google_flow(redirect_uri: str) -> Flow:
    return Flow.from_client_secrets_file(
        'client_secret.json',
        scopes= settings.SCOPES.split(","),
        redirect_uri=redirect_uri
    )


async def refresh_google_token(user: User, db: AsyncSession):

    google_credentials = user.google_credentials
    if google_credentials and google_credentials.refresh_token:
        credentials = Credentials(
            token=None,
            refresh_token=google_credentials.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        )
        credentials.refresh(GoogleRequest())
        
        # Update the credentials in the database
        google_credentials.access_token = credentials.token
        google_credentials.expires_at = credentials.expiry
        await db.commit()
        return credentials.token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to refresh token")

async def check_and_refresh_token(request: Request, call_next):
    user = await get_current_user(request)
    if user:
        db = await get_async_session()
        google_credentials = user.google_credentials
        if google_credentials and google_credentials.expires_at <= datetime.utcnow():
            try:
                await refresh_google_token(user, db)
            except HTTPException as e:
                return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    response = await call_next(request)
    return response

# --- Google Signup ---
@router.get("/google/signup")
async def google_signup(request: Request):
    """Initiates Google signup flow."""
    redirect_uri = request.url_for("google_signup_callback")
    flow = get_google_flow(redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return RedirectResponse(authorization_url)

@router.get("/google/signup/callback")
async def google_signup_callback(request: Request, db: AsyncSession = Depends(get_async_session)):
    """Callback for Google signup."""
    try:
        redirect_uri = request.url_for("google_signup_callback")
        flow = get_google_flow(redirect_uri)
        flow.fetch_token(authorization_response=request.url._url)
        credentials = flow.credentials


        async with httpx.AsyncClient() as client:
            user_info = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            user_info = user_info.json()

        # Check if user already exists (you might want to handle this differently)
        existing_user = await db.execute(select(User).where(User.google_id == user_info["sub"]))
        existing_user = existing_user.scalar_one_or_none()
        if (existing_user):
            return RedirectResponse(url="/static/log-in.html?error=user_exists")

        # Create new user
        new_user = User(
            email=user_info["email"],
            hashed_password=None,
            google_id=user_info["sub"],
            is_active=True,
            is_verified=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Store Google Credentials
        google_credentials = GoogleCredentials(
            user_id=new_user.id,
            refresh_token=credentials.refresh_token,
            access_token=credentials.token,
            expires_at=credentials.expiry
        )
        db.add(google_credentials)
        await db.commit()

        # Generate JWT token and set cookie
        jwt_token = await auth_backend.get_strategy().write_token(new_user)
        response = RedirectResponse(url="/")
        response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=True)
        return response

    except Exception as e:
        print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Google Login ---
@router.get("/google/login")
async def google_login(request: Request):
    """Initiates Google login flow."""
    redirect_uri = request.url_for("google_login_callback")
    flow = get_google_flow(redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return RedirectResponse(authorization_url)

@router.get("/google/login/callback")
async def google_login_callback(request: Request, db: AsyncSession = Depends(get_async_session)):
    """Callback for Google login."""
    try:
        redirect_uri = request.url_for("google_login_callback")
        flow = get_google_flow(redirect_uri)
        flow.fetch_token(authorization_response=request.url._url)
        credentials = flow.credentials


        async with httpx.AsyncClient() as client:
            user_info = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {credentials.token}"},
            )
            user_info = user_info.json()

        # Find existing user
        result = await db.execute(
            select(User).options(joinedload(User.google_credentials)).where(User.google_id == user_info["sub"])
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found. Please sign up.")
        
        print("Refresh token",credentials.refresh_token)
        # Update Google credentials if a new refresh token is provided
        if user.google_credentials is None:
            google_credentials = GoogleCredentials(
                user_id=user.id,
                refresh_token=credentials.refresh_token,
                access_token=credentials.token,
                expires_at=credentials.expiry
            )
            db.add(google_credentials)
        else:
            if credentials.refresh_token:
                user.google_credentials.refresh_token = credentials.refresh_token
                user.google_credentials.access_token = credentials.token
                user.google_credentials.expires_at = credentials.expiry
        await db.commit()

        # Generate JWT token and set cookie
        jwt_token = await auth_backend.get_strategy().write_token(user)
        response = RedirectResponse(url="/")
        response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=True)
        return response

    except Exception as e:
        print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Refresh Token ---
@router.post("/auth/jwt/refresh")
async def refresh_jwt_token(response: Response, user: User = Depends(get_current_user)):
    
    """Endpoint to refresh JWT token."""
    try:
        jwt_token = await auth_backend.get_strategy().write_token(user)
        response.set_cookie("Authorization", f"Bearer {jwt_token}", httponly=True)
        return {"access_token": jwt_token}
    except Exception as e:
        print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

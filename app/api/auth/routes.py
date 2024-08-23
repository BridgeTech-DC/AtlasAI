from fastapi import APIRouter, Request, Depends, HTTPException, status, Response, File, UploadFile
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from app.config import settings
from .manager import get_user_manager
from app.database import get_async_session
from app.models import User as UserModel, GoogleCredentials
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
import os
import shutil
from .schemas import User  # Import the User schema

SECRET = settings.JWT_SECRET_KEY

bearer_transport = BearerTransport(tokenUrl="/app/auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[UserModel, UUID](
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

async def refresh_google_token(user: UserModel, db: AsyncSession):
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

        existing_user = await db.execute(select(UserModel).where(UserModel.google_id == user_info["sub"]))
        existing_user = existing_user.scalar_one_or_none()

        if existing_user:
            return RedirectResponse(url="/static/log-in.html?error=user_exists")

        new_user = UserModel(
            email=user_info["email"],
            hashed_password=None,
            google_id=user_info["sub"],
            google_username=user_info.get("name"),
            profile_image_url=user_info.get("picture"),  # Store profile image URL
            is_active=True,
            is_verified=True,
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        google_credentials = GoogleCredentials(
            user_id=new_user.id,
            refresh_token=credentials.refresh_token,
            access_token=credentials.token,
            expires_at=credentials.expiry
        )

        db.add(google_credentials)
        await db.commit()

        jwt_token = await auth_backend.get_strategy().write_token(new_user)
        response = RedirectResponse(url="/")
        response.set_cookie(
            key="Authorization",
            value=f"Bearer {jwt_token}",
            httponly=True,
            samesite="None",
            secure=True  # Ensure this is only set if you're using HTTPS
        )
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

        result = await db.execute(
            select(UserModel).options(joinedload(UserModel.google_credentials)).where(UserModel.google_id == user_info["sub"])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found. Please sign up.")

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

        # Update Google username and profile image if they have changed
        if user.google_username != user_info.get("name"):
            user.google_username = user_info.get("name")
        if not user.profile_image_url:  # Only update if profile_image_url is empty
            user.profile_image_url = user_info.get("picture")

        await db.commit()

        jwt_token = await auth_backend.get_strategy().write_token(user)
        response = RedirectResponse(url="/")
        response.set_cookie(
            key="Authorization",
            value=f"Bearer {jwt_token}",
            httponly=True,
            samesite="None",
            secure=True  # Ensure this is only set if you're using HTTPS
        )
        return response

    except Exception as e:
        print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/auth/upload-profile-picture")
async def upload_profile_picture(file: UploadFile, user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    try:
        # Define the directory and file location
        directory = "app/templates/media/profile_pictures"
        file_location = os.path.join(directory, f"{user.id}_{file.filename}")

        # Create the directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        # Save the file
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Update the user's profile image URL
        user.profile_image_url = f"/static/media/profile_pictures/{user.id}_{file.filename}"
        await db.commit()

        return {"message": "Profile picture uploaded successfully", "profile_image_url": user.profile_image_url}
    except Exception as e:
        print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# --- Refresh Token ---
@router.post("/auth/jwt/refresh")
async def refresh_jwt_token(response: Response, user: UserModel = Depends(get_current_user)):
    """Endpoint to refresh JWT token."""
    try:
        jwt_token = await auth_backend.get_strategy().write_token(user)
        response.set_cookie(
            key="Authorization",
            value=f"Bearer {jwt_token}",
            httponly=True,
            samesite="None",
            secure=True  # Ensure this is only set if you're using HTTPS
        )
        return {"access_token": jwt_token}
    except Exception as e:
        print_exc()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# --- Get User Info ---
@router.get("/auth/user", response_model=User)
async def get_user_info(user: UserModel = Depends(get_current_user)):
    return user

# --- Logout ---
@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="Authorization",
        httponly=True,
        samesite="None",
        secure=True  # Ensure this is only set if you're using HTTPS
    )
    return {"message": "Successfully logged out"}

from typing import Optional
from fastapi import Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_users.jwt import decode_jwt
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.database import get_async_session
from app.models import User
from app.config import settings



async def get_current_user(request: Request, db: AsyncSession = Depends(get_async_session)) -> Optional[User]:
    """
    Authenticates user from JWT token stored in a cookie.
    """
    token = request.cookies.get("Authorization")
    if token:
        token = token.split(" ")[-1]  # No cookie, user is not authenticated
    else:
        print("No token found")
        RedirectResponse(url="/static/access-denied.html") 
        return None
    try:
        payload = decode_jwt(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM], audience="fastapi-users:auth")
        user_id = payload.get("sub")  # Extract user ID from JWT payload
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: Missing user ID")

        user = await db.get(User, user_id)  # Fetch user from database
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token: User not found")

        return user

    except Exception as e:
        RedirectResponse(url="/static/access-denied.html") 
        return None
        

# Provide a session to user_db
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

# UserManager class definition
from fastapi_users import BaseUserManager
from sqlalchemy.dialects.postgresql import UUID

class UserManager(BaseUserManager[User, UUID]):
    user_db_model = User
    reset_password_token_secret = settings.JWT_SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

# get_user_manager function using SQLAlchemyUserDatabase
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

    

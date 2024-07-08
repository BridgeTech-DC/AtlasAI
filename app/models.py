#app\models.py

from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from .database import Base, get_async_session 
from .config import settings
from typing import Optional
from fastapi import Request, Depends
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from app.api.ai.conversations.models import Conversation

class User(Base, SQLAlchemyBaseUserTableUUID):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    google_id = Column(String, unique=True, index=True, nullable=True)
    selected_persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)
    google_credentials = relationship("GoogleCredentials", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan") # Add this relationship

class GoogleCredentials(Base):
    __tablename__ = "google_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    refresh_token = Column(String, nullable=False)
    access_token = Column(String, nullable=True)  # Optional: Store the access token
    expires_at = Column(DateTime, nullable=True)   # Optional: Store the access token expiry time

    user = relationship("User", back_populates="google_credentials")
    
async def get_user_manager(user_db: SQLAlchemyUserDatabase):
    yield UserManager(user_db)

class UserManager(BaseUserManager[User, UUID]):
    user_db_model = User
    reset_password_token_secret = settings.JWT_SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

async def get_user_db(db: AsyncSession = Depends(get_async_session)): # Correctly use get_async_session
    yield SQLAlchemyUserDatabase(db, User)

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    is_verified: bool
    google_id: Optional[str]
    google_username: Optional[str]
    profile_image_url: Optional[str]
    created_at: datetime
    subscription: Optional[str] = "Free"

    class Config:
        orm_mode = True

class UserCreate(UserBase):
    hashed_password: Optional[str]

class UserUpdate(UserBase):
    pass

class User(UserBase):
    pass

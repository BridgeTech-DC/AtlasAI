from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models import User 
class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    gender = Column(Enum("Male", "Female", "Other", name="gender_enum"), nullable=False) 
    country = Column(String, nullable=False)
    language = Column(String, nullable=False)
    role = Column(String, nullable=False)
    characteristic = Column(String, nullable=False)
    expertise = Column(String, nullable=True) 
    conversations = relationship("Conversation", back_populates="persona", cascade="all, delete-orphan") # Add this relationship
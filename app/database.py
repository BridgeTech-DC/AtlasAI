from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings
import asyncpg
import databases

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

database = databases.Database(SQLALCHEMY_DATABASE_URL)

async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def connect_to_db():
    await database.connect()

async def close_db_connection():
    await database.disconnect()
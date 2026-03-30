"""
database.py

SQLAlchemy async setup for FastAPI project.
Defines engine, sessionmaker, Base, and get_db dependency generator.
"""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from fastapi import Depends

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/mydatabase"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,
    max_overflow=10
)

async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

Base = declarative_base()


async def getDb() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency generator for providing an async SQLAlchemy session.

    Yields:
        AsyncSession: An SQLAlchemy async session.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
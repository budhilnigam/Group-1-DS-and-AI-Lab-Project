"""
Pytest fixtures for FastAPI project tests.

Provides fixtures for:
- Async HTTP client (httpx.AsyncClient)
- Test database session
- Sample user data
- Authorization headers for authenticated requests
"""

import asyncio
from typing import AsyncGenerator, Dict, Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from httpx import AsyncClient

from app.main import app
from app.db.models import Base, User
from app.db.dependencies import get_db
from app.core.config import settings
from app.security import create_access_token


DATABASE_URL = settings.TEST_DATABASE_URL


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
  """
  Create an event loop for tests.
  """
  loop = asyncio.get_event_loop_policy().new_event_loop()
  yield loop
  loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator:
  """
  Create async engine for test database.
  """
  engine = create_async_engine(DATABASE_URL, future=True, echo=False)
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
  yield engine
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)
  await engine.dispose()


@pytest.fixture(scope="function")
async def testDb(test_engine) -> AsyncGenerator[AsyncSession, None]:
  """
  Provide a transactional test DB session.
  """
  async_session = async_sessionmaker(
    test_engine, expire_on_commit=False, class_=AsyncSession
  )
  async with async_session() as session:
    yield session
    await session.rollback()


@pytest.fixture(scope="function")
async def overrideGetDb(testDb: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
  """
  Override FastAPI dependency for DB session.
  """
  yield testDb


@pytest.fixture(scope="function")
async def asyncClient(
  overrideGetDb: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
  """
  Async HTTP client for testing FastAPI app.
  """
  app.dependency_overrides[get_db] = lambda: overrideGetDb
  async with AsyncClient(app=app, base_url="http://test") as client:
    yield client
  app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def sampleUser(testDb: AsyncSession) -> Dict[str, Any]:
  """
  Create and return a sample user in DB.
  """
  user_dict = {
    "email": "testuser@example.com",
    "hashed_password": "fakehashedpassword",
    "is_active": True,
  }
  user = User(**user_dict)
  testDb.add(user)
  await testDb.commit()
  await testDb.refresh(user)
  return {
    "id": user.id,
    "email": user.email,
    "password": "password",  # Plain text for tests
  }


@pytest.fixture(scope="function")
async def authHeaders(sampleUser: Dict[str, Any]) -> Dict[str, str]:
  """
  Authorization headers for test user.
  """
  token = create_access_token({"sub": sampleUser["email"]})
  return {"Authorization": f"Bearer {token}"}
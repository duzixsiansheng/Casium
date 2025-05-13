"""
Test configuration and fixtures
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import tempfile
import shutil
from pathlib import Path

from database.models import Base
from database.operations import DatabaseService


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db():
    """Create a test database for each test function."""
    # Use an in-memory SQLite database for tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.close()
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_service(test_db: AsyncSession):
    """Create a database service instance with test database."""
    return DatabaseService(test_db)


@pytest.fixture(scope="function")
def temp_upload_dir():
    """Create a temporary upload directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_passport_image():
    """Return a base64 encoded sample passport image."""
    # This would be a real base64 image in production
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_driver_license_image():
    """Return a base64 encoded sample driver's license image."""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@pytest.fixture
def sample_ead_card_image():
    """Return a base64 encoded sample EAD card image."""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    def _mock_response(document_type="passport", fields=None):
        if fields is None:
            fields = {
                "full_name": "John Doe",
                "date_of_birth": "01/15/1990",
                "passport_number": "123456789"
            }
        
        return {
            "choices": [{
                "message": {
                    "content": document_type if isinstance(document_type, str) else json.dumps(fields)
                }
            }]
        }
    
    return _mock_response
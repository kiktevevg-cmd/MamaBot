import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base, MemoryFacts, User, UserSettings
from database import crud


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        user = User(user_id=123, first_name="Test")
        sess.add(user)
        sess.add(UserSettings(user_id=123))
        sess.add(MemoryFacts(user_id=123))
        await sess.commit()
        yield sess


@pytest.mark.asyncio
async def test_update_and_get_facts(session):
    await crud.update_memory_facts(session, 123, {"work": "собеседование завтра"})
    facts = await crud.get_memory_facts(session, 123)
    assert facts["work"] == "собеседование завтра"


@pytest.mark.asyncio
async def test_merge_facts(session):
    await crud.update_memory_facts(session, 123, {"work": "офис"})
    await crud.update_memory_facts(session, 123, {"health": "болит спина"})
    facts = await crud.get_memory_facts(session, 123)
    assert facts["work"] == "офис"
    assert facts["health"] == "болит спина"


@pytest.mark.asyncio
async def test_clear_memory(session):
    await crud.update_memory_facts(session, 123, {"work": "IT", "health": "ok"})
    await crud.clear_memory(session, 123)
    facts = await crud.get_memory_facts(session, 123)
    assert facts == {}


@pytest.mark.asyncio
async def test_delete_fact(session):
    await crud.update_memory_facts(session, 123, {"work": "IT", "pet": "кот"})
    await crud.delete_memory_fact(session, 123, "work")
    facts = await crud.get_memory_facts(session, 123)
    assert "work" not in facts
    assert facts["pet"] == "кот"

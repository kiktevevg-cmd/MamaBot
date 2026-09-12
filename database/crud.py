import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import CrisisLog, DndSchedule, MemoryFacts, Message, User, UserSettings


async def get_or_create_user(
    session: AsyncSession,
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.settings),
            selectinload(User.memory),
            selectinload(User.dnd_schedules),
        )
        .where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if user:
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        user.last_activity = datetime.utcnow()
        await session.commit()
        return user

    user = User(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        last_activity=datetime.utcnow(),
    )
    session.add(user)
    session.add(UserSettings(user_id=user_id, user_name=first_name))
    session.add(MemoryFacts(user_id=user_id))
    await session.commit()

    result = await session.execute(
        select(User)
        .options(
            selectinload(User.settings),
            selectinload(User.memory),
            selectinload(User.dnd_schedules),
        )
        .where(User.user_id == user_id)
    )
    return result.scalar_one()


async def get_user(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.settings),
            selectinload(User.memory),
            selectinload(User.dnd_schedules),
        )
        .where(User.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def update_user_settings(
    session: AsyncSession, user_id: int, **fields: Any
) -> UserSettings | None:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return None
    for key, value in fields.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    settings.updated_at = datetime.utcnow()
    await session.commit()
    return settings


async def add_message(
    session: AsyncSession,
    user_id: int,
    role: str,
    content: str,
    is_crisis: bool = False,
) -> Message:
    msg = Message(user_id=user_id, role=role, content=content, is_crisis=is_crisis)
    session.add(msg)
    await session.commit()
    return msg


async def get_recent_messages(
    session: AsyncSession, user_id: int, limit: int = 10
) -> list[Message]:
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


async def get_last_message_time(session: AsyncSession, user_id: int) -> datetime | None:
    result = await session.execute(
        select(Message.created_at)
        .where(Message.user_id == user_id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def user_has_recent_activity(
    session: AsyncSession, user_id: int, minutes: int = 15
) -> bool:
    threshold = datetime.utcnow() - timedelta(minutes=minutes)
    result = await session.execute(
        select(User.last_activity).where(
            User.user_id == user_id, User.last_activity >= threshold
        )
    )
    return result.scalar_one_or_none() is not None


async def get_active_users(session: AsyncSession) -> list[User]:
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.settings),
            selectinload(User.memory),
            selectinload(User.dnd_schedules),
        )
        .where(User.last_activity.isnot(None))
    )
    return list(result.scalars().all())


async def get_memory_facts(session: AsyncSession, user_id: int) -> dict[str, str]:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        return {}
    try:
        return json.loads(memory.facts)
    except json.JSONDecodeError:
        return {}


async def update_memory_facts(
    session: AsyncSession, user_id: int, new_facts: dict[str, str]
) -> dict[str, str]:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        memory = MemoryFacts(user_id=user_id)
        session.add(memory)

    current = {}
    try:
        current = json.loads(memory.facts)
    except json.JSONDecodeError:
        pass

    current.update({k: v for k, v in new_facts.items() if v})
    memory.facts = json.dumps(current, ensure_ascii=False)
    memory.updated_at = datetime.utcnow()
    await session.commit()
    return current


async def clear_memory(
    session: AsyncSession, user_id: int, topic: str | None = None
) -> None:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        return

    if topic:
        facts = json.loads(memory.facts or "{}")
        facts.pop(topic, None)
        memory.facts = json.dumps(facts, ensure_ascii=False)
    else:
        memory.facts = "{}"
        memory.last_topics = "[]"
        memory.context_messages = "[]"
    memory.updated_at = datetime.utcnow()
    await session.commit()


async def delete_memory_fact(session: AsyncSession, user_id: int, key: str) -> bool:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        return False
    facts = json.loads(memory.facts or "{}")
    if key not in facts:
        return False
    del facts[key]
    memory.facts = json.dumps(facts, ensure_ascii=False)
    memory.updated_at = datetime.utcnow()
    await session.commit()
    return True


async def update_mood_trend(session: AsyncSession, user_id: int, mood: str) -> None:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if memory:
        memory.mood_trend = mood
        memory.updated_at = datetime.utcnow()
        await session.commit()


async def log_crisis(
    session: AsyncSession,
    user_id: int,
    trigger_text: str,
    severity_level: str,
    response_sent: str,
) -> CrisisLog:
    log = CrisisLog(
        user_id=user_id,
        trigger_text=trigger_text[:200],
        severity_level=severity_level,
        response_sent=response_sent,
    )
    session.add(log)
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(
            crisis_mode=(severity_level == "red"),
            last_crisis_at=datetime.utcnow(),
            crisis_count=User.crisis_count + 1,
        )
    )
    await session.commit()
    return log


async def get_pending_crisis_followups(session: AsyncSession) -> list[CrisisLog]:
    now = datetime.utcnow()
    result = await session.execute(select(CrisisLog))
    logs = list(result.scalars().all())
    pending = []
    for log in logs:
        age = now - log.created_at
        if not log.follow_up_2h_sent and age >= timedelta(hours=2):
            pending.append(log)
        elif (
            not log.follow_up_24h_sent
            and log.follow_up_2h_sent
            and age >= timedelta(hours=24)
        ):
            pending.append(log)
    return pending


async def mark_followup_sent(
    session: AsyncSession, log_id: int, followup_type: str
) -> None:
    result = await session.execute(select(CrisisLog).where(CrisisLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        return
    if followup_type == "2h":
        log.follow_up_2h_sent = True
    elif followup_type == "24h":
        log.follow_up_24h_sent = True
    await session.commit()


async def set_dnd_schedule(
    session: AsyncSession,
    user_id: int,
    schedules: list[dict[str, Any]],
) -> None:
    result = await session.execute(
        select(DndSchedule).where(DndSchedule.user_id == user_id)
    )
    for item in result.scalars().all():
        await session.delete(item)
    for sched in schedules:
        session.add(
            DndSchedule(
                user_id=user_id,
                day_of_week=sched["day_of_week"],
                start_time=sched["start_time"],
                end_time=sched["end_time"],
            )
        )
    await session.commit()

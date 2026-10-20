import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.persona import (
    default_persona,
    default_relationship,
    dumps_json,
    ensure_persona,
    ensure_relationship,
    maybe_refresh_status,
    pick_status,
)
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
        if user.settings:
            await _ensure_persona_defaults(session, user.settings, commit=False)
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
    session.add(
        UserSettings(
            user_id=user_id,
            user_name=first_name,
            persona_json=dumps_json(default_persona()),
            relationship_json=dumps_json(default_relationship()),
            mama_status=pick_status("день"),
            mama_status_updated_at=datetime.utcnow(),
            onboarding_completed=False,
            onboarding_step=0,
        )
    )
    session.add(MemoryFacts(user_id=user_id, facts="{}"))
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


def _parse_facts_json(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if v is not None and str(v).strip()}


async def get_memory_facts(session: AsyncSession, user_id: int) -> dict[str, str]:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        return {}
    return _parse_facts_json(memory.facts)


async def update_memory_facts(
    session: AsyncSession, user_id: int, new_facts: dict[str, str]
) -> dict[str, str]:
    result = await session.execute(
        select(MemoryFacts).where(MemoryFacts.user_id == user_id)
    )
    memory = result.scalar_one_or_none()
    if not memory:
        # Explicit facts="{}" — без этого memory.facts бывает None до flush,
        # а json.loads(None) даёт TypeError и первая запись фактов молча ломалась.
        memory = MemoryFacts(user_id=user_id, facts="{}")
        session.add(memory)
        current: dict[str, str] = {}
    else:
        current = _parse_facts_json(memory.facts)

    current.update({k: str(v) for k, v in new_facts.items() if v})
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


async def _ensure_persona_defaults(
    session: AsyncSession, settings: UserSettings, *, commit: bool = True
) -> None:
    changed = False
    raw_p = (getattr(settings, "persona_json", None) or "").strip()
    if raw_p in ("", "{}"):
        settings.persona_json = dumps_json(default_persona())
        changed = True
    raw_r = (getattr(settings, "relationship_json", None) or "").strip()
    if raw_r in ("", "{}"):
        settings.relationship_json = dumps_json(default_relationship())
        changed = True
    if not getattr(settings, "mama_status", None):
        settings.mama_status = pick_status("день")
        settings.mama_status_updated_at = datetime.utcnow()
        changed = True
    if changed and commit:
        await session.commit()


async def get_persona(session: AsyncSession, user_id: int) -> dict:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return default_persona()
    await _ensure_persona_defaults(session, settings)
    return ensure_persona(settings.persona_json)


async def get_relationship(session: AsyncSession, user_id: int) -> dict:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return default_relationship()
    return ensure_relationship(settings.relationship_json)


async def update_persona(
    session: AsyncSession, user_id: int, patch: dict[str, Any]
) -> dict:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return default_persona()
    persona = ensure_persona(settings.persona_json)
    for key, value in patch.items():
        if value is None:
            continue
        if key in ("habits", "likes", "weaknesses", "catchphrases", "taboos") and isinstance(
            value, list
        ):
            persona[key] = value
        else:
            persona[key] = value
    settings.persona_json = dumps_json(persona)
    settings.updated_at = datetime.utcnow()
    await session.commit()
    return persona


async def update_relationship(
    session: AsyncSession, user_id: int, patch: dict[str, Any]
) -> dict:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return default_relationship()
    rel = ensure_relationship(settings.relationship_json)
    for key, value in patch.items():
        if value is None:
            continue
        if key in ("pet_names", "shared_jokes", "topics_joy", "topics_avoid"):
            if isinstance(value, list):
                rel[key] = value
            elif isinstance(value, str) and value.strip():
                items = rel.get(key) or []
                if value.strip() not in items:
                    items.append(value.strip())
                rel[key] = items[-8:]
        else:
            rel[key] = value
    settings.relationship_json = dumps_json(rel)
    settings.updated_at = datetime.utcnow()
    await session.commit()
    return rel


async def refresh_mama_status(
    session: AsyncSession, user_id: int, time_of_day: str, force: bool = False
) -> str:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        return pick_status(time_of_day)
    new_status = maybe_refresh_status(settings, time_of_day, force=force)
    if new_status != settings.mama_status or force:
        settings.mama_status = new_status
        settings.mama_status_updated_at = datetime.utcnow()
        await session.commit()
    return new_status


def settings_to_prompt_dict(settings: UserSettings) -> dict[str, Any]:
    """Поля настроек + persona для GPT."""
    persona = ensure_persona(getattr(settings, "persona_json", None))
    relationship = ensure_relationship(getattr(settings, "relationship_json", None))
    return {
        "mama_name": settings.mama_name,
        "mama_personality": settings.mama_personality,
        "enable_emojis": settings.enable_emojis,
        "response_length": settings.response_length,
        "user_name": settings.user_name,
        "user_gender": settings.user_gender,
        "persona": persona,
        "relationship": relationship,
        "mama_status": settings.mama_status or pick_status("день"),
        "onboarding_completed": bool(getattr(settings, "onboarding_completed", False)),
    }

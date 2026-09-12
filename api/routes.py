from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from api.validators import (
    DndActivateRequest,
    DndScheduleRequest,
    MemoryClearRequest,
    MemoryDeleteRequest,
    SettingsUpdateRequest,
)
from database import async_session, crud

router = APIRouter(prefix="/api")


def _settings_to_dict(settings) -> dict:
    return {
        "user_id": settings.user_id,
        "initiative_level": settings.initiative_level,
        "min_cooldown_minutes": settings.min_cooldown_minutes,
        "max_cooldown_hours": settings.max_cooldown_hours,
        "initiative_start_hour": settings.initiative_start_hour,
        "initiative_end_hour": settings.initiative_end_hour,
        "dnd_enabled": settings.dnd_enabled,
        "dnd_until": settings.dnd_until.isoformat() if settings.dnd_until else None,
        "user_gender": settings.user_gender,
        "user_name": settings.user_name,
        "mama_name": settings.mama_name,
        "mama_personality": settings.mama_personality,
        "enable_voice_recognition": settings.enable_voice_recognition,
        "enable_emojis": settings.enable_emojis,
        "response_length": settings.response_length,
        "enable_crisis_detection": settings.enable_crisis_detection,
        "crisis_sensitivity": settings.crisis_sensitivity,
        "enable_reactions": getattr(settings, "enable_reactions", True),
        "allow_multiple_reactions": getattr(settings, "allow_multiple_reactions", True),
        "reaction_style": getattr(settings, "reaction_style", "живой"),
        "reaction_sensitivity": getattr(settings, "reaction_sensitivity", 3),
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }


@router.get("/settings/{user_id}")
async def get_settings(user_id: int):
    async with async_session() as session:
        user = await crud.get_or_create_user(session, user_id)
        if not user.settings:
            raise HTTPException(status_code=404, detail="User not found")
        return _settings_to_dict(user.settings)


@router.post("/settings/update")
async def update_settings(body: SettingsUpdateRequest):
    fields = body.model_dump(exclude={"user_id"}, exclude_none=True)
    async with async_session() as session:
        settings = await crud.update_user_settings(session, body.user_id, **fields)
        if not settings:
            raise HTTPException(status_code=404, detail="User not found")
        return _settings_to_dict(settings)


@router.get("/memory/facts/{user_id}")
async def get_memory_facts(user_id: int):
    async with async_session() as session:
        facts = await crud.get_memory_facts(session, user_id)
        return {"user_id": user_id, "facts": facts}


@router.post("/memory/clear")
async def clear_memory(body: MemoryClearRequest):
    async with async_session() as session:
        if body.scope == "topic" and body.topic:
            await crud.clear_memory(session, body.user_id, topic=body.topic)
        else:
            await crud.clear_memory(session, body.user_id)
    return {"ok": True}


@router.post("/memory/delete")
async def delete_memory_fact(body: MemoryDeleteRequest):
    async with async_session() as session:
        deleted = await crud.delete_memory_fact(session, body.user_id, body.key)
        if not deleted:
            raise HTTPException(status_code=404, detail="Fact not found")
    return {"ok": True}


@router.post("/dnd/activate")
async def activate_dnd(body: DndActivateRequest):
    dnd_until = datetime.utcnow() + timedelta(hours=body.duration_hours)
    async with async_session() as session:
        settings = await crud.update_user_settings(
            session,
            body.user_id,
            dnd_enabled=True,
            dnd_until=dnd_until,
        )
        if not settings:
            raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "dnd_until": dnd_until.isoformat()}


@router.post("/dnd/schedule")
async def set_dnd_schedule(body: DndScheduleRequest):
    async with async_session() as session:
        await crud.set_dnd_schedule(session, body.user_id, body.schedules)
    return {"ok": True}


@router.get("/health")
async def health():
    return {"status": "ok"}

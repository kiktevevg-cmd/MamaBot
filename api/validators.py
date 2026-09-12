from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SettingsUpdateRequest(BaseModel):
    user_id: int
    initiative_level: int | None = Field(None, ge=1, le=5)
    min_cooldown_minutes: int | None = None
    max_cooldown_hours: int | None = None
    initiative_start_hour: int | None = Field(None, ge=0, le=23)
    initiative_end_hour: int | None = Field(None, ge=0, le=23)
    dnd_enabled: bool | None = None
    dnd_until: datetime | None = None
    user_gender: str | None = None
    user_name: str | None = None
    mama_name: str | None = None
    mama_personality: str | None = None
    enable_voice_recognition: bool | None = None
    enable_emojis: bool | None = None
    response_length: int | None = Field(None, ge=1, le=5)
    enable_crisis_detection: bool | None = None
    crisis_sensitivity: int | None = Field(None, ge=1, le=5)
    enable_reactions: bool | None = None
    allow_multiple_reactions: bool | None = None
    reaction_style: str | None = None
    reaction_sensitivity: int | None = Field(None, ge=1, le=5)
    enable_reactions: bool | None = None
    allow_multiple_reactions: bool | None = None
    reaction_style: str | None = None
    reaction_sensitivity: int | None = Field(None, ge=1, le=5)


class MemoryClearRequest(BaseModel):
    user_id: int
    scope: str = "all"
    topic: str | None = None


class MemoryDeleteRequest(BaseModel):
    user_id: int
    key: str


class DndActivateRequest(BaseModel):
    user_id: int
    duration_hours: float = 2


class DndScheduleRequest(BaseModel):
    user_id: int
    schedules: list[dict[str, Any]]

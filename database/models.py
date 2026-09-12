from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    timezone: Mapped[str] = mapped_column(String, default="UTC+3")
    crisis_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    last_crisis_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    crisis_count: Mapped[int] = mapped_column(Integer, default=0)

    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False)
    memory: Mapped["MemoryFacts"] = relationship(back_populates="user", uselist=False)
    dnd_schedules: Mapped[list["DndSchedule"]] = relationship(back_populates="user")
    messages: Mapped[list["Message"]] = relationship(back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        CheckConstraint("initiative_level BETWEEN 1 AND 5", name="ck_initiative_level"),
        CheckConstraint("response_length BETWEEN 1 AND 5", name="ck_response_length"),
        CheckConstraint("crisis_sensitivity BETWEEN 1 AND 5", name="ck_crisis_sensitivity"),
        CheckConstraint(
            "reaction_sensitivity BETWEEN 1 AND 5", name="ck_reaction_sensitivity"
        ),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    initiative_level: Mapped[int] = mapped_column(Integer, default=3)
    min_cooldown_minutes: Mapped[int] = mapped_column(Integer, default=45)
    max_cooldown_hours: Mapped[int] = mapped_column(Integer, default=6)
    initiative_start_hour: Mapped[int] = mapped_column(Integer, default=8)
    initiative_end_hour: Mapped[int] = mapped_column(Integer, default=22)
    dnd_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    dnd_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_gender: Mapped[str] = mapped_column(String, default="не указано")
    user_name: Mapped[str | None] = mapped_column(String, nullable=True)
    mama_name: Mapped[str] = mapped_column(String, default="Людмила Петровна")
    mama_personality: Mapped[str] = mapped_column(String, default="заботливая")
    enable_voice_recognition: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_emojis: Mapped[bool] = mapped_column(Boolean, default=True)
    response_length: Mapped[int] = mapped_column(Integer, default=3)
    enable_crisis_detection: Mapped[bool] = mapped_column(Boolean, default=True)
    crisis_sensitivity: Mapped[int] = mapped_column(Integer, default=3)
    enable_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_multiple_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    reaction_style: Mapped[str] = mapped_column(String, default="живой")
    reaction_sensitivity: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="settings")


class DndSchedule(Base):
    __tablename__ = "dnd_schedule"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_day_of_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    day_of_week: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[str] = mapped_column(String)
    end_time: Mapped[str] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="dnd_schedules")


class MemoryFacts(Base):
    __tablename__ = "memory_facts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    facts: Mapped[str] = mapped_column(Text, default="{}")
    last_topics: Mapped[str] = mapped_column(Text, default="[]")
    mood_trend: Mapped[str] = mapped_column(String, default="neutral")
    context_messages: Mapped[str] = mapped_column(Text, default="[]")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="memory")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_message_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    is_crisis: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="messages")


class CrisisLog(Base):
    __tablename__ = "crisis_logs"
    __table_args__ = (
        CheckConstraint(
            "severity_level IN ('green', 'yellow', 'red')",
            name="ck_severity_level",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer)
    trigger_text: Mapped[str] = mapped_column(Text)
    severity_level: Mapped[str] = mapped_column(String)
    response_sent: Mapped[str] = mapped_column(Text)
    follow_up_2h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_24h_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

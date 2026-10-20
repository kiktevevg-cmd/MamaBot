import logging
import random
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.gpt_client import GPTClient
from core.time_utils import get_time_of_day, get_user_local_time, is_in_dnd_schedule
from database import async_session, crud

logger = logging.getLogger(__name__)


def calculate_next_message_time(
    last_msg: datetime | None,
    settings: dict,
    has_recent_activity: bool,
) -> datetime:
    now = datetime.utcnow()
    if not last_msg:
        last_msg = now - timedelta(hours=1)

    if has_recent_activity:
        cooldown = settings.get("min_cooldown_minutes", 45)
    else:
        cooldown = settings.get("max_cooldown_hours", 6) * 60

    initiative = settings.get("initiative_level", 3)
    cooldown = cooldown * (3 / initiative)
    # Стабильный разброс от last_msg — иначе каждые 10 мин jitter менялся бы
    rng = random.Random(int(last_msg.timestamp()))
    jitter = rng.randint(-40, 50)
    return last_msg + timedelta(minutes=max(20, cooldown + jitter))


def should_send_message(user, settings: dict, last_msg_time: datetime | None) -> bool:
    now = datetime.utcnow()

    if settings.get("dnd_enabled") and settings.get("dnd_until"):
        if now < settings["dnd_until"]:
            return False

    if user.dnd_schedules and is_in_dnd_schedule(user.dnd_schedules, user.timezone):
        return False

    local_hour = get_user_local_time(user.timezone).hour
    if local_hour < settings.get("initiative_start_hour", 8):
        return False
    if local_hour > settings.get("initiative_end_hour", 22):
        return False

    next_time = calculate_next_message_time(
        last_msg_time,
        settings,
        has_recent_activity=False,
    )
    return now >= next_time


def pick_initiative_type(facts: dict, timezone: str) -> str:
    hour = get_user_local_time(timezone).hour
    if 5 <= hour < 11:
        pool = ["morning", "memory", "life", "checkin"] if facts else ["morning", "life", "checkin"]
    elif 11 <= hour < 17:
        pool = (
            ["day", "memory", "life", "checkin"]
            if facts
            else ["day", "life", "checkin", "general"]
        )
    elif 17 <= hour < 22:
        pool = (
            ["evening", "memory", "life", "checkin"]
            if facts
            else ["evening", "life", "checkin", "general"]
        )
    else:
        pool = ["checkin", "life", "general"]

    roll = random.random()
    if facts and roll < 0.35:
        return "memory"
    if roll < 0.55:
        return "life"
    return random.choice(pool)


class InitiativeScheduler:
    def __init__(self, bot: Bot, gpt: GPTClient) -> None:
        self.bot = bot
        self.gpt = gpt
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        self.scheduler.add_job(
            self.check_and_send_initiative,
            "interval",
            minutes=10,
            id="initiative_checker",
        )
        self.scheduler.add_job(
            self.check_crisis_followups,
            "interval",
            minutes=30,
            id="crisis_followup_checker",
        )
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)

    async def check_and_send_initiative(self) -> None:
        async with async_session() as session:
            users = await crud.get_active_users(session)
            for user in users:
                try:
                    settings = user.settings
                    if not settings:
                        continue

                    settings_dict = {
                        "initiative_level": settings.initiative_level,
                        "min_cooldown_minutes": settings.min_cooldown_minutes,
                        "max_cooldown_hours": settings.max_cooldown_hours,
                        "initiative_start_hour": settings.initiative_start_hour,
                        "initiative_end_hour": settings.initiative_end_hour,
                        "dnd_enabled": settings.dnd_enabled,
                        "dnd_until": settings.dnd_until,
                        **crud.settings_to_prompt_dict(settings),
                    }

                    last_msg = await crud.get_last_message_time(session, user.user_id)
                    if not should_send_message(user, settings_dict, last_msg):
                        continue

                    # Онбординг не завершён — не пишем первыми
                    if not getattr(settings, "onboarding_completed", True):
                        continue

                    facts = await crud.get_memory_facts(session, user.user_id)
                    time_of_day = get_time_of_day(user.timezone)
                    settings_dict["mama_status"] = await crud.refresh_mama_status(
                        session, user.user_id, time_of_day
                    )
                    msg_type = pick_initiative_type(facts, user.timezone)

                    recent = await crud.get_recent_messages(session, user.user_id, limit=16)
                    recent_assistant = [
                        m.content for m in recent if m.role == "assistant"
                    ][-8:]

                    content = await self.gpt.generate_initiative_message(
                        settings_dict,
                        facts,
                        time_of_day,
                        msg_type,
                        recent_messages=recent_assistant,
                    )
                    if not content:
                        continue
                    await self.bot.send_message(user.user_id, content)
                    await crud.add_message(session, user.user_id, "assistant", content)
                    logger.info(
                        "Initiative (%s) sent to user %d", msg_type, user.user_id
                    )
                except Exception as e:
                    logger.error("Initiative error for user %d: %s", user.user_id, e)

    async def check_crisis_followups(self) -> None:
        async with async_session() as session:
            pending = await crud.get_pending_crisis_followups(session)
            for log in pending:
                try:
                    age = datetime.utcnow() - log.created_at
                    if not log.follow_up_2h_sent and age >= timedelta(hours=2):
                        text = (
                            "Солнышко, я всё ещё думаю о тебе. Как ты сейчас? "
                            "Помни — я рядом ❤️"
                        )
                        await self.bot.send_message(log.user_id, text)
                        await crud.mark_followup_sent(session, log.id, "2h")
                    elif (
                        not log.follow_up_24h_sent
                        and log.follow_up_2h_sent
                        and age >= timedelta(hours=24)
                    ):
                        text = (
                            "Мой хороший, прошли сутки. Надеюсь, тебе стало хоть чуть легче. "
                            "Расскажи, как дела?"
                        )
                        await self.bot.send_message(log.user_id, text)
                        await crud.mark_followup_sent(session, log.id, "24h")
                except Exception as e:
                    logger.error("Followup error: %s", e)

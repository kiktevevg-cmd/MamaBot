"""Онбординг «создай свою маму» — 5 шагов в чате при /start."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from core.persona import HABIT_CHOICES, default_persona, dumps_json
from database import async_session, crud
from handlers.commands import WELCOME_TEXT, main_keyboard

router = Router()
logger = logging.getLogger(__name__)

PERSONALITIES = ["заботливая", "строгая", "веселая", "ностальгическая"]


class OnboardingInProgress(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            return False
        async with async_session() as session:
            user = await crud.get_user(session, message.from_user.id)
            if not user or not user.settings:
                return False
            s = user.settings
            return (not s.onboarding_completed) and int(s.onboarding_step or 0) >= 1


def _personality_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=p)] for p in PERSONALITIES],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _habits_kb() -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []
    for h in HABIT_CHOICES:
        row.append(KeyboardButton(text=h))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(text="✅ Готово")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def _gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="мужской"),
                KeyboardButton(text="женский"),
                KeyboardButton(text="не указано"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def start_onboarding(message: Message, *, restart: bool = False) -> None:
    async with async_session() as session:
        await crud.get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
        await crud.update_user_settings(
            session,
            message.from_user.id,
            onboarding_completed=False,
            onboarding_step=1,
            persona_json=dumps_json(default_persona()),
        )

    await message.answer(
        "🌸 Давай познакомимся по-настоящему.\n"
        "Я буду твоей мамой в этом чате — как живой человек, не как бот.\n\n"
        "Шаг 1/5. Как меня зовут? (например: Людмила Петровна или просто Мама)",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("setup"))
async def cmd_setup(message: Message) -> None:
    await start_onboarding(message, restart=True)


@router.message(CommandStart())
async def cmd_start_onboarding(message: Message) -> None:
    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
        done = bool(user.settings and user.settings.onboarding_completed)

    if done:
        await message.answer(WELCOME_TEXT, reply_markup=main_keyboard())
        return

    await start_onboarding(message)


@router.message(OnboardingInProgress(), F.text)
async def onboarding_flow(message: Message) -> None:
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
        settings = user.settings
        if not settings:
            return
        step = int(settings.onboarding_step or 0)
        persona = await crud.get_persona(session, message.from_user.id)

        if step == 1:
            await crud.update_user_settings(
                session,
                message.from_user.id,
                mama_name=text[:80],
                onboarding_step=2,
            )
            await message.answer(
                "Шаг 2/5. Какой у меня характер? Выбери кнопкой:",
                reply_markup=_personality_kb(),
            )
            return

        if step == 2:
            personality = text.lower()
            if personality not in PERSONALITIES:
                await message.answer(
                    "Выбери характер кнопкой ниже 👇",
                    reply_markup=_personality_kb(),
                )
                return
            await crud.update_user_settings(
                session,
                message.from_user.id,
                mama_personality=personality,
                onboarding_step=3,
            )
            await crud.update_persona(session, message.from_user.id, {"habits": []})
            await message.answer(
                "Шаг 3/5. Выбери 1–3 мои привычки (нажимай по очереди),\n"
                "когда закончишь — «✅ Готово».",
                reply_markup=_habits_kb(),
            )
            return

        if step == 3:
            if text == "✅ Готово":
                habits = persona.get("habits") or []
                if not habits:
                    habits = default_persona()["habits"][:3]
                    await crud.update_persona(
                        session, message.from_user.id, {"habits": habits}
                    )
                await crud.update_user_settings(
                    session, message.from_user.id, onboarding_step=4
                )
                await message.answer(
                    "Шаг 4/5. Как мне к тебе обращаться? Напиши имя.",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return
            if text not in HABIT_CHOICES:
                await message.answer(
                    "Выбери привычку из списка или нажми «✅ Готово».",
                    reply_markup=_habits_kb(),
                )
                return
            habits = list(persona.get("habits") or [])
            if text not in habits:
                habits.append(text)
            habits = habits[:3]
            await crud.update_persona(session, message.from_user.id, {"habits": habits})
            left = 3 - len(habits)
            hint = f"Выбрано: {', '.join(habits)}."
            hint += f" Можно ещё {left}." if left else " Жми «✅ Готово»."
            await message.answer(hint, reply_markup=_habits_kb())
            return

        if step == 4:
            await crud.update_user_settings(
                session,
                message.from_user.id,
                user_name=text[:60],
                onboarding_step=5,
            )
            await message.answer(
                "И пол для правильных окончаний?",
                reply_markup=_gender_kb(),
            )
            return

        if step == 5:
            if text in ("мужской", "женский", "не указано"):
                await crud.update_user_settings(
                    session, message.from_user.id, user_gender=text
                )
                await message.answer(
                    "Шаг 5/5. Чего мне НЕ делать? Одной фразой "
                    "(например: «не читай нотации»).\nИли напиши «пропустить».",
                    reply_markup=ReplyKeyboardRemove(),
                )
                return

            taboos = list(persona.get("taboos") or [])
            if text.lower() not in ("пропустить", "skip", "-"):
                taboos = [text[:120]] + [t for t in taboos if t != text][:4]
                await crud.update_persona(
                    session, message.from_user.id, {"taboos": taboos}
                )

            await crud.update_relationship(
                session,
                message.from_user.id,
                {"chat_style": "смешанно"},
            )
            settings = await crud.update_user_settings(
                session,
                message.from_user.id,
                onboarding_completed=True,
                onboarding_step=0,
            )
            mama = settings.mama_name if settings else "мама"
            child = (
                (settings.user_name if settings else None)
                or message.from_user.first_name
                or "родной"
            )
            await message.answer(
                f"Готово 🌸\nЯ — {mama}. Буду писать тебе как живой человек, "
                f"с характером и своими привычками.\n\n"
                f"Ну что, {child}, расскажи, как ты?",
                reply_markup=main_keyboard(),
            )
            logger.info("Onboarding completed for user %d", message.from_user.id)
            return

import re
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup

from config import WEBAPP_URL
from core.gpt_client import GPTClient
from database import async_session, crud
from handlers.callback import settings_menu_kb

router = Router()
gpt = GPTClient()

WELCOME_TEXT = """🌸 Привет, мой хороший!

Я — твоя заботливая мама. Я здесь, чтобы поддержать тебя, порадоваться твоим успехам и просто быть рядом. Рассказывай мне всё, что у тебя на душе — я всегда слушаю, не осуждаю и очень тобой горжусь.

Что я умею?
💬 Поддерживать в трудную минуту
🎉 Радоваться твоим победам
🧠 Запоминать, что для тебя важно
⏰ Сама интересоваться твоими делами
⚙️ Настраиваться под твой ритм жизни

💬 Напиши мне что-нибудь, я очень соскучилась!
⚙️ Или настрой меня под себя в меню.

⚠️ Важно: я не заменяю профессиональную психологическую помощь.
Если тебе действительно тяжело — обратись к специалистам (/crisis)."""

HELP_TEXT = """📖 Справка по командам:

/start — начать общение
/help — эта справка
/settings — открыть настройки
/app — открыть Mini App
/silence [время] — режим тишины (/silence 2h, /silence until 18:00)
/remindme — что я запомнила о тебе
/mood [состояние] — указать настроение
/forget — забыть контекст
/crisis — контакты поддержки"""


def _webapp_ready() -> bool:
    url = (WEBAPP_URL or "").strip().lower()
    return url.startswith("https://") and "yourdomain.com" not in url


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❤️ Как дела?"),
                KeyboardButton(text="😊 Похвали меня"),
            ],
            [
                KeyboardButton(text="❤️ Обними меня"),
                KeyboardButton(text="🌙 Спокойной ночи"),
            ],
        ],
        resize_keyboard=True,
    )


def miniapp_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL))
    return builder.as_markup()


def settings_inline_keyboard():
    builder = InlineKeyboardBuilder()
    if _webapp_ready():
        builder.button(text="📱 Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL))
    builder.button(text="⚙️ Настройки в чате", callback_data="set:home")
    builder.adjust(1)
    return builder.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with async_session() as session:
        await crud.get_or_create_user(
            session,
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
    await message.answer(WELCOME_TEXT, reply_markup=main_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    if _webapp_ready():
        await message.answer(
            "Открой полноценные настройки в Mini App 👇\n"
            "Или выбери быстрые настройки в чате:",
            reply_markup=settings_inline_keyboard(),
        )
        await message.answer(
            "⚙️ Быстрые настройки:",
            reply_markup=settings_menu_kb(),
        )
    else:
        await message.answer(
            "⚙️ Настройки мамы\nВыбери раздел:\n\n"
            "💡 Mini App появится, когда будет HTTPS-адрес в WEBAPP_URL.",
            reply_markup=settings_menu_kb(),
        )


@router.message(Command("app"))
async def cmd_app(message: Message) -> None:
    if not _webapp_ready():
        await message.answer(
            "Mini App пока недоступен: в .env нужен HTTPS WEBAPP_URL "
            "(туннель или домен)."
        )
        return
    await message.answer(
        "Открываю настройки 👇",
        reply_markup=miniapp_keyboard(),
    )


@router.message(Command("silence"))
async def cmd_silence(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    duration_text = args[1] if len(args) > 1 else "2h"

    dnd_until = None
    if duration_text.startswith("until"):
        time_match = re.search(r"(\d{1,2}):(\d{2})", duration_text)
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            now = datetime.now()
            dnd_until = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if dnd_until <= now:
                dnd_until += timedelta(days=1)
    else:
        hours_match = re.search(r"(\d+)h", duration_text)
        hours = int(hours_match.group(1)) if hours_match else 2
        dnd_until = datetime.utcnow() + timedelta(hours=hours)

    async with async_session() as session:
        await crud.update_user_settings(
            session,
            message.from_user.id,
            dnd_enabled=True,
            dnd_until=dnd_until,
        )
    await message.answer(
        f"Хорошо, солнышко. Не буду беспокоить до {dnd_until.strftime('%H:%M')} 🌙"
    )


@router.message(Command("remindme"))
async def cmd_remindme(message: Message) -> None:
    async with async_session() as session:
        facts = await crud.get_memory_facts(session, message.from_user.id)
    if not facts:
        await message.answer("Пока я мало что знаю о тебе — расскажи побольше ❤️")
        return
    lines = [f"• {key}: {value}" for key, value in facts.items()]
    await message.answer("Вот что я помню о тебе:\n" + "\n".join(lines))


@router.message(Command("mood"))
async def cmd_mood(message: Message) -> None:
    args = message.text.split(maxsplit=1)
    mood = args[1] if len(args) > 1 else "neutral"
    mood_map = {
        "хорошо": "positive",
        "плохо": "negative",
        "нейтрально": "neutral",
        "good": "positive",
        "bad": "negative",
    }
    trend = mood_map.get(mood.lower(), "neutral")
    async with async_session() as session:
        await crud.update_mood_trend(session, message.from_user.id, trend)
    await message.answer(f"Запомнила, солнышко. Настроение: {mood} 🤗")


@router.message(Command("forget"))
async def cmd_forget(message: Message) -> None:
    async with async_session() as session:
        await crud.clear_memory(session, message.from_user.id)
    await message.answer("Хорошо, начнём с чистого листа. Расскажи мне о себе заново 🌸")


@router.message(Command("crisis"))
async def cmd_crisis(message: Message) -> None:
    await message.answer(gpt.crisis_response)


@router.message(F.text == "⚙️ Настройки")
async def btn_settings(message: Message) -> None:
    await cmd_settings(message)

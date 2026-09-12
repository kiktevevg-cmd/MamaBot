import logging
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.types import Message, ReactionTypeEmoji

from core.button_handler import BUTTON_MAP, ButtonHandler
from core.crisis_detector import CrisisDetector
from core.gpt_client import GPTClient
from core.memory_manager import MemoryManager
from core.reaction_manager import ReactionManager
from core.time_utils import get_time_of_day
from database import async_session, crud

router = Router()
logger = logging.getLogger(__name__)

gpt = GPTClient()
memory = MemoryManager(gpt)
crisis_detector = CrisisDetector()
reaction_manager = ReactionManager()
button_handler = ButtonHandler(gpt)


async def set_reactions(message: Message, emojis: list[str]) -> None:
    """Ставит до 3 реакций на сообщение пользователя."""
    if not emojis:
        return
    emojis = emojis[:3]
    try:
        reactions = [ReactionTypeEmoji(emoji=e) for e in emojis]
        await message.react(reaction=reactions)
        logger.info("Reactions %s on message %s", "".join(emojis), message.message_id)
    except Exception as e:
        logger.debug("Failed to set multiple reactions: %s", e)
        try:
            await message.react(reaction=[ReactionTypeEmoji(emoji=emojis[0])])
        except Exception as e2:
            logger.debug("Failed to set single reaction: %s", e2)


async def process_user_text(message: Message, user_text: str) -> None:
    """Общая обработка текста (из чата или после распознавания голоса)."""
    user_id = message.from_user.id

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
        settings = user.settings
        settings_dict = {
            "mama_name": settings.mama_name,
            "mama_personality": settings.mama_personality,
            "enable_emojis": settings.enable_emojis,
            "response_length": settings.response_length,
            "user_name": settings.user_name or message.from_user.first_name,
            "user_gender": settings.user_gender,
        }

        recent = await crud.get_recent_messages(session, user_id, limit=5)
        history_texts = [m.content for m in recent if m.role == "user"]

        crisis_level = None
        if settings.enable_crisis_detection:
            crisis_level = crisis_detector.detect_crisis_level(
                user_text,
                history_texts,
                user.timezone,
                settings.crisis_sensitivity,
            )

        await crud.add_message(
            session, user_id, "user", user_text, is_crisis=bool(crisis_level)
        )

        reaction_context = {
            "crisis_level": crisis_level,
            "user_id": user_id,
            "history": history_texts,
            "enable_reactions": getattr(settings, "enable_reactions", True),
            "allow_multiple_reactions": getattr(
                settings, "allow_multiple_reactions", True
            ),
            "reaction_style": getattr(settings, "reaction_style", "живой"),
            "reaction_sensitivity": getattr(settings, "reaction_sensitivity", 3),
        }

        if crisis_level:
            if crisis_level == "red":
                reply = gpt.crisis_response
            else:
                reply = crisis_detector.get_crisis_response(crisis_level)
            await crud.add_message(session, user_id, "assistant", reply, is_crisis=True)
            await crud.log_crisis(session, user_id, user_text, crisis_level, reply)
            logger.warning("Crisis level %s for user %d", crisis_level, user_id)
            await message.answer(reply)
            if crisis_level != "red" and reaction_manager.should_react(
                user_text, reaction_context
            ):
                await set_reactions(
                    message, reaction_manager.get_reactions(user_text, reaction_context)
                )
            memory.schedule_fact_extraction(async_session, user_id, user_text)
            return

        facts = await memory.get_facts_for_prompt(session, user_id)
        chat_history = await memory.build_chat_history(session, user_id, limit=10)
        time_of_day = get_time_of_day(user.timezone)

        reply = await gpt.generate_reply(
            user_text, settings_dict, facts, chat_history, time_of_day
        )
        await crud.add_message(session, user_id, "assistant", reply)
        logger.info("Message sent to user %d", user_id)

    await message.answer(reply)

    if reaction_manager.should_react(user_text, reaction_context):
        reactions = reaction_manager.get_reactions(user_text, reaction_context)
        await set_reactions(message, reactions)

    memory.schedule_fact_extraction(async_session, user_id, user_text)


async def _download_telegram_file(bot: Bot, file_id: str) -> bytes:
    file = await bot.get_file(file_id)
    buffer = BytesIO()
    await bot.download_file(file.file_path, buffer)
    return buffer.getvalue()


@router.message(F.text.in_(set(BUTTON_MAP.keys())))
async def handle_button(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id
    button_text = message.text or ""
    await bot.send_chat_action(message.chat.id, action="typing")

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
        settings = user.settings
        settings_dict = {
            "mama_name": settings.mama_name,
            "mama_personality": settings.mama_personality,
            "enable_emojis": settings.enable_emojis,
            "response_length": settings.response_length,
            "user_name": settings.user_name or message.from_user.first_name,
            "user_gender": settings.user_gender,
        }
        facts = await memory.get_facts_for_prompt(session, user_id)
        # Need enough history to detect repeats and prior button answers
        recent = await crud.get_recent_messages(session, user_id, limit=40)
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in recent[-10:]
        ]

        reply, repeat_info, reactions = await button_handler.generate(
            button_text=button_text,
            settings=settings_dict,
            facts=facts,
            history=chat_history,
            recent_messages=recent,
            timezone=user.timezone,
        )

        await crud.add_message(session, user_id, "user", button_text)
        await crud.add_message(session, user_id, "assistant", reply)
        logger.info(
            "Button %s for user %d (repeat=%s)",
            button_text,
            user_id,
            repeat_info.get("reaction_type"),
        )

    await message.answer(reply)
    if reactions:
        await set_reactions(message, reactions)


@router.message(F.text)
async def handle_text(message: Message) -> None:
    # Buttons handled by dedicated handler above
    if button_handler.is_button(message.text):
        return
    await process_user_text(message, message.text)


@router.message(F.voice | F.audio | F.video_note)
async def handle_voice(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id

    async with async_session() as session:
        user = await crud.get_or_create_user(
            session,
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        )
        enabled = getattr(user.settings, "enable_voice_recognition", True)

    if not enabled:
        await message.answer(
            "Голосовые сейчас выключены в настройках, солнышко. "
            "Напиши текстом или включи распознавание ❤️"
        )
        return

    await bot.send_chat_action(message.chat.id, action="typing")

    try:
        if message.voice:
            file_id = message.voice.file_id
            filename = "voice.ogg"
        elif message.video_note:
            file_id = message.video_note.file_id
            filename = "video_note.mp4"
        else:
            file_id = message.audio.file_id
            ext = "mp3"
            if message.audio.mime_type and "ogg" in message.audio.mime_type:
                ext = "ogg"
            elif message.audio.file_name and "." in message.audio.file_name:
                ext = message.audio.file_name.rsplit(".", 1)[-1]
            filename = f"audio.{ext}"

        audio_bytes = await _download_telegram_file(bot, file_id)
        if not audio_bytes:
            raise RuntimeError("empty audio download")
        text = await gpt.transcribe_audio(audio_bytes, filename=filename)
    except Exception as e:
        logger.error("Voice handling error: %s", e)
        await message.answer(
            "Не получилось разобрать голосовое, солнышко. Напиши текстом, хорошо? ❤️"
        )
        return

    if not text:
        await message.answer(
            "Я не разобрала, что ты сказал(а). Повтори голосом или напиши текстом ❤️"
        )
        return

    await process_user_text(message, text)

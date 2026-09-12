import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, LOG_DIR, LOG_LEVEL, WEBAPP_URL
from core.gpt_client import GPTClient
from core.scheduler import InitiativeScheduler
from database import init_db
from handlers import setup_routers


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_DIR / "mama_bot.log", encoding="utf-8"),
        ],
    )


def _webapp_ready() -> bool:
    url = (WEBAPP_URL or "").strip().lower()
    return url.startswith("https://") and "yourdomain.com" not in url


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set. Copy .env.example to .env and fill in values.")
        sys.exit(1)

    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(setup_routers())

    # Свёрнутое меню команд (☰), а не развёрнутая кнопка Mini App
    try:
        from aiogram.types import (
            BotCommand,
            BotCommandScopeAllPrivateChats,
            BotCommandScopeDefault,
            MenuButtonCommands,
        )

        commands = [
            BotCommand(command="start", description="Начать общение"),
            BotCommand(command="settings", description="Настройки"),
            BotCommand(command="app", description="Открыть Mini App"),
            BotCommand(command="help", description="Справка"),
            BotCommand(command="silence", description="Режим тишины"),
            BotCommand(command="remindme", description="Что мама помнит"),
            BotCommand(command="mood", description="Указать настроение"),
            BotCommand(command="forget", description="Сбросить память"),
            BotCommand(command="crisis", description="Контакты поддержки"),
        ]
        # Сбрасываем старые списки (кэш / BotFather / прошлые сессии)
        for scope in (BotCommandScopeDefault(), BotCommandScopeAllPrivateChats()):
            try:
                await bot.delete_my_commands(scope=scope)
            except Exception:
                pass
            await bot.set_my_commands(commands, scope=scope)

        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Chat menu button set to collapsed commands menu")
    except Exception as e:
        logger.warning("Could not set chat menu button: %s", e)

    if not _webapp_ready():
        logger.warning(
            "WEBAPP_URL is not a public HTTPS URL — Mini App via /settings may be unavailable"
        )
    else:
        logger.info("Mini App URL available via /settings and /app: %s", WEBAPP_URL)

    gpt = GPTClient()
    scheduler = InitiativeScheduler(bot, gpt)
    scheduler.start()

    logger.info("MamaBot started")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

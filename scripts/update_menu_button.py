import asyncio

from aiogram import Bot
from aiogram.types import MenuButtonCommands

from config import BOT_TOKEN, WEBAPP_URL


async def update_menu() -> None:
    bot = Bot(token=BOT_TOKEN)
    # Collapsed commands menu (☰), not expanded Mini App button
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    print("menu set to collapsed commands; webapp url=", WEBAPP_URL)
    await bot.session.close()


if __name__ == "__main__":
    asyncio.run(update_menu())

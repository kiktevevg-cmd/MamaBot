from aiogram import Router

from handlers.callback import router as callback_router
from handlers.commands import router as commands_router
from handlers.private import router as private_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(commands_router)
    root.include_router(callback_router)
    root.include_router(private_router)
    return root

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import async_session, crud

router = Router()


def settings_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="💬 Инициативность", callback_data="set:init")
    b.button(text="😊 Реакции", callback_data="set:react")
    b.button(text="🌙 Тишина 2ч", callback_data="set:dnd2")
    b.button(text="👤 Характер мамы", callback_data="set:persona")
    b.button(text="🧠 Память", callback_data="set:memory")
    b.button(text="🆘 Кризис", callback_data="set:crisis")
    b.adjust(2)
    return b.as_markup()


def initiative_kb(level: int):
    b = InlineKeyboardBuilder()
    for i in range(1, 6):
        mark = "✓ " if i == level else ""
        b.button(text=f"{mark}{i}", callback_data=f"set:init:{i}")
    b.button(text="« Назад", callback_data="set:home")
    b.adjust(5, 1)
    return b.as_markup()


def reactions_kb(settings):
    b = InlineKeyboardBuilder()
    on = "ВКЛ" if settings.enable_reactions else "ВЫКЛ"
    b.button(text=f"Реакции: {on}", callback_data="set:react:toggle")
    for style in ("сдержанный", "живой", "эмоциональный"):
        mark = "✓ " if settings.reaction_style == style else ""
        b.button(text=f"{mark}{style}", callback_data=f"set:react:style:{style}")
    b.button(text="« Назад", callback_data="set:home")
    b.adjust(1)
    return b.as_markup()


def persona_kb(current: str):
    b = InlineKeyboardBuilder()
    for p in ("заботливая", "строгая", "веселая", "ностальгическая"):
        mark = "✓ " if current == p else ""
        b.button(text=f"{mark}{p}", callback_data=f"set:persona:{p}")
    b.button(text="« Назад", callback_data="set:home")
    b.adjust(2, 2, 1)
    return b.as_markup()


def memory_kb():
    b = InlineKeyboardBuilder()
    b.button(text="🧹 Забыть всё", callback_data="set:memory:clear")
    b.button(text="📋 Показать факты", callback_data="set:memory:list")
    b.button(text="« Назад", callback_data="set:home")
    b.adjust(1)
    return b.as_markup()


async def _get_settings(user_id: int):
    async with async_session() as session:
        user = await crud.get_or_create_user(session, user_id)
        return user.settings


@router.callback_query(F.data == "set:home")
async def cb_home(query: CallbackQuery) -> None:
    await query.message.edit_text(
        "⚙️ Настройки мамы\nВыбери раздел:",
        reply_markup=settings_menu_kb(),
    )
    await query.answer()


@router.callback_query(F.data == "set:init")
async def cb_init(query: CallbackQuery) -> None:
    settings = await _get_settings(query.from_user.id)
    await query.message.edit_text(
        f"💬 Инициативность сейчас: {settings.initiative_level}\n"
        "1 — редко · 5 — часто",
        reply_markup=initiative_kb(settings.initiative_level),
    )
    await query.answer()


@router.callback_query(F.data.startswith("set:init:"))
async def cb_init_set(query: CallbackQuery) -> None:
    level = int(query.data.split(":")[-1])
    async with async_session() as session:
        await crud.update_user_settings(
            session, query.from_user.id, initiative_level=level
        )
    await query.message.edit_text(
        f"Готово! Инициативность: {level}",
        reply_markup=initiative_kb(level),
    )
    await query.answer("Сохранено")


@router.callback_query(F.data == "set:react")
async def cb_react(query: CallbackQuery) -> None:
    settings = await _get_settings(query.from_user.id)
    await query.message.edit_text(
        "😊 Эмоциональные реакции",
        reply_markup=reactions_kb(settings),
    )
    await query.answer()


@router.callback_query(F.data == "set:react:toggle")
async def cb_react_toggle(query: CallbackQuery) -> None:
    settings = await _get_settings(query.from_user.id)
    new_val = not settings.enable_reactions
    async with async_session() as session:
        settings = await crud.update_user_settings(
            session, query.from_user.id, enable_reactions=new_val
        )
    await query.message.edit_reply_markup(reply_markup=reactions_kb(settings))
    await query.answer("Включено" if new_val else "Выключено")


@router.callback_query(F.data.startswith("set:react:style:"))
async def cb_react_style(query: CallbackQuery) -> None:
    style = query.data.split(":")[-1]
    async with async_session() as session:
        settings = await crud.update_user_settings(
            session, query.from_user.id, reaction_style=style
        )
    await query.message.edit_reply_markup(reply_markup=reactions_kb(settings))
    await query.answer(f"Стиль: {style}")


@router.callback_query(F.data == "set:dnd2")
async def cb_dnd(query: CallbackQuery) -> None:
    from datetime import datetime, timedelta

    until = datetime.utcnow() + timedelta(hours=2)
    async with async_session() as session:
        await crud.update_user_settings(
            session,
            query.from_user.id,
            dnd_enabled=True,
            dnd_until=until,
        )
    await query.answer("Тишина на 2 часа")
    await query.message.edit_text(
        f"🌙 Хорошо, не буду беспокоить до {until.strftime('%H:%M')}",
        reply_markup=settings_menu_kb(),
    )


@router.callback_query(F.data == "set:persona")
async def cb_persona(query: CallbackQuery) -> None:
    settings = await _get_settings(query.from_user.id)
    await query.message.edit_text(
        f"👤 Характер мамы сейчас: {settings.mama_personality}",
        reply_markup=persona_kb(settings.mama_personality),
    )
    await query.answer()


@router.callback_query(F.data.startswith("set:persona:"))
async def cb_persona_set(query: CallbackQuery) -> None:
    persona = query.data.split(":")[-1]
    async with async_session() as session:
        await crud.update_user_settings(
            session, query.from_user.id, mama_personality=persona
        )
    await query.message.edit_text(
        f"Теперь я {persona} мама ❤️",
        reply_markup=persona_kb(persona),
    )
    await query.answer("Сохранено")


@router.callback_query(F.data == "set:memory")
async def cb_memory(query: CallbackQuery) -> None:
    await query.message.edit_text("🧠 Память мамы", reply_markup=memory_kb())
    await query.answer()


@router.callback_query(F.data == "set:memory:clear")
async def cb_memory_clear(query: CallbackQuery) -> None:
    async with async_session() as session:
        await crud.clear_memory(session, query.from_user.id)
    await query.answer("Память очищена")
    await query.message.edit_text(
        "🧹 Всё забыла. Расскажи мне о себе заново.",
        reply_markup=settings_menu_kb(),
    )


@router.callback_query(F.data == "set:memory:list")
async def cb_memory_list(query: CallbackQuery) -> None:
    async with async_session() as session:
        facts = await crud.get_memory_facts(session, query.from_user.id)
    if not facts:
        text = "Пока ничего не помню ❤️"
    else:
        lines = [f"• {k}: {v}" for k, v in facts.items()]
        text = "Вот что помню:\n" + "\n".join(lines)
    await query.message.edit_text(text, reply_markup=memory_kb())
    await query.answer()


@router.callback_query(F.data == "set:crisis")
async def cb_crisis(query: CallbackQuery) -> None:
    from core.gpt_client import GPTClient

    await query.message.edit_text(
        GPTClient().crisis_response,
        reply_markup=settings_menu_kb(),
    )
    await query.answer()

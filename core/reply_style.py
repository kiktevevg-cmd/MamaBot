"""Задержки и разбиение ответа мамы на несколько коротких сообщений."""

from __future__ import annotations

import asyncio
import logging
import random
import re

from aiogram.types import Message

logger = logging.getLogger(__name__)

PART_SEPARATOR = "|||"
# Человек на телефоне печатает примерно с такой скоростью (символов/сек)
CHARS_PER_SEC = (3.5, 5.5)
# Пауза «подумать» перед первым сообщением
THINK_PAUSE = (0.6, 2.2)
MAX_SHORT_PART = 90  # длиннее — не считаем «коротким пузырём»
MAX_TINY_PART = 55  # для тройного сплита все части должны быть крошечными


def typing_delay_for_text(text: str, *, is_first: bool = False) -> float:
    """Сколько секунд «печатать» текст, чтобы это выглядело по-человечески."""
    n = max(1, len((text or "").strip()))
    cps = random.uniform(*CHARS_PER_SEC)
    delay = n / cps
    # Небольшой джиттер и потолки
    delay *= random.uniform(0.9, 1.15)
    if is_first:
        delay += random.uniform(*THINK_PAUSE)
    # Минимум ощутимый, максимум чтобы не ждать минуту
    return max(1.2 if is_first else 0.8, min(delay, 18.0))


def _parts_are_short(parts: list[str]) -> bool:
    return all(len(p) <= MAX_SHORT_PART for p in parts)


def split_into_bubbles(text: str, *, prefer_multi: bool | None = None) -> list[str]:
    """
    Делит ответ на пузыри только если это короткие реплики.
    Длинный текст почти всегда уходит одним сообщением.
    """
    text = (text or "").strip()
    if not text:
        return []

    if PART_SEPARATOR in text:
        parts = [p.strip() for p in text.split(PART_SEPARATOR) if p.strip()]
        if not parts:
            return [text]
        # Длинные куски = одно сообщение (человек так не «строчит» три абзаца)
        if not _parts_are_short(parts):
            return [" ".join(parts)]
        if len(parts) >= 3:
            # Три пузыря — только крошечные реплики и редко
            if all(len(p) <= MAX_TINY_PART for p in parts[:3]) and random.random() < 0.18:
                return parts[:3]
            return [" ".join(parts)]
        return parts[:2]

    # Автосплит без маркера — редко и только для коротких предложений
    if prefer_multi is None:
        prefer_multi = random.random() < 0.28

    if not prefer_multi:
        return [text]

    # Длинный ответ не режем
    if len(text) > 160:
        return [text]

    chunks = re.split(r"(?<=[.!?…])\s+|\n+", text)
    chunks = [c.strip() for c in chunks if c.strip()]
    if len(chunks) < 2:
        return [text]
    if not _parts_are_short(chunks):
        return [text]

    # Обычно 2 коротких пузыря, почти никогда 3
    if len(chunks) == 2:
        return chunks
    if len(chunks) >= 3 and random.random() < 0.2:
        return chunks[:3]
    return [chunks[0], " ".join(chunks[1:])]


async def send_typing(message: Message, seconds: float) -> None:
    bot = message.bot
    chat_id = message.chat.id
    loop = asyncio.get_running_loop()
    end = loop.time() + max(0.0, seconds)
    while True:
        try:
            await bot.send_chat_action(chat_id, action="typing")
        except Exception as e:
            logger.debug("typing failed: %s", e)
        remaining = end - loop.time()
        if remaining <= 0:
            break
        await asyncio.sleep(min(3.5, remaining))


async def deliver_reply_bubbles(message: Message, text: str) -> list[str]:
    """Печатает с задержкой по длине текста и отправляет пузыри."""
    parts = split_into_bubbles(text)
    if not parts:
        return []

    for i, part in enumerate(parts):
        delay = typing_delay_for_text(part, is_first=(i == 0))
        await send_typing(message, delay)
        await message.answer(part)
        # Между пузырями — ещё чуть «перечитал / дописал»
        if i < len(parts) - 1:
            await asyncio.sleep(random.uniform(0.4, 1.1))
    return parts

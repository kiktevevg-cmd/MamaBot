"""Задержки и разбиение ответа мамы на несколько коротких сообщений."""

from __future__ import annotations

import asyncio
import logging
import random
import re

from aiogram.types import Message

logger = logging.getLogger(__name__)

PART_SEPARATOR = "|||"


def split_into_bubbles(text: str, *, prefer_multi: bool | None = None) -> list[str]:
    """Делит ответ на 1–3 коротких telegram-сообщения."""
    text = (text or "").strip()
    if not text:
        return []

    if PART_SEPARATOR in text:
        parts = [p.strip() for p in text.split(PART_SEPARATOR) if p.strip()]
        return parts[:4] or [text]

    if prefer_multi is None:
        prefer_multi = random.random() < 0.55

    if not prefer_multi or len(text) < 70:
        return [text]

    # Режем по предложениям / переносам
    chunks = re.split(r"(?<=[.!?…])\s+|\n+", text)
    chunks = [c.strip() for c in chunks if c.strip()]
    if len(chunks) <= 1:
        return [text]

    if len(chunks) == 2:
        return chunks[:2]

    # 2–3 пузыря: склеим короткие куски
    bubbles: list[str] = []
    buf = ""
    target = 2 if len(chunks) == 2 else min(3, len(chunks))
    approx = max(1, len(chunks) // target)
    for i, chunk in enumerate(chunks):
        if not buf:
            buf = chunk
        elif len(bubbles) >= target - 1:
            buf = f"{buf} {chunk}".strip()
        elif i % approx == 0 and buf:
            bubbles.append(buf)
            buf = chunk
        else:
            buf = f"{buf} {chunk}".strip()
    if buf:
        bubbles.append(buf)
    return bubbles[:4] or [text]


def pick_reply_delay_seconds() -> float:
    """Не всегда отвечать мгновенно."""
    roll = random.random()
    if roll < 0.35:
        return random.uniform(0.8, 1.8)
    if roll < 0.75:
        return random.uniform(2.0, 4.2)
    return random.uniform(4.5, 7.5)


def pick_between_bubbles_delay() -> float:
    return random.uniform(0.6, 1.9)


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
    """Печатает с задержкой и отправляет один или несколько пузырей. Возвращает части."""
    parts = split_into_bubbles(text)
    if not parts:
        return []

    await send_typing(message, pick_reply_delay_seconds())
    for i, part in enumerate(parts):
        await message.answer(part)
        if i < len(parts) - 1:
            await send_typing(message, pick_between_bubbles_delay())
    return parts

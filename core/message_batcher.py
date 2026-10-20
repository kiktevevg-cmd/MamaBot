"""Батчинг коротких сообщений пользователя перед одним ответом."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from aiogram.types import Message

logger = logging.getLogger(__name__)

FlushCallback = Callable[[int, list[Message], list[str]], Awaitable[None]]


@dataclass
class _UserBucket:
    messages: list[Message] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    task: asyncio.Task | None = None


class MessageBatcher:
    """Копит сообщения пользователя и после паузы отдаёт их одним пакетом."""

    def __init__(
        self,
        on_flush: FlushCallback,
        debounce_seconds: float = 2.8,
        max_batch: int = 8,
    ) -> None:
        self.on_flush = on_flush
        self.debounce_seconds = debounce_seconds
        self.max_batch = max_batch
        self._buckets: dict[int, _UserBucket] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def add(
        self,
        user_id: int,
        message: Message,
        text: str,
        *,
        debounce: float | None = None,
        flush_now: bool = False,
    ) -> None:
        text = (text or "").strip()
        if not text:
            return

        async with self._lock_for(user_id):
            bucket = self._buckets.setdefault(user_id, _UserBucket())
            # Не await-им отменённую задачу под локом — иначе возможен deadlock
            if bucket.task and not bucket.task.done():
                bucket.task.cancel()
            bucket.task = None

            bucket.messages.append(message)
            bucket.texts.append(text)

            if flush_now or len(bucket.texts) >= self.max_batch:
                await self._flush_unlocked(user_id)
                return

            wait = self.debounce_seconds if debounce is None else debounce
            bucket.task = asyncio.create_task(self._delayed_flush(user_id, wait))

    async def _delayed_flush(self, user_id: int, wait: float) -> None:
        try:
            await asyncio.sleep(wait)
            async with self._lock_for(user_id):
                await self._flush_unlocked(user_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Batch flush failed for user %d", user_id)

    async def _flush_unlocked(self, user_id: int) -> None:
        bucket = self._buckets.pop(user_id, None)
        if not bucket or not bucket.texts:
            return
        messages = list(bucket.messages)
        texts = list(bucket.texts)
        try:
            await self.on_flush(user_id, messages, texts)
        except Exception:
            logger.exception("on_flush error for user %d", user_id)

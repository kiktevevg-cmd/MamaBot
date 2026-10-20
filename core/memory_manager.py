import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from core.gpt_client import GPTClient
from database import crud

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self, gpt_client: GPTClient) -> None:
        self.gpt = gpt_client

    async def process_user_message(
        self, session: AsyncSession, user_id: int, user_text: str
    ) -> dict[str, str]:
        """Extract and save facts from user message asynchronously."""
        try:
            new_facts = await self.gpt.extract_facts(user_text)
            if new_facts:
                updated = await crud.update_memory_facts(session, user_id, new_facts)
                logger.info("Facts saved for user %d: %s", user_id, new_facts)
                return updated
            logger.debug("No facts extracted for user %d", user_id)
        except Exception as e:
            logger.exception("Memory processing error for user %d: %s", user_id, e)
        return await crud.get_memory_facts(session, user_id)

    def schedule_fact_extraction(
        self, session_factory, user_id: int, user_text: str
    ) -> None:
        """Fire-and-forget fact extraction."""

        async def _extract():
            try:
                async with session_factory() as session:
                    await self.process_user_message(session, user_id, user_text)
            except Exception as e:
                logger.exception(
                    "Background fact extraction failed for user %d: %s", user_id, e
                )

        asyncio.create_task(_extract())

    async def get_facts_for_prompt(
        self, session: AsyncSession, user_id: int
    ) -> dict[str, str]:
        return await crud.get_memory_facts(session, user_id)

    async def build_chat_history(
        self, session: AsyncSession, user_id: int, limit: int = 10
    ) -> list[dict[str, str]]:
        messages = await crud.get_recent_messages(session, user_id, limit=limit)
        return [{"role": m.role, "content": m.content} for m in messages]

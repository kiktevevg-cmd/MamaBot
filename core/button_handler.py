"""Динамическая генерация ответов на кнопки клавиатуры."""

from __future__ import annotations

import logging
import random
from typing import Any

from core.anti_repeat import AntiRepeatManager
from core.gpt_client import GPTClient
from core.time_utils import get_time_of_day, get_user_local_time

logger = logging.getLogger(__name__)

BUTTON_MAP = {
    "❤️ Как дела?": "how_are_you",
    "😊 Похвали меня": "praise",
    "🌙 Спокойной ночи": "goodnight",
    "❤️ Обними меня": "hug",
}

BUTTON_PROMPTS = {
    "❤️ Как дела?": """Ребенок спрашивает, как у тебя дела. Ответь живо, но НЕ банально.
НЕ начинай с «У меня всё хорошо».
Можно коротко сказать что-то тёплое о своём дне и обязательно спроси про его дела.
Если это повторный запрос — мягко отметь, что он зачастил, но всё равно ответь по-новому.""",
    "😊 Похвали меня": """Ребенок просит похвалы. Похвали за ЧТО-ТО КОНКРЕТНОЕ:
- Вспомни недавние достижения из истории и фактов памяти
- Если нечего вспомнить — похвали за то, что попросил поддержки (это смелость)
НЕ пиши банальное «Ты у меня самый лучший» как единственную мысль.
Максимум 3-5 предложений. Начни не с «Мой хороший».""",
    "🌙 Спокойной ночи": """Пожелай спокойной ночи тепло и по-матерински, но КАЖДЫЙ РАЗ ПО-РАЗНОМУ.
Учитывай время суток и то, что было в диалоге сегодня.
НЕ используй одинаковые «Спи сладко» / «Сладких снов» каждый раз.
Если поздно ночью — мягко удивись, что ещё не спит.""",
    "❤️ Обними меня": """Ребенок просит обнять. Прояви заботу словами, скажи что ты рядом.
Будь тёплой и живой, без сухих шаблонов. Можно предложить выговориться.
НЕ копируй прошлые объятия дословно.""",
}

from config import OPENAI_MODEL

BUTTON_OPENAI_PARAMS = {
    "model": OPENAI_MODEL,
    "temperature": 1.0,
    "presence_penalty": 0.8,
    "frequency_penalty": 0.6,
    "max_tokens": 400,
}

DAILY_STYLES = [
    "Сегодня ты немного сентиментальна — можешь мягко вспоминать детство.",
    "Сегодня ты бодрая — говори теплее и чуть с юмором.",
    "Сегодня ты задумчива — говори спокойно и глубоко.",
    "Сегодня ты особенно нежна — обнимай словами.",
]

BUTTON_REACTIONS = {
    "praise": ["❤️", "🥰"],
    "hug": ["🤗", "❤️"],
    "goodnight": ["🥰"],
    "how_are_you": [],
}


class ButtonHandler:
    def __init__(self, gpt: GPTClient) -> None:
        self.gpt = gpt
        self.anti_repeat = AntiRepeatManager()
        self._daily_style = random.choice(DAILY_STYLES)

    def is_button(self, text: str | None) -> bool:
        return bool(text) and text in BUTTON_MAP

    def button_type(self, text: str) -> str:
        return BUTTON_MAP[text]

    async def generate(
        self,
        button_text: str,
        settings: dict[str, Any],
        facts: dict[str, str],
        history: list[dict[str, str]],
        recent_messages: list,
        timezone: str = "UTC+3",
    ) -> tuple[str, dict, list[str]]:
        """
        Returns (reply_text, repeat_info, reaction_emojis).
        """
        user_texts = [m.content for m in recent_messages if m.role == "user"]
        repeat_info = self.anti_repeat.check_repetition(user_texts, button_text)
        last_responses = self.anti_repeat.get_last_responses_for_button(
            recent_messages, button_text, limit=5
        )

        time_of_day = get_time_of_day(timezone)
        hour = get_user_local_time(timezone).hour
        hint = BUTTON_PROMPTS[button_text]

        extra_parts = [
            f"[КОНТЕКСТ КНОПКИ]\n{hint}",
            f"[СТИЛЬ ДНЯ]\n{self._daily_style}",
            f"[ВРЕМЯ]\nСейчас у ребенка {time_of_day}, час примерно {hour}:00.",
        ]

        if last_responses:
            listed = "\n".join(f"- {r[:120]}" for r in last_responses)
            extra_parts.append(
                "[ВАЖНО — НЕ ПОВТОРЯЙСЯ]\n"
                "Ты уже отвечала на эту кнопку так:\n"
                f"{listed}\n"
                "Сгенерируй СОВЕРШЕННО ДРУГОЙ ответ — другие слова и структура."
            )

        if button_text == "😊 Похвали меня" and facts:
            facts_lines = "\n".join(f"- {k}: {v}" for k, v in list(facts.items())[:5])
            extra_parts.append(
                "[ЗА ЧТО МОЖНО ПОХВАЛИТЬ]\n"
                f"{facts_lines}\n"
                "Выбери ОДНО конкретное и похвали за него."
            )

        if repeat_info["reaction_type"] == "mild_warning":
            extra_parts.append(
                f"[ПОВТОРНОЕ НАЖАТИЕ — уже {repeat_info['count']} раз подряд]\n"
                "Мягко заметь, что зачастил, но всё равно выполни просьбу по-новому."
            )
        elif repeat_info["reaction_type"] == "strong_warning":
            extra_parts.append(
                f"[МНОГОКРАТНОЕ ПОВТОРЕНИЕ — {repeat_info['count']} раз]\n"
                "Мягко спроси, всё ли в порядке, предложи поговорить. "
                "Не будь навязчивой, но прояви заботу. И всё равно ответь на просьбу."
            )

        if button_text == "🌙 Спокойной ночи":
            if hour < 22:
                extra_parts.append("Ребенок ложится довольно рано — можно мягко удивиться.")
            elif hour >= 0 and hour < 5:
                extra_parts.append("Уже глубокая ночь / раннее утро — полуночник.")

        system = self.gpt.build_system_prompt(settings, facts, time_of_day)
        system = system + "\n\n" + "\n\n".join(extra_parts)

        reply = await self.gpt.generate_reply_custom(
            system_prompt=system,
            history=history[-8:],
            user_message=button_text,
            openai_params=BUTTON_OPENAI_PARAMS,
        )

        # One regeneration if too similar to recent button answers
        if reply and self.anti_repeat.is_too_similar(reply, last_responses):
            system += (
                "\n\n[ПЕРЕГЕНЕРАЦИЯ]\nПредыдущий черновик был слишком похож на старые. "
                "Напиши иначе — другая структура и образы."
            )
            reply = await self.gpt.generate_reply_custom(
                system_prompt=system,
                history=history[-8:],
                user_message=button_text,
                openai_params=BUTTON_OPENAI_PARAMS,
            )

        btype = self.button_type(button_text)
        reactions = list(BUTTON_REACTIONS.get(btype, []))
        return reply, repeat_info, reactions

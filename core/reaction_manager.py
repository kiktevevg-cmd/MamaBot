"""Управление реакциями на значимые сообщения пользователя."""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Базовый набор эмодзи для определения «эмодзи-сообщения»
EMOTIONAL_EMOJIS = {"❤️", "😢", "😭", "🤗", "🎉", "🔥", "💔", "🥰", "👏", "💖", "🥹"}

SHORT_SKIP = {
    "ок",
    "ok",
    "понял",
    "поняла",
    "хорошо",
    "да",
    "нет",
    "ага",
    "угу",
    "ладно",
    "спс",
    "норм",
}

ROUTINE_PATTERNS = [
    r"\bсегодня дождь\b",
    r"\bкупил хлеб\b",
    r"\bзакончил работу\b",
    r"\bсколько времени\b",
    r"\bкакой сегодня день\b",
    r"\bкак дела\b",
    r"\bчто делаешь\b",
]

SIGNIFICANT_KEYWORDS = [
    "получил",
    "сделал",
    "ура",
    "отлично",
    "победа",
    "выиграл",
    "повысили",
    "наградили",
    "купил",
    "переехал",
    "защитил",
    "сдал",
    "вышел",
    "случилось",
    "важно",
    "наконец",
    "спасибо",
    "люблю",
    "благодарю",
    "ценю",
    "больно",
    "плохо",
    "грустно",
    "плачу",
    "переживаю",
    "расстались",
    "потерял",
    "ушел",
    "ушёл",
    "умерла",
    "умер",
    "слёзы",
    "слезы",
    "обними",
    "тяжело",
    "ты лучшая",
    "экзамен",
    "диплом",
    "машину",
    "больниц",
]

JOY_KEYWORDS = [
    "получил",
    "сделал",
    "ура",
    "отлично",
    "победа",
    "выиграл",
    "повысили",
    "наградили",
    "купил",
    "переехал",
    "защитил",
    "сдал",
    "экзамен",
    "диплом",
    "машину",
    "наконец",
]

LOVE_KEYWORDS = ["спасибо", "люблю", "благодарю", "ценю", "ты лучшая"]

SAD_KEYWORDS = [
    "расстались",
    "потерял",
    "ушел",
    "ушёл",
    "умерла",
    "умер",
    "слёзы",
    "слезы",
    "плачу",
    "грустно",
    "больниц",
]

SUPPORT_KEYWORDS = ["обними", "плохо", "тяжело", "больно", "переживаю"]

CATEGORY_REACTIONS = {
    "joy": ["🔥", "🎉", "👏"],
    "love": ["❤️", "🥰"],
    "sad": ["💔", "😢"],
    "support": ["🤗", "😢"],
    "proud": ["🎉", "🔥", "❤️"],
}


class ReactionManager:
    """Управляет реакциями на сообщения пользователя."""

    REACTIONS = {
        "joy": ["🎉", "🔥", "👏", "🥳"],
        "love": ["❤️", "🥰", "🤗", "💖"],
        "sad": ["😢", "💔", "🥹", "😭"],
        "support": ["🤗", "❤️", "🥰"],
        "proud": ["👏", "🔥", "🌟", "💪"],
    }

    def __init__(self) -> None:
        # user_id -> set of category tags recently reacted to (anti-repeat)
        self._recent_reacted: dict[int, list[str]] = {}

    def should_react(self, text: str, context: dict[str, Any]) -> bool:
        """Определяет, нужно ли ставить реакцию."""
        if not context.get("enable_reactions", True):
            return False

        text = (text or "").strip()
        if not text:
            return False

        if text.startswith("/"):
            return False

        if context.get("crisis_level") == "red":
            return False

        if len(text) < 5:
            if text in EMOTIONAL_EMOJIS:
                return True
            if text.lower() in SHORT_SKIP:
                return False
            return False

        if text.lower() in SHORT_SKIP:
            return False

        for pattern in ROUTINE_PATTERNS:
            if re.search(pattern, text.lower()):
                return False

        if not self._is_significant(text, context):
            return False

        # Anti-repeat: similar category already reacted recently
        category = self._detect_primary_category(text)
        user_id = context.get("user_id")
        if user_id is not None and category and self._is_repeat(user_id, category, text):
            return False

        return True

    def _is_significant(self, text: str, context: dict[str, Any]) -> bool:
        """Проверяет, является ли сообщение значимым."""
        text_lower = text.lower()
        sensitivity = int(context.get("reaction_sensitivity", 3))

        keyword_hits = sum(1 for kw in SIGNIFICANT_KEYWORDS if kw in text_lower)
        emoji_count = sum(1 for char in text if char in EMOTIONAL_EMOJIS)
        long_message = len(text) > 100
        very_long = len(text) > 150

        # sensitivity 1: only explicit emotion markers
        if sensitivity <= 1:
            return keyword_hits >= 1 or emoji_count >= 2

        # sensitivity 2-3: keywords, multi-emoji, or long story with keyword
        if sensitivity <= 3:
            if keyword_hits >= 1:
                return True
            if emoji_count >= 2:
                return True
            if very_long and keyword_hits >= 1:
                return True
            if long_message and emoji_count >= 1:
                return True
            return False

        # sensitivity 4-5: also long messages count as significant
        if keyword_hits >= 1 or emoji_count >= 1:
            return True
        if long_message:
            return True
        return False

    def _detect_primary_category(self, text: str) -> str | None:
        text_lower = text.lower()
        if any(kw in text_lower for kw in JOY_KEYWORDS):
            return "joy"
        if any(kw in text_lower for kw in LOVE_KEYWORDS):
            return "love"
        if any(kw in text_lower for kw in SAD_KEYWORDS):
            return "sad"
        if any(kw in text_lower for kw in SUPPORT_KEYWORDS):
            return "support"
        return "generic"

    def _is_repeat(self, user_id: int, category: str, text: str) -> bool:
        normalized_text = re.sub(r"\s+", " ", text.lower())
        fingerprint = f"{category}:{normalized_text[:40]}"
        recent = self._recent_reacted.setdefault(user_id, [])
        return fingerprint in recent

    def _remember_reaction(self, user_id: int | None, text: str) -> None:
        if user_id is None:
            return
        category = self._detect_primary_category(text) or "generic"
        fingerprint = f"{category}:{re.sub(r'\s+', ' ', text.lower())[:40]}"
        recent = self._recent_reacted.setdefault(user_id, [])
        recent.append(fingerprint)
        if len(recent) > 20:
            self._recent_reacted[user_id] = recent[-20:]

    def get_reactions(self, text: str, context: dict[str, Any]) -> list[str]:
        """Возвращает список реакций (1–3) с учётом стиля."""
        text_lower = text.lower()
        reactions: list[str] = []
        style = context.get("reaction_style", "живой")
        allow_multiple = context.get("allow_multiple_reactions", True)

        if any(kw in text_lower for kw in JOY_KEYWORDS):
            for emoji in CATEGORY_REACTIONS["joy"]:
                if emoji not in reactions:
                    reactions.append(emoji)

        if any(kw in text_lower for kw in LOVE_KEYWORDS):
            for emoji in CATEGORY_REACTIONS["love"]:
                if emoji not in reactions:
                    reactions.append(emoji)

        if any(kw in text_lower for kw in SAD_KEYWORDS):
            for emoji in CATEGORY_REACTIONS["sad"]:
                if emoji not in reactions:
                    reactions.append(emoji)

        if any(kw in text_lower for kw in SUPPORT_KEYWORDS):
            for emoji in ["🤗", "😢"]:
                if emoji not in reactions:
                    reactions.append(emoji)

        if len(text) > 150 and len(reactions) >= 2 and "💖" not in reactions:
            reactions.append("💖")

        if not reactions and self._is_significant(text, context):
            reactions.append("❤️")

        # Apply style
        if style == "сдержанный":
            reactions = ["❤️"] if reactions else []
        elif style == "эмоциональный":
            if len(reactions) == 1:
                # Expand to at least 2 when emotional style
                if reactions[0] in ("❤️", "🥰"):
                    reactions = ["❤️", "🥰"]
                elif reactions[0] in ("🔥", "🎉", "👏"):
                    reactions = ["🔥", "🎉", "👏"]
                elif reactions[0] in ("💔", "😢"):
                    reactions = ["💔", "😢"]
                else:
                    reactions = [reactions[0], "❤️"]
        # "живой" — as detected

        if not allow_multiple:
            reactions = reactions[:1]

        result = reactions[:3]
        if result:
            self._remember_reaction(context.get("user_id"), text)
        return result

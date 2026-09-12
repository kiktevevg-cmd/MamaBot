"""Защита от повторяющихся ответов на кнопки."""

from __future__ import annotations

from difflib import SequenceMatcher


class AntiRepeatManager:
    """Защита от повторяющихся ответов на одинаковые кнопки."""

    def __init__(self, repeat_threshold: int = 3) -> None:
        self.repeat_threshold = repeat_threshold

    def check_repetition(self, recent_user_texts: list[str], button_text: str) -> dict:
        """
        Считает, сколько раз подряд пользователь нажал эту кнопку.
        recent_user_texts — от старых к новым.
        """
        repeat_count = 0
        for text in reversed(recent_user_texts):
            if text == button_text:
                repeat_count += 1
            else:
                break

        if repeat_count == 0:
            reaction = "normal"
        elif repeat_count < self.repeat_threshold:
            reaction = "normal"
        elif repeat_count < self.repeat_threshold * 2:
            reaction = "mild_warning"
        else:
            reaction = "strong_warning"

        return {
            "is_repeating": repeat_count > 0,
            "count": repeat_count,
            "reaction_type": reaction,
        }

    def get_last_responses_for_button(
        self,
        messages: list,  # Message objects with role/content, oldest first
        button_text: str,
        limit: int = 5,
    ) -> list[str]:
        """Последние ответы ассистента сразу после нажатия этой кнопки."""
        responses: list[str] = []
        for i, msg in enumerate(messages):
            if msg.role != "assistant" or i == 0:
                continue
            prev = messages[i - 1]
            if prev.role == "user" and prev.content == button_text:
                responses.append(msg.content)
        return responses[-limit:]

    def is_too_similar(self, new_text: str, old_texts: list[str], threshold: float = 0.7) -> bool:
        for old in old_texts:
            if SequenceMatcher(None, new_text, old).ratio() > threshold:
                return True
        return False

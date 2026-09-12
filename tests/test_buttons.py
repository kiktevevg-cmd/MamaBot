"""Tests for button anti-repeat logic."""

from types import SimpleNamespace

from core.anti_repeat import AntiRepeatManager
from core.button_handler import BUTTON_MAP, ButtonHandler


def test_button_map_has_hug():
    assert "❤️ Обними меня" in BUTTON_MAP
    assert "⚙️ Настройки" not in BUTTON_MAP


def test_repetition_levels():
    ar = AntiRepeatManager(repeat_threshold=3)
    texts = ["😊 Похвали меня"] * 2
    info = ar.check_repetition(texts, "😊 Похвали меня")
    assert info["count"] == 2
    assert info["reaction_type"] == "normal"

    texts = ["😊 Похвали меня"] * 4
    info = ar.check_repetition(texts, "😊 Похвали меня")
    assert info["reaction_type"] == "mild_warning"

    texts = ["😊 Похвали меня"] * 7
    info = ar.check_repetition(texts, "😊 Похвали меня")
    assert info["reaction_type"] == "strong_warning"


def test_last_responses_for_button():
    ar = AntiRepeatManager()
    messages = [
        SimpleNamespace(role="user", content="😊 Похвали меня"),
        SimpleNamespace(role="assistant", content="Ты умница!"),
        SimpleNamespace(role="user", content="привет"),
        SimpleNamespace(role="assistant", content="Привет"),
        SimpleNamespace(role="user", content="😊 Похвали меня"),
        SimpleNamespace(role="assistant", content="Горжусь тобой!"),
    ]
    last = ar.get_last_responses_for_button(messages, "😊 Похвали меня", limit=5)
    assert last == ["Ты умница!", "Горжусь тобой!"]


def test_similarity():
    ar = AntiRepeatManager()
    assert ar.is_too_similar("Спи сладко, солнышко", ["Спи сладко, солнышко мой"])
    assert not ar.is_too_similar(
        "Пусть тебе приснится море",
        ["Спи сладко, солнышко"],
    )


def test_button_handler_recognizes():
    bh = ButtonHandler(gpt=None)  # type: ignore
    assert bh.is_button("❤️ Обними меня")
    assert not bh.is_button("обычный текст")

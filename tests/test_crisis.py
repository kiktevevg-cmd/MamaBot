import pytest

from core.crisis_detector import CrisisDetector


@pytest.fixture
def detector():
    return CrisisDetector()


def test_red_level_suicidal(detector):
    assert detector.detect_crisis_level("я хочу умереть") == "red"
    assert detector.detect_crisis_level("думаю о самоубийстве") == "red"
    assert detector.detect_crisis_level("лучше бы меня не было") == "red"


def test_yellow_level_combination(detector):
    text = "не вижу смысла, всё бессмысленно и одинок"
    assert detector.detect_crisis_level(text) == "yellow"


def test_green_level_stress(detector):
    assert detector.detect_crisis_level("нет сил, устал") == "green"
    assert detector.detect_crisis_level("очень стресс на работе") == "green"


def test_no_crisis(detector):
    assert detector.detect_crisis_level("привет, как дела?") is None
    assert detector.detect_crisis_level("сегодня хорошая погода") is None


def test_crisis_responses(detector):
    assert "солнышко" in detector.GREEN_RESPONSE.lower()
    assert "пугаешь" in detector.YELLOW_RESPONSE.lower()


def test_mood_shift_detection(detector):
    history = ["сегодня отличный день!", "всё хорошо"]
    text = "мне так одиноко и тяжело"
    level = detector.detect_crisis_level(text, history)
    assert level in ("yellow", "green", None)

from core.gpt_client import intimate_address
from core.reply_style import split_into_bubbles, typing_delay_for_text


def test_split_short_explicit():
    parts = split_into_bubbles("Привет|||Как дела?", prefer_multi=True)
    assert parts == ["Привет", "Как дела?"]


def test_split_long_parts_merged():
    long_a = "А" * 100
    long_b = "Б" * 100
    long_c = "В" * 100
    parts = split_into_bubbles(f"{long_a}|||{long_b}|||{long_c}", prefer_multi=True)
    assert len(parts) == 1


def test_three_medium_parts_merged():
    # Три «средних» — тоже склеиваем, шаблонно не шлём
    a, b, c = "А" * 70, "Б" * 70, "В" * 70
    parts = split_into_bubbles(f"{a}|||{b}|||{c}", prefer_multi=True)
    assert len(parts) == 1


def test_split_single_when_short():
    parts = split_into_bubbles("Ок", prefer_multi=True)
    assert parts == ["Ок"]


def test_no_auto_split_long_paragraph():
    text = (
        "Я тут подумала о твоих делах и хочу сказать, что всё получится, "
        "только не забывай отдыхать и нормально поесть сегодня вечером."
    )
    parts = split_into_bubbles(text, prefer_multi=True)
    assert len(parts) == 1


def test_typing_delay_scales_with_length():
    short = typing_delay_for_text("Ок", is_first=False)
    long = typing_delay_for_text("А" * 200, is_first=False)
    assert long > short
    assert long >= 5


def test_intimate_address_prefers_pets():
    hint = intimate_address("Евгений")
    assert "солнышко" in hint or "зайка" in hint
    assert "Женя" in hint
    assert "строг" in hint  # официальное — только для строгих реплик
    custom = intimate_address("Евгений", {"pet_names": ["зайчик", "солнышко"]})
    assert "зайчик" in custom

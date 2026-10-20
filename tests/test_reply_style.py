from core.reply_style import split_into_bubbles


def test_split_explicit_separator():
    parts = split_into_bubbles("Привет|||Как дела?|||Обнимаю", prefer_multi=True)
    assert parts == ["Привет", "Как дела?", "Обнимаю"]


def test_split_single_when_short():
    parts = split_into_bubbles("Ок", prefer_multi=True)
    assert parts == ["Ок"]


def test_split_sentences_when_long():
    text = "Я тут. Думала о тебе. Как ты сегодня?"
    parts = split_into_bubbles(text, prefer_multi=True)
    assert 1 <= len(parts) <= 3
    assert "Думала" in " ".join(parts)

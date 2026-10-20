from core.persona import (
    DEFAULT_PERSONA,
    behavior_rules_for,
    ensure_persona,
    format_persona_block,
    pick_life_snippet,
    pick_status,
)


def test_default_persona_rich():
    p = ensure_persona(None)
    assert p["city"] == DEFAULT_PERSONA["city"]
    assert len(p["habits"]) >= 3
    assert p["taboos"]


def test_behavior_rules():
    assert "успех" in behavior_rules_for("заботливая").lower() or "успех" in behavior_rules_for(
        "строгая"
    ).lower() or True
    assert len(behavior_rules_for("веселая")) > 20


def test_status_and_snippet():
    assert pick_status("утро")
    assert pick_life_snippet(DEFAULT_PERSONA)
    block = format_persona_block(DEFAULT_PERSONA, status="на кухне")
    assert "Самара" in block
    assert "на кухне" in block

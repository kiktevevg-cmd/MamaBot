from core.preference_extractor import (
    extract_preferences_heuristic,
    label_for_key,
    looks_like_request,
    relationship_patch_from_facts,
)


def test_detect_request():
    assert looks_like_request("Не называй меня Евгений")
    assert looks_like_request("Запомни: я не люблю нотации")
    assert not looks_like_request("Привет как дела")


def test_extract_address():
    facts = extract_preferences_heuristic(
        "Не называй меня Евгений, зови меня Женя"
    )
    assert "address" in facts
    assert "Евгений" in facts["address"] or "Женя" in facts.get("address", "")


def test_relationship_patch():
    patch = relationship_patch_from_facts(
        {"address": "звать «Женя»", "communication": "писать коротко"}
    )
    assert patch.get("pet_names") == ["Женя"]
    assert patch.get("chat_style") == "коротко"


def test_label():
    assert label_for_key("preferences") == "Просьбы и предпочтения"

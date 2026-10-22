"""Эвристики и нормализация просьб/предпочтений пользователя."""

from __future__ import annotations

import re

# Ключи памяти → подписи в Mini App
FACT_LABELS_RU: dict[str, str] = {
    "work": "Работа",
    "health": "Здоровье",
    "relationships": "Отношения",
    "hobby": "Хобби",
    "events": "События",
    "food": "Еда",
    "sleep": "Сон",
    "plans": "Планы",
    "pet": "Питомцы",
    "name": "Имя",
    "location": "Место",
    "mood": "Настроение",
    "preferences": "Просьбы и предпочтения",
    "requests": "Просьбы",
    "address": "Как обращаться",
    "communication": "Как общаться",
    "family": "Семья",
    "other": "Другое",
}


def label_for_key(key: str) -> str:
    return FACT_LABELS_RU.get(key, key)


def looks_like_request(text: str) -> bool:
    t = (text or "").lower()
    markers = (
        "не называй",
        "не пиши",
        "не говори",
        "не надо",
        "не нужно",
        "прошу",
        "пожалуйста не",
        "запомни",
        "зови меня",
        "называй меня",
        "обращайся",
        "хочу чтобы",
        "хочу, чтобы",
        "лучше зови",
        "давай на «ты»",
        "давай на ты",
        "без официоза",
        "короче пиши",
        "пиши коротко",
        "не сюсюкай",
        "не читай нотации",
    )
    return any(m in t for m in markers)


def extract_preferences_heuristic(text: str) -> dict[str, str]:
    """Достаёт явные просьбы без GPT — чтобы не терялись."""
    raw = (text or "").strip()
    if not raw or not looks_like_request(raw):
        return {}

    facts: dict[str, str] = {}
    lower = raw.lower()

    # Как обращаться
    m = re.search(
        r"(?:зови|называй|обращайся(?:\s+ко\s+мне)?)\s+(?:меня\s+)?[«\"']?([А-Яа-яЁёA-Za-z\-]+)[»\"']?",
        raw,
        re.IGNORECASE,
    )
    if m:
        facts["address"] = f"звать «{m.group(1)}»"

    if "не называй" in lower or "не зови" in lower:
        m2 = re.search(
            r"не\s+(?:называй|зови)(?:\s+меня)?\s+[«\"']?([А-Яа-яЁёA-Za-z\-]+)[»\"']?",
            raw,
            re.IGNORECASE,
        )
        if m2:
            facts["address"] = (
                (facts.get("address") + "; " if facts.get("address") else "")
                + f"не называть «{m2.group(1)}»"
            )
        else:
            facts.setdefault("preferences", raw[:180])

    # Стиль общения
    if any(x in lower for x in ("пиши коротко", "короче пиши", "короткие сообщения")):
        facts["communication"] = "писать коротко"
    if any(x in lower for x in ("не сюсюкай", "без сюсюканья", "меньше ласкательных")):
        facts["communication"] = (
            (facts.get("communication") + "; " if facts.get("communication") else "")
            + "меньше сюсюканья"
        )
    if "не читай нотации" in lower or "без нотаций" in lower:
        facts["preferences"] = (
            (facts.get("preferences") + "; " if facts.get("preferences") else "")
            + "не читать нотации"
        )

    # Общая просьба «запомни …»
    if "запомни" in lower and "preferences" not in facts:
        after = re.split(r"запомни[,:]?\s*", raw, maxsplit=1, flags=re.IGNORECASE)
        if len(after) > 1 and after[1].strip():
            facts["preferences"] = after[1].strip()[:200]

    if not facts and looks_like_request(raw):
        facts["preferences"] = raw[:200]

    return {k: v for k, v in facts.items() if v}


def relationship_patch_from_facts(facts: dict[str, str]) -> dict:
    """Часть предпочтений дублируем в relationship для промпта."""
    patch: dict = {}
    address = facts.get("address") or ""
    prefs = facts.get("preferences") or ""
    comm = facts.get("communication") or ""

    # «звать X» → pet_names
    m = re.search(r"звать\s+[«\"']?([^«»\"';;]+)[»\"']?", address, re.IGNORECASE)
    if m:
        patch["pet_names"] = [m.group(1).strip()]

    notes_bits = []
    if address:
        notes_bits.append(address)
    if prefs:
        notes_bits.append(prefs)
    if comm:
        notes_bits.append(comm)
        if "коротк" in comm.lower():
            patch["chat_style"] = "коротко"
    if notes_bits:
        patch["notes"] = "; ".join(notes_bits)[:300]
    return patch

"""Карточка личности мамы, статус и поведенческие правила."""

from __future__ import annotations

import json
import random
from copy import deepcopy
from datetime import datetime

# Богатый дефолт «Людмила Петровна» — живой аватар из коробки
DEFAULT_PERSONA: dict = {
    "age": 63,
    "city": "Самара",
    "occupation": "на пенсии, раньше бухгалтер на заводе",
    "family_note": "живу одна в двушке, дети выросли",
    "habits": [
        "утром обязательно чай с бутербродом",
        "смотрю новости и сериалы вечером",
        "люблю звонить/писать ближе к обеду",
        "по выходным пеку что-нибудь простое",
    ],
    "likes": [
        "цветы на подоконнике",
        "рынок по субботам",
        "когда ребёнок рассказывает мелочи дня",
    ],
    "weaknesses": [
        "путаю названия приложений и кнопок в телефоне",
        "иногда забываю, какой сегодня день недели",
        "могу повторить один и тот же совет дважды",
    ],
    "catchphrases": [
        "ну ты понял(а), да?",
        "главное — здоровье",
        "я же говорила… ладно, не буду",
    ],
    "taboos": [
        "не читаю нотации длиннее пары фраз",
        "не обесцениваю чувства",
        "не даю советы, если не просят",
        "не пишу «ок» и канцелярит",
    ],
    "backstory": (
        "Вырастила детей, привыкла быть опорой. Скучает по живым разговорам, "
        "но не душит. Гордится тихо, переживает явно, шутит по-доброму."
    ),
}

DEFAULT_RELATIONSHIP: dict = {
    "chat_style": "смешанно",
    "pet_names": ["солнышко", "зайка", "родной", "милый"],
    "shared_jokes": [],
    "topics_joy": [],
    "topics_avoid": [],
    "recent_mood": "neutral",
    "notes": "",
}

# Поведенческие правила по типу характера
BEHAVIOR_RULES: dict[str, str] = {
    "заботливая": (
        "На успех — тёплая гордость и один конкретный вопрос.\n"
        "На усталость — коротко, еда/сон/пауза, без лекции.\n"
        "На молчание — мягкий check-in без давления.\n"
        "Иногда (редко) расскажи кусочек СВОЕЙ жизни."
    ),
    "строгая": (
        "На успех — сдержанная похвала («молодец, так и надо») + вопрос по делу.\n"
        "На усталость — признай тяжесть, но подтолкни к одному маленькому шагу.\n"
        "На молчание — коротко и по существу, без сюсюканья.\n"
        "Можешь мягко поспорить, если видишь явную ерунду."
    ),
    "веселая": (
        "На успех — шутка + восторг, без пафоса.\n"
        "На усталость — лёгкая поддержка, можно самоиронию про себя.\n"
        "На молчание — игривый пинг, не допрос.\n"
        "Чаще вставляй бытовые мелочи и юмор."
    ),
    "ностальгическая": (
        "Ностальгию используй РЕДКО (примерно раз в много сообщений).\n"
        "На успех — чаще просто гордость здесь и сейчас, без «в детстве».\n"
        "На усталость — забота; воспоминание только если оно есть в фактах о ребёнке.\n"
        "НИКОГДА не выдумывай совместное прошлое. Нет факта — спроси, не утверждай.\n"
        "Бытовые мелочи своей жизни — ок; фальшивые «помню как ты…» — запрещены."
    ),
}

HABIT_CHOICES = [
    "утром чай и новости",
    "вечером сериалы",
    "люблю готовить простое",
    "хожу на рынок",
    "вяжу / рукодельничаю",
    "гуляю у дома",
    "звоню родственникам",
    "читаю детективы",
]

STATUS_BY_HOUR = {
    # hour_start inclusive ranges handled in function
    "morning": ["на кухне с чаем", "собираюсь на день", "поливаю цветы"],
    "day": ["дома, делаю мелочи", "смотрю новости", "вернулась с магазина"],
    "evening": ["смотрю сериал", "на кухне ужинаю", "тихо сижу с чаем"],
    "night": ["уже почти сплю", "ещё не сплю, думаю о своём"],
}

LIFE_SNIPPETS = [
    "Сегодня в магазине очередь была — стояла и думала о тебе.",
    "Соседка опять сверлит. Ужас.",
    "Чайник свистит, села на минутку написать.",
    "На подоконнике герань распустилась, красота.",
    "По телеку опять одну и ту же рекламу крутят.",
    "Пекла пирог — чуть не забыла в духовке.",
    "На рынке клубнику хвалили, я не взяла: дорогая.",
    "Телефон опять сам обновился, ничего не найти.",
]


def default_persona() -> dict:
    return deepcopy(DEFAULT_PERSONA)


def default_relationship() -> dict:
    return deepcopy(DEFAULT_RELATIONSHIP)


def parse_json_field(raw: str | None, fallback: dict) -> dict:
    if not raw:
        return deepcopy(fallback)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return deepcopy(fallback)
    if not isinstance(data, dict):
        return deepcopy(fallback)
    merged = deepcopy(fallback)
    merged.update(data)
    return merged


def dumps_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def ensure_persona(raw: str | None) -> dict:
    persona = parse_json_field(raw, DEFAULT_PERSONA)
    # Гарантируем ключевые списки
    for key in ("habits", "likes", "weaknesses", "catchphrases", "taboos"):
        if not isinstance(persona.get(key), list):
            persona[key] = list(DEFAULT_PERSONA.get(key, []))
    return persona


def ensure_relationship(raw: str | None) -> dict:
    rel = parse_json_field(raw, DEFAULT_RELATIONSHIP)
    for key in ("pet_names", "shared_jokes", "topics_joy", "topics_avoid"):
        if not isinstance(rel.get(key), list):
            rel[key] = []
    return rel


def pick_status(time_of_day: str) -> str:
    bucket = {
        "утро": "morning",
        "день": "day",
        "вечер": "evening",
        "ночь": "night",
    }.get(time_of_day, "day")
    return random.choice(STATUS_BY_HOUR[bucket])


def pick_life_snippet(persona: dict | None = None) -> str:
    habits = (persona or {}).get("habits") or []
    pool = list(LIFE_SNIPPETS)
    if habits:
        habit = random.choice(habits)
        pool.append(f"Сейчас как раз: {habit} — и вспомнила о тебе.")
    return random.choice(pool)


def behavior_rules_for(personality: str) -> str:
    return BEHAVIOR_RULES.get(personality, BEHAVIOR_RULES["заботливая"])


def format_persona_block(persona: dict, status: str | None = None) -> str:
    habits = ", ".join(persona.get("habits", [])[:4]) or "—"
    likes = ", ".join(persona.get("likes", [])[:3]) or "—"
    weak = ", ".join(persona.get("weaknesses", [])[:3]) or "—"
    taboos = "; ".join(persona.get("taboos", [])[:4]) or "—"
    lines = [
        f"Возраст: {persona.get('age', '—')}, город: {persona.get('city', '—')}.",
        f"Занятие: {persona.get('occupation', '—')}.",
        f"О себе: {persona.get('family_note', '')} {persona.get('backstory', '')}".strip(),
        f"Привычки: {habits}.",
        f"Любит: {likes}.",
        f"Слабости (можно проявлять редко): {weak}.",
        f"Нельзя: {taboos}.",
    ]
    if status:
        lines.append(f"Сейчас по статусу: «{status}».")
    return "\n".join(lines)


def format_relationship_block(rel: dict) -> str:
    parts = [
        f"Стиль общения с ребёнком: {rel.get('chat_style', 'смешанно')}.",
        f"Недавнее настроение ребёнка: {rel.get('recent_mood', 'neutral')}.",
    ]
    if rel.get("pet_names"):
        parts.append("Свои обращения: " + ", ".join(rel["pet_names"][:5]))
    if rel.get("topics_joy"):
        parts.append("Темы, которые радуют: " + ", ".join(rel["topics_joy"][:5]))
    if rel.get("topics_avoid"):
        parts.append("Темы осторожно: " + ", ".join(rel["topics_avoid"][:5]))
    if rel.get("shared_jokes"):
        parts.append("Наши шутки/отсылки: " + ", ".join(rel["shared_jokes"][:5]))
    if rel.get("notes"):
        parts.append("Заметки об отношениях: " + str(rel["notes"]))
    return "\n".join(parts)


def settings_persona_fields(settings_obj) -> dict:
    """Достаёт persona/relationship/status из ORM UserSettings."""
    persona = ensure_persona(getattr(settings_obj, "persona_json", None))
    relationship = ensure_relationship(getattr(settings_obj, "relationship_json", None))
    status = getattr(settings_obj, "mama_status", None) or pick_status("день")
    return {
        "persona": persona,
        "relationship": relationship,
        "mama_status": status,
        "onboarding_completed": bool(
            getattr(settings_obj, "onboarding_completed", False)
        ),
    }


def maybe_refresh_status(settings_obj, time_of_day: str, force: bool = False) -> str:
    """Обновляет статус, если устарел (>2ч) или force."""
    status = getattr(settings_obj, "mama_status", None)
    updated = getattr(settings_obj, "mama_status_updated_at", None)
    stale = True
    if updated and not force:
        try:
            stale = (datetime.utcnow() - updated).total_seconds() > 2 * 3600
        except Exception:
            stale = True
    if force or not status or stale:
        status = pick_status(time_of_day)
    return status

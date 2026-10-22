import json
import logging
import random
import re
from difflib import SequenceMatcher

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_PARAMS, PROMPTS_DIR
from core.persona import (
    behavior_rules_for,
    ensure_persona,
    ensure_relationship,
    format_persona_block,
    format_relationship_block,
    pick_status,
)

logger = logging.getLogger(__name__)

INITIATIVE_BANNED = (
    "рада, что ты написал",
    "рада что ты написал",
    "как же я рада, что ты написал",
    "соскучилась неимоверно",
    "обнимаю крепко-крепко",
    "всегда здесь для тебя",
    "всегда рядом",
    "написала(а)",
    "написал(а)",
)

PERSONALITY_HINTS = {
    "заботливая": "Ты заботливая, тёплая, немного сентиментальная.",
    "строгая": "Ты строгая, но любящая. Говоришь прямо, но с теплотой.",
    "веселая": "Ты весёлая, шутливая, поднимаешь настроение.",
    "ностальгическая": (
        "Ты мягкая и тёплая. Ностальгию проявляешь редко и только опираясь на "
        "то, что ребёнок сам рассказывал. Не выдумывай детские воспоминания."
    ),
}

# Полное официальное → домашнее (если пользователь указал паспортное имя)
_NAME_DIMINUTIVES = {
    "евгений": "Женя",
    "евгения": "Женя",
    "александр": "Саша",
    "александра": "Саша",
    "дмитрий": "Дима",
    "михаил": "Миша",
    "николай": "Коля",
    "владимир": "Вова",
    "алексей": "Лёша",
    "сергей": "Серёжа",
    "андрей": "Андрей",
    "иван": "Ваня",
    "мария": "Маша",
    "анна": "Аня",
    "елена": "Лена",
    "ольга": "Оля",
    "татьяна": "Таня",
    "наталья": "Наташа",
    "екатерина": "Катя",
    "юрий": "Юра",
    "павел": "Паша",
    "артём": "Тёма",
    "артем": "Тёма",
    "максим": "Макс",
    "кирилл": "Кирилл",
}


# Базовые мамины ласкательные — основной способ обращения
DEFAULT_PET_NAMES = [
    "солнышко",
    "зайка",
    "родной",
    "милый",
    "хороший",
    "лапушка",
]


def _short_home_name(user_name: str | None) -> str | None:
    name = (user_name or "").strip()
    if not name:
        return None
    first = name.split()[0]
    lower = first.lower().replace("ё", "е")
    if lower in _NAME_DIMINUTIVES:
        return _NAME_DIMINUTIVES[lower]
    if len(first) <= 5:
        return first
    return None


def intimate_address(user_name: str | None, relationship: dict | None = None) -> str:
    """Подсказка для промпта: чем можно звать (ласкательные + редкое имя)."""
    rel = relationship or {}
    custom = [str(p).strip() for p in (rel.get("pet_names") or []) if str(p).strip()]
    pets = custom or list(DEFAULT_PET_NAMES)
    home = _short_home_name(user_name)
    formal = (user_name or "").strip().split()[0] if (user_name or "").strip() else ""
    sample = ", ".join(pets[:5])
    bits = [f"чаще: {sample}", "часто без обращения («ты»)"]
    if home:
        bits.append(f"иногда коротко: {home}")
    if formal and formal.lower().replace("ё", "е") not in {
        (home or "").lower().replace("ё", "е")
    }:
        bits.append(
            f"официально «{formal}» — только в редких строгих/серьёзных репликах"
        )
    return "; ".join(bits)


RESPONSE_LENGTH_HINTS = {
    1: "Отвечай очень кратко, 1-2 предложения.",
    2: "Отвечай коротко, 2-3 предложения.",
    3: "Отвечай средней длины, 3-5 предложений.",
    4: "Отвечай развёрнуто, 5-7 предложений.",
    5: "Отвечай подробно и тепло, 7-10 предложений.",
}


class GPTClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.system_template = self._load_prompt("system.txt")
        self.extract_template = self._load_prompt("extract_facts.txt")
        self.crisis_template = self._load_prompt("crisis.txt")

    def _load_prompt(self, filename: str) -> str:
        path = PROMPTS_DIR / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def build_system_prompt(
        self,
        settings: dict,
        facts: dict[str, str],
        time_of_day: str,
    ) -> str:
        # Просьбы/предпочтения — первыми и обязательно соблюдать
        priority_keys = (
            "preferences",
            "requests",
            "address",
            "communication",
        )
        ordered: list[tuple[str, str]] = []
        for key in priority_keys:
            if key in facts and facts[key]:
                ordered.append((key, facts[key]))
        for key, value in facts.items():
            if key not in priority_keys:
                ordered.append((key, value))
        recent_items = ordered[-14:]
        facts_lines = [f"- {key}: {value}" for key, value in recent_items]
        facts_block = (
            "Факты и ПРОСЬБЫ ребёнка (просьбы соблюдай всегда; не перечисляй всё вслух):\n"
            + "\n".join(facts_lines)
            if facts_lines
            else "Пока мало фактов о ребенке — мягко узнай больше в разговоре."
        )

        personality = settings.get("mama_personality", "заботливая")
        emoji_rule = (
            "Твои сообщения живые, с эмодзи 🤗🥰❤️."
            if settings.get("enable_emojis", True)
            else "Не используй эмодзи в сообщениях."
        )
        persona = settings.get("persona") or ensure_persona(None)
        if isinstance(persona, str):
            persona = ensure_persona(persona)
        relationship = settings.get("relationship") or ensure_relationship(None)
        if isinstance(relationship, str):
            relationship = ensure_relationship(relationship)
        mama_status = settings.get("mama_status") or pick_status(time_of_day)
        user_name = settings.get("user_name") or ""
        intimate = intimate_address(user_name, relationship)

        def _safe(value: object) -> str:
            # Чтобы .format не ломался на { } в биографии пользователя
            return str(value).replace("{", "{{").replace("}", "}}")

        return self.system_template.format(
            mama_name=_safe(settings.get("mama_name", "Людмила Петровна")),
            mama_personality=_safe(personality),
            personality_hints=_safe(
                PERSONALITY_HINTS.get(personality, PERSONALITY_HINTS["заботливая"])
            ),
            persona_block=_safe(format_persona_block(persona, status=mama_status)),
            relationship_block=_safe(format_relationship_block(relationship)),
            behavior_rules=_safe(behavior_rules_for(personality)),
            emoji_rule=_safe(emoji_rule),
            response_length_hint=_safe(
                RESPONSE_LENGTH_HINTS.get(
                    settings.get("response_length", 3), RESPONSE_LENGTH_HINTS[3]
                )
            ),
            facts_block=_safe(facts_block),
            time_of_day=_safe(time_of_day),
            mama_status=_safe(mama_status),
            user_name=_safe(user_name or "—"),
            intimate_name=_safe(intimate),
            user_gender=_safe(settings.get("user_gender", "не указано")),
        )

    @staticmethod
    def _history_without_current_user(
        history: list[dict[str, str]] | None,
        user_message: str,
        batch_texts: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """Убирает хвост с текущей репликой/батчем — он добавляется отдельно."""
        cleaned = list(history or [])
        pending = [t.strip() for t in (batch_texts or []) if t and t.strip()]
        combined = (user_message or "").strip()

        # Снимаем отдельные короткие сообщения батча с конца истории
        changed = True
        while changed and cleaned and cleaned[-1].get("role") == "user":
            changed = False
            content = (cleaned[-1].get("content") or "").strip()
            if pending and content in pending:
                pending.remove(content)
                cleaned.pop()
                changed = True
            elif content == combined:
                cleaned.pop()
                changed = True

        while (
            cleaned
            and cleaned[-1].get("role") == "user"
            and (cleaned[-1].get("content") or "").strip() == combined
        ):
            cleaned.pop()
        return cleaned

    async def generate_reply(
        self,
        user_message: str,
        settings: dict,
        facts: dict[str, str],
        history: list[dict[str, str]],
        time_of_day: str,
        batch_texts: list[str] | None = None,
    ) -> str:
        if not self.client:
            return (
                "Солнышко, у меня сейчас технические неполадки, но я всё равно с тобой ❤️ "
                "Попробуй написать чуть позже."
            )

        prior = self._history_without_current_user(
            history, user_message, batch_texts=batch_texts
        )
        system_prompt = self.build_system_prompt(settings, facts, time_of_day)
        if prior and prior[-1].get("role") == "assistant":
            system_prompt += (
                "\nРебёнок отвечает на твоё предыдущее сообщение в этом диалоге. "
                "Продолжай разговор: не здоровайся заново, если уже поздоровались, "
                "и опирайся на то, что ты только что написала."
            )
        if batch_texts and len(batch_texts) > 1:
            system_prompt += (
                "\nРебёнок прислал несколько коротких сообщений подряд — это одна мысль. "
                "Ответь целостно на всё сразу, не по каждому сообщению отдельно."
            )
        system_prompt += (
            "\nЧаще отвечай ОДНИМ сообщением. Разделитель ||| — только для 2 коротких "
            "реплик (каждая до пары предложений). Не делай три длинных сообщения."
        )
        return await self.generate_reply_custom(
            system_prompt=system_prompt,
            history=prior,
            user_message=user_message,
            openai_params=OPENAI_PARAMS,
        )

    async def generate_reply_custom(
        self,
        system_prompt: str,
        history: list[dict[str, str]],
        user_message: str,
        openai_params: dict | None = None,
    ) -> str:
        if not self.client:
            return (
                "Солнышко, у меня сейчас технические неполадки, но я всё равно с тобой ❤️ "
                "Попробуй написать чуть позже."
            )

        params = dict(openai_params or OPENAI_PARAMS)
        # model comes from OPENAI_PARAMS / config; ensure present
        if "model" not in params:
            params["model"] = OPENAI_PARAMS.get("model", "gpt-4-turbo")

        prior = self._history_without_current_user(history, user_message)
        # Если модель вернёт ||| — это несколько пузырей; маркер не для пользователя
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(prior)
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self.client.chat.completions.create(
                messages=messages,
                **params,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return (
                "Ох, солнышко, что-то пошло не так на моей стороне. "
                "Но я здесь и скоро отвечу нормально ❤️"
            )

    @staticmethod
    def _parse_facts_response(content: str) -> dict[str, str]:
        text = (content or "{}").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return {}
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items() if v is not None and str(v).strip()}

    async def extract_facts(self, user_text: str) -> dict[str, str]:
        if not self.client:
            return {}

        # replace, не format — иначе фигурные скобки в тексте пользователя ломают шаблон
        prompt = self.extract_template.replace("<<<USER_TEXT>>>", user_text)
        try:
            response = await self.client.chat.completions.create(
                model=OPENAI_PARAMS["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=300,
            )
            content = response.choices[0].message.content or "{}"
            facts = self._parse_facts_response(content)
            if facts:
                logger.info("Extracted facts: %s", facts)
            return facts
        except Exception as e:
            logger.error("Fact extraction error: %s", e)
        return {}

    @staticmethod
    def _is_too_similar(new_text: str, old_texts: list[str], threshold: float = 0.62) -> bool:
        for old in old_texts:
            if SequenceMatcher(None, new_text.lower(), old.lower()).ratio() > threshold:
                return True
        return False

    @staticmethod
    def _has_banned_phrases(text: str) -> bool:
        lowered = text.lower()
        return any(phrase in lowered for phrase in INITIATIVE_BANNED)

    def _initiative_user_prompt(
        self,
        message_type: str,
        facts: dict[str, str],
        recent_messages: list[str],
        attempt: int,
        life_snippet: str | None = None,
    ) -> str:
        fact_hint = ""
        if facts:
            key, value = random.choice(list(facts.items()))
            fact_hint = f"Один конкретный факт для опоры (не обязательно все): {key} — {value}."
        snippet = life_snippet or "Сегодня обычный день дома."

        type_hints = {
            "morning": (
                "Ты сама пишешь утром первой. Коротко про сон/завтрак/планы на день. "
                "Без «рада что написал» — ребёнок ещё не писал."
            ),
            "day": (
                "Дневной check-in. Спроси, как идёт день или работа/дела. "
                "Можно лёгкую шутку. Без «соскучилась неимоверно»."
            ),
            "evening": (
                "Вечернее сообщение. Спроси, что запомнилось за день или как усталость. "
                "Без утреннего тона и без завтрака."
            ),
            "memory": (
                f"Напиши проактивно, опираясь на факт. {fact_hint} "
                "Один конкретный вопрос по делу."
            ),
            "life": (
                f"Напиши от СВОЕГО лица про кусочек своей жизни. Опора: «{snippet}». "
                "Можно в конце один лёгкий вопрос ребёнку, но не обязательно. "
                "Главное — ты живой человек со своим днём, не только заботливый бот."
            ),
            "checkin": (
                "Короткое «просто так» без пафоса. Можно без вопроса. "
                "Иногда обратись по имени, иногда без ласкательных."
            ),
            "general": (
                "Тёплое короткое сообщение по своей инициативе. "
                "Один живой нюанс, без шаблонных обнимашек."
            ),
        }
        base = type_hints.get(message_type, type_hints["general"])
        recent_block = ""
        if recent_messages:
            joined = "\n---\n".join(recent_messages[-8:])
            recent_block = (
                f"\n\nВот твои последние сообщения — НЕ повторяй их структуру, "
                f"обращения и формулировки:\n{joined}"
            )
        retry = ""
        if attempt > 0:
            retry = (
                "\nПредыдущий вариант был слишком шаблонным или похожим на прошлые. "
                "Напиши СОВСЕМ иначе: другой зачин, другой ритм, другая тема."
            )
        return (
            f"{base}\n"
            "Правила:\n"
            "- 1–3 коротких предложения\n"
            "- максимум 1–2 эмодзи (или без них)\n"
            "- запрещены клише: «рада что написал(а)», «соскучилась неимоверно», "
            "«обнимаю крепко-крепко», «всегда рядом/здесь для тебя»\n"
            "- не притворяйся, что это ответ на его сообщение — ты пишешь сама\n"
            "- чередуй обращения: имя / без обращения / редко ласкательное\n"
            f"{recent_block}{retry}"
        )

    async def generate_initiative_message(
        self,
        settings: dict,
        facts: dict[str, str],
        time_of_day: str,
        message_type: str = "general",
        recent_messages: list[str] | None = None,
    ) -> str:
        recent = recent_messages or []
        from core.persona import pick_life_snippet

        persona = settings.get("persona") or {}
        if isinstance(persona, str):
            persona = ensure_persona(persona)
        life_snippet = pick_life_snippet(persona if isinstance(persona, dict) else None)

        if not self.client:
            fallbacks = {
                "morning": "Доброе утро. Как спалось — удалось выспаться?",
                "day": "Как день? Есть минутка рассказать, что по плану?",
                "evening": "Как вечер? Что из дня зацепило больше всего?",
                "memory": "Вспомнила про твои дела — как там сейчас?",
                "life": life_snippet,
                "checkin": "Просто заглянула. Ты как?",
                "general": "На связи. Как ты сегодня?",
            }
            return fallbacks.get(message_type, fallbacks["general"])

        system = self.build_system_prompt(settings, facts, time_of_day)
        system += (
            "\n\nСейчас ты пишешь ПРОАКТИВНОЕ сообщение по своей инициативе, "
            "а не отвечаешь на реплику ребёнка."
        )
        params = dict(OPENAI_PARAMS)
        params["temperature"] = min(1.1, float(params.get("temperature", 0.95)) + 0.1)
        params["presence_penalty"] = max(0.8, float(params.get("presence_penalty", 0.6)))

        last_text = ""
        for attempt in range(3):
            prompt = self._initiative_user_prompt(
                message_type, facts, recent, attempt, life_snippet=life_snippet
            )
            try:
                response = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    **params,
                )
                text = (response.choices[0].message.content or "").strip()
                last_text = text
                if not text:
                    continue
                if self._has_banned_phrases(text) or self._is_too_similar(text, recent):
                    logger.info(
                        "Initiative rewrite (attempt %d, type=%s)", attempt + 1, message_type
                    )
                    continue
                return text
            except Exception as e:
                logger.error("Initiative message error: %s", e)
                break

        return last_text or "Заглянула на минутку. Как ты сегодня?"

    @property
    def crisis_response(self) -> str:
        return self.crisis_template

    async def transcribe_audio(
        self, file_bytes: bytes, filename: str = "voice.ogg"
    ) -> str:
        """Распознаёт речь через OpenAI Whisper."""
        if not self.client:
            return ""
        try:
            from io import BytesIO

            bio = BytesIO(file_bytes)
            bio.name = filename
            # Explicit tuple is more reliable for aiohttp multipart upload
            mime = "audio/ogg"
            if filename.endswith(".mp3"):
                mime = "audio/mpeg"
            elif filename.endswith(".mp4") or filename.endswith(".m4a"):
                mime = "audio/mp4"
            elif filename.endswith(".wav"):
                mime = "audio/wav"

            result = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=(filename, bio, mime),
                language="ru",
            )
            text = (result.text or "").strip()
            logger.info("Voice transcribed (%d chars)", len(text))
            return text
        except Exception as e:
            logger.error("Voice transcription error: %s", e)
            return ""

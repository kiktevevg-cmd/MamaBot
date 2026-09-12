import json
import logging

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_PARAMS, PROMPTS_DIR

logger = logging.getLogger(__name__)

PERSONALITY_HINTS = {
    "заботливая": "Ты заботливая, тёплая, немного сентиментальная.",
    "строгая": "Ты строгая, но любящая. Говоришь прямо, но с теплотой.",
    "веселая": "Ты весёлая, шутливая, поднимаешь настроение.",
    "ностальгическая": "Ты часто вспоминаешь прошлое, детство, семейные традиции.",
}

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
        facts_lines = []
        for key, value in list(facts.items())[:5]:
            facts_lines.append(f"- {key}: {value}")
        facts_block = (
            "Важные факты о ребенке:\n" + "\n".join(facts_lines)
            if facts_lines
            else "Пока мало фактов о ребенке — узнай больше в разговоре."
        )

        personality = settings.get("mama_personality", "заботливая")
        emoji_rule = (
            "Твои сообщения живые, с эмодзи 🤗🥰❤️."
            if settings.get("enable_emojis", True)
            else "Не используй эмодзи в сообщениях."
        )

        return self.system_template.format(
            mama_name=settings.get("mama_name", "Людмила Петровна"),
            mama_personality=personality,
            personality_hints=PERSONALITY_HINTS.get(personality, PERSONALITY_HINTS["заботливая"]),
            emoji_rule=emoji_rule,
            response_length_hint=RESPONSE_LENGTH_HINTS.get(
                settings.get("response_length", 3), RESPONSE_LENGTH_HINTS[3]
            ),
            facts_block=facts_block,
            time_of_day=time_of_day,
            user_name=settings.get("user_name") or "солнышко",
            user_gender=settings.get("user_gender", "не указано"),
        )

    async def generate_reply(
        self,
        user_message: str,
        settings: dict,
        facts: dict[str, str],
        history: list[dict[str, str]],
        time_of_day: str,
    ) -> str:
        if not self.client:
            return (
                "Солнышко, у меня сейчас технические неполадки, но я всё равно с тобой ❤️ "
                "Попробуй написать чуть позже."
            )

        system_prompt = self.build_system_prompt(settings, facts, time_of_day)
        return await self.generate_reply_custom(
            system_prompt=system_prompt,
            history=history,
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

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
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

    async def extract_facts(self, user_text: str) -> dict[str, str]:
        if not self.client:
            return {}

        prompt = self.extract_template.format(user_text=user_text)
        try:
            response = await self.client.chat.completions.create(
                model=OPENAI_PARAMS["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            content = response.choices[0].message.content or "{}"
            content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            facts = json.loads(content)
            if isinstance(facts, dict):
                return {k: str(v) for k, v in facts.items() if v}
        except Exception as e:
            logger.error("Fact extraction error: %s", e)
        return {}

    async def generate_initiative_message(
        self,
        settings: dict,
        facts: dict[str, str],
        time_of_day: str,
        message_type: str = "general",
    ) -> str:
        if not self.client:
            fallbacks = {
                "morning": "Доброе утро, солнышко! Как ты спал? 🥞",
                "memory": "Вспомнила о твоих делах — как там всё?",
                "general": "Скучаю, мой хороший. Как твои дела?",
            }
            return fallbacks.get(message_type, fallbacks["general"])

        type_hints = {
            "morning": "Напиши утреннее заботливое сообщение.",
            "memory": f"Спроси о чём-то из фактов: {facts}",
            "general": "Напиши тёплое сообщение просто так, соскучилась.",
        }
        system = self.build_system_prompt(settings, facts, time_of_day)
        prompt = type_hints.get(message_type, type_hints["general"])

        try:
            response = await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                **OPENAI_PARAMS,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error("Initiative message error: %s", e)
            return "Скучаю, солнышко. Как ты? ❤️"

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

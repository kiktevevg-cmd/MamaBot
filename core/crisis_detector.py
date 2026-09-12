from core.time_utils import is_night_time


class CrisisDetector:
    GREEN_KEYWORDS = [
        "устал",
        "устала",
        "нет сил",
        "тяжело",
        "перегруз",
        "выгорание",
        "не высыпаюсь",
        "стресс",
        "усталость",
    ]

    YELLOW_PHRASES = [
        ("не могу больше", "уже неделю"),
        ("не вижу смысла", "бессмысленно"),
        ("никому не нужен", "одинок"),
        ("не хочу ничего", "даже вставать"),
    ]

    YELLOW_SINGLE = [
        "не могу больше",
        "не вижу смысла",
        "никому не нужен",
        "не хочу ничего",
        "всё бессмысленно",
        "надоело жить",
        "не с кем поговорить",
    ]

    RED_KEYWORDS = [
        "хочу умереть",
        "покончить с собой",
        "самоубийств",
        "порежусь",
        "наврежу себе",
        "выпью таблетки",
        "нет выхода",
        "всё кончено",
        "не хочу просыпаться",
        "прощай",
        "последнее сообщение",
        "планирую умереть",
        "не хочу жить",
        "лучше бы меня не было",
        "возьму нож",
    ]

    GREEN_RESPONSE = (
        "Ох, солнышко, слышу, что ты устал. Это нормально — иногда хочется всё бросить "
        "и лежать. Ты молодец, что держишься. Давай сегодня без подвигов: поешь чего-то "
        "вкусного и ляг пораньше. Я с тобой ❤️"
    )

    YELLOW_RESPONSE = (
        "Солнышко, ты меня немножко пугаешь. Я чувствую, что тебе правда тяжело. "
        "Расскажи, что случилось? Ты не один, я здесь. Может, тебе нужна помощь? "
        "Только скажи ❤️"
    )

    def detect_crisis_level(
        self,
        text: str,
        user_history: list[str] | None = None,
        timezone: str = "UTC+3",
        sensitivity: int = 3,
    ) -> str | None:
        """Returns: 'green', 'yellow', 'red' or None."""
        text_lower = text.lower()
        user_history = user_history or []

        for keyword in self.RED_KEYWORDS:
            if keyword in text_lower:
                return "red"

        yellow_score = 0
        threshold = max(2, 4 - sensitivity)

        for phrase1, phrase2 in self.YELLOW_PHRASES:
            if phrase1 in text_lower and phrase2 in text_lower:
                yellow_score += 2

        for phrase in self.YELLOW_SINGLE:
            if phrase in text_lower:
                yellow_score += 1

        if is_night_time(timezone) and yellow_score > 0:
            yellow_score += 1

        if self._has_mood_shift(user_history, text):
            yellow_score += 1

        if yellow_score >= threshold:
            return "yellow"

        for word in self.GREEN_KEYWORDS:
            if word in text_lower:
                return "green"

        return None

    def _has_mood_shift(self, user_history: list[str], current_text: str) -> bool:
        if len(user_history) < 2:
            return False
        positive_words = ["хорошо", "рад", "рада", "отлично", "счастлив", "класс"]
        prev_positive = any(w in user_history[-2].lower() for w in positive_words)
        negative_words = ["плохо", "тяжело", "грустно", "одинок", "устал", "бессмысленно"]
        curr_negative = any(w in current_text.lower() for w in negative_words)
        return prev_positive and curr_negative

    def get_crisis_response(self, level: str, red_template: str | None = None) -> str:
        if level == "red":
            return red_template or ""
        if level == "yellow":
            return self.YELLOW_RESPONSE
        if level == "green":
            return self.GREEN_RESPONSE
        return ""

from core.reaction_manager import ReactionManager


def test_no_react_on_commands():
    rm = ReactionManager()
    assert rm.should_react("/start", {"enable_reactions": True}) is False
    assert rm.should_react("/help", {}) is False


def test_no_react_on_short_and_routine():
    rm = ReactionManager()
    ctx = {"enable_reactions": True, "reaction_sensitivity": 3, "user_id": 1}
    assert rm.should_react("Ок", ctx) is False
    assert rm.should_react("Да", ctx) is False
    assert rm.should_react("Как дела?", ctx) is False
    assert rm.should_react("Сегодня дождь", ctx) is False


def test_no_react_on_red_crisis():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "crisis_level": "red",
        "reaction_sensitivity": 3,
        "user_id": 1,
    }
    assert rm.should_react("Хочу умереть", ctx) is False


def test_joy_reactions():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "reaction_style": "живой",
        "allow_multiple_reactions": True,
        "reaction_sensitivity": 3,
        "user_id": 10,
    }
    text = "Мам, я защитил диплом!"
    assert rm.should_react(text, ctx) is True
    reactions = rm.get_reactions(text, ctx)
    assert "🔥" in reactions
    assert "🎉" in reactions
    assert len(reactions) <= 3


def test_love_reactions():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "reaction_style": "живой",
        "allow_multiple_reactions": True,
        "reaction_sensitivity": 3,
        "user_id": 11,
    }
    text = "Спасибо тебе, мама. Ты лучшая"
    assert rm.should_react(text, ctx) is True
    reactions = rm.get_reactions(text, ctx)
    assert "❤️" in reactions
    assert "🥰" in reactions


def test_sad_reactions():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "reaction_style": "живой",
        "allow_multiple_reactions": True,
        "reaction_sensitivity": 3,
        "user_id": 12,
    }
    text = "Мы расстались... мне очень больно"
    assert rm.should_react(text, ctx) is True
    reactions = rm.get_reactions(text, ctx)
    assert "💔" in reactions or "😢" in reactions or "🤗" in reactions


def test_restrained_style():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "reaction_style": "сдержанный",
        "allow_multiple_reactions": True,
        "reaction_sensitivity": 3,
        "user_id": 13,
    }
    reactions = rm.get_reactions("Меня повысили на работе!", ctx)
    assert reactions == ["❤️"]


def test_single_reaction_toggle():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "reaction_style": "живой",
        "allow_multiple_reactions": False,
        "reaction_sensitivity": 3,
        "user_id": 14,
    }
    reactions = rm.get_reactions("Купил новую машину!", ctx)
    assert len(reactions) == 1


def test_anti_repeat():
    rm = ReactionManager()
    ctx = {
        "enable_reactions": True,
        "reaction_style": "живой",
        "allow_multiple_reactions": True,
        "reaction_sensitivity": 3,
        "user_id": 99,
    }
    text = "Я сдал экзамен наконец!"
    assert rm.should_react(text, ctx) is True
    rm.get_reactions(text, ctx)
    assert rm.should_react(text, ctx) is False

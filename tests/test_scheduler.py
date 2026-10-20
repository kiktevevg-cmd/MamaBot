from datetime import datetime, timedelta

from core.scheduler import calculate_next_message_time, pick_initiative_type, should_send_message


def test_calculate_next_message_time_active():
    last = datetime.utcnow() - timedelta(minutes=60)
    settings = {"min_cooldown_minutes": 45, "max_cooldown_hours": 6, "initiative_level": 3}
    next_time = calculate_next_message_time(last, settings, has_recent_activity=True)
    # base 45 мин + jitter [-40; +50] → итог не меньше 20
    delta_min = (next_time - last).total_seconds() / 60
    assert 20 <= delta_min <= 95


def test_calculate_next_message_time_inactive():
    last = datetime.utcnow() - timedelta(hours=2)
    settings = {"min_cooldown_minutes": 45, "max_cooldown_hours": 6, "initiative_level": 5}
    next_time = calculate_next_message_time(last, settings, has_recent_activity=False)
    # base 216 мин * (3/5)=216? wait max_cooldown_hours*60*(3/initiative)=360*(3/5)=216 + jitter
    delta_min = (next_time - last).total_seconds() / 60
    assert 20 <= delta_min <= 270


def test_pick_initiative_type():
    allowed = {
        "morning",
        "day",
        "evening",
        "checkin",
        "general",
        "memory",
        "life",
    }
    assert pick_initiative_type({}, "UTC+3") in allowed
    assert pick_initiative_type({"work": "отчёт"}, "UTC+3") in allowed


class FakeSettings:
    dnd_enabled = False
    dnd_until = None


class FakeUser:
    timezone = "UTC+3"
    dnd_schedules = []


def test_should_send_message_dnd():
    user = FakeUser()
    settings = {
        "dnd_enabled": True,
        "dnd_until": datetime.utcnow() + timedelta(hours=1),
        "initiative_start_hour": 8,
        "initiative_end_hour": 22,
        "min_cooldown_minutes": 45,
        "max_cooldown_hours": 6,
        "initiative_level": 3,
    }
    assert should_send_message(user, settings, datetime.utcnow() - timedelta(hours=2)) is False

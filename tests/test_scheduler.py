from datetime import datetime, timedelta

from core.scheduler import calculate_next_message_time, pick_initiative_type, should_send_message


def test_calculate_next_message_time_active():
    last = datetime.utcnow() - timedelta(minutes=60)
    settings = {"min_cooldown_minutes": 45, "max_cooldown_hours": 6, "initiative_level": 3}
    next_time = calculate_next_message_time(last, settings, has_recent_activity=True)
    expected_delta = 45 * (3 / 3)
    assert (next_time - last).total_seconds() == pytest_approx_minutes(expected_delta)


def test_calculate_next_message_time_inactive():
    last = datetime.utcnow() - timedelta(hours=2)
    settings = {"min_cooldown_minutes": 45, "max_cooldown_hours": 6, "initiative_level": 5}
    next_time = calculate_next_message_time(last, settings, has_recent_activity=False)
    expected_delta = 6 * 60 * (3 / 5)
    assert (next_time - last).total_seconds() == pytest_approx_minutes(expected_delta)


def pytest_approx_minutes(minutes):
    from pytest import approx
    return approx(minutes * 60, rel=0.01)


def test_pick_initiative_type():
    assert pick_initiative_type({}, "UTC+3") in ("morning", "general", "memory")
    assert pick_initiative_type({"work": "отчёт"}, "UTC+3") == "memory"


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

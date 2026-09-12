from datetime import datetime, timedelta, timezone


def parse_timezone(tz_str: str) -> timezone:
    """Parse timezone string like 'UTC+3' or 'UTC-5'."""
    tz_str = tz_str.strip().upper()
    if tz_str == "UTC":
        return timezone.utc
    if tz_str.startswith("UTC"):
        offset_str = tz_str[3:]
        if not offset_str:
            return timezone.utc
        sign = 1 if offset_str.startswith("+") else -1
        hours = int(offset_str.lstrip("+-"))
        return timezone(timedelta(hours=sign * hours))
    return timezone(timedelta(hours=3))


def get_user_local_time(tz_str: str = "UTC+3") -> datetime:
    tz = parse_timezone(tz_str)
    return datetime.now(tz)


def get_time_of_day(tz_str: str = "UTC+3") -> str:
    hour = get_user_local_time(tz_str).hour
    if 5 <= hour < 12:
        return "утро"
    if 12 <= hour < 17:
        return "день"
    if 17 <= hour < 22:
        return "вечер"
    return "ночь"


def is_night_time(tz_str: str = "UTC+3") -> bool:
    hour = get_user_local_time(tz_str).hour
    return 2 <= hour < 5


def is_in_dnd_schedule(
    schedules: list, tz_str: str = "UTC+3"
) -> bool:
    """Check if current time falls within any DND schedule slot."""
    now = get_user_local_time(tz_str)
    current_day = now.weekday()
    current_time = now.strftime("%H:%M")

    for sched in schedules:
        if sched.day_of_week != current_day:
            continue
        if sched.start_time <= current_time <= sched.end_time:
            return True
    return False

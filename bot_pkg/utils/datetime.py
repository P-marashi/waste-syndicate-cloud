from datetime import datetime


def now() -> datetime:
    return datetime.now()


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def fromiso(
    value: str | None,
    default: datetime | None = None,
) -> datetime:
    if not value:
        return default or now()

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return default or now()


def today_key() -> str:
    return now().strftime("%Y-%m-%d")


def fmt_cd(seconds: float) -> str:
    seconds = max(0, int(seconds))

    if seconds <= 0:
        return "آماده! ✅"

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    if d:
        return f"{d} روز و {h} ساعت"

    if h:
        return f"{h} ساعت" if m == 0 else f"{h} ساعت و {m} دقیقه"

    if m:
        return f"{m} دقیقه" if s == 0 else f"{m} دقیقه و {s} ثانیه"

    return f"{s} ثانیه"


def fmt_dt(value: str | None) -> str:
    dt = fromiso(value, now())
    return dt.strftime("%Y/%m/%d ساعت %H:%M")

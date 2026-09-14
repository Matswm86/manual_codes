from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
OSLO = ZoneInfo("Europe/Oslo")


def to_oslo(hhmm, on_date, extra_days=0):
    """Convert one 'HHMM' New York clock time to Oslo. Returns 'HH:MM' or 'HH:MM (+1d)'."""
    hour, minute = int(hhmm[:2]), int(hhmm[2:])
    ny = datetime.combine(on_date, datetime.min.time(), tzinfo=NY)
    ny = ny + timedelta(days=extra_days, hours=hour, minutes=minute)
    oslo = ny.astimezone(OSLO)
    day_shift = (oslo.date() - on_date).days
    return oslo.strftime("%H:%M") + (f" (+{day_shift}d)" if day_shift else "")


def convert_range(text, on_date):
    """'1815-0400' -> '00:15 (+1d) - 10:00 (+1d)'. A session that ends
    before it starts is treated as running past midnight."""
    start, end = [part.strip() for part in text.split("-")]
    wraps = int(end) <= int(start)
    return f"{to_oslo(start, on_date)} - {to_oslo(end, on_date, extra_days=wraps)}"


if __name__ == "__main__":
    today = date.today()
    print(f"NY -> Oslo, using {today}. Blank line to quit.")
    while True:
        raw = input("NY range (e.g. 1815-0400): ").strip()
        if not raw:
            break
        try:
            print("  Oslo:", convert_range(raw, today))
        except (ValueError, IndexError):
            print("  Use HHMM-HHMM, e.g. 0930-1600")

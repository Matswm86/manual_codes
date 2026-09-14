import os
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv

HIT_FILE = Path.home() / "mnq_hit_levels.txt"
ENV_FILE = Path.home() / "mnq.env"
ALERT_WINDOW_MINUTES = 15
LOOKBACK_DAYS = 15
REQUEST_TIMEOUT = 10


def get_token():
    load_dotenv(ENV_FILE)
    username = os.environ["PROJECT_X_USERNAME"]
    api_key = os.environ["PROJECT_X_API_KEY"]
    payload = {"userName": username, "apiKey": api_key}
    response = requests.post(
        "https://api.topstepx.com/api/Auth/loginKey",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if data["success"]:
        return data["token"]
    print(f"Login failed: {data['errorMessage']}")
    return None


def get_contract_id(token):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"searchText": "MNQ", "live": False}
    response = requests.post(
        "https://api.topstepx.com/api/Contract/search",
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    for contract in data["contracts"]:
        if contract["name"].startswith("MNQ"):
            return contract["id"]
    print("No MNQ contract found")
    return None


def get_bars(contract_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    ny = ZoneInfo("America/New_York")
    end = datetime.now(ny)
    start = end - timedelta(days=LOOKBACK_DAYS)

    payload = {
        "contractId": contract_id,
        "live": False,
        "startTime": start.isoformat(),
        "endTime": end.isoformat(),
        "unit": 2,
        "unitNumber": 1,
        "limit": 20000,
        "includePartialBar": True,
    }

    response = requests.post(
        "https://api.topstepx.com/api/History/retrieveBars",
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    data = response.json()
    df = pd.DataFrame(data["bars"])
    df["t"] = pd.to_datetime(df["t"]).dt.tz_convert(ny)
    df = df.set_index("t").sort_index()
    return df.rename(columns={"h": "High", "l": "Low", "c": "Close", "o": "Open"})


def session_name(timestamp):
    t = timestamp.time()
    if t >= time(20, 0) or t < time(1, 0):
        return "ASIA"
    if time(3, 0) <= t < time(9, 30):
        return "LONDON"
    if time(9, 30) <= t < time(16, 0):
        return "NEW YORK"
    return None


def session_date(timestamp):
    date = timestamp.date()
    if timestamp.time() < time(1, 0):
        date = date - timedelta(days=1)
    return date


def prior_levels(bars):
    ny = ZoneInfo("America/New_York")
    today = session_date(datetime.now(ny))
    levels = []
    for date in sorted(set(bars.index.map(session_date))):
        if date >= today:
            continue
        day = bars[bars.index.map(session_date) == date]

        for session in ["ASIA", "LONDON", "NEW YORK"]:
            session_bars = day[day.index.map(session_name) == session]
            if len(session_bars) == 0:
                continue
            end = session_bars.index[-1]
            levels.append(
                {
                    "name": f"{date} {session} HIGH",
                    "side": "HIGH",
                    "price": session_bars["High"].max(),
                    "end": end,
                }
            )
            levels.append(
                {
                    "name": f"{date} {session} LOW",
                    "side": "LOW",
                    "price": session_bars["Low"].min(),
                    "end": end,
                }
            )
    return levels


def first_touches(bars, levels):
    touches = {}
    for level in levels:
        after = bars[bars.index > level["end"]]
        if level["side"] == "HIGH":
            reached = after[after["High"] >= level["price"]]
        else:
            reached = after[after["Low"] <= level["price"]]
        if len(reached) > 0:
            touches[level["name"]] = reached.index[0]
    return touches


def load_hit_levels():
    try:
        with HIT_FILE.open() as file:
            return {line.strip() for line in file if line.strip()}
    except FileNotFoundError:
        return set()


def save_hit_levels(names):
    with HIT_FILE.open("w") as file:
        file.writelines(f"{name}\n" for name in sorted(names))


def send_alert(text):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print(f"NTFY_TOPIC not set, skipping alert: {text}")
        return
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=text,
        timeout=REQUEST_TIMEOUT,
    )


def main():
    token = get_token()
    contract_id = get_contract_id(token)
    bars = get_bars(contract_id, token)
    levels = prior_levels(bars)
    touches = first_touches(bars, levels)
    known = load_hit_levels()

    last_bar = bars.index[-1]
    cutoff = last_bar - timedelta(minutes=ALERT_WINDOW_MINUTES)

    prices = {level["name"]: level["price"] for level in levels}
    fresh = [
        name for name, when in touches.items() if name not in known and when >= cutoff
    ]

    save_hit_levels(touches)

    untouched = len(levels) - len(touches)
    print(f"Price: {bars['Close'].iloc[-1]:.2f} at {last_bar}")
    print(f"Levels: {len(levels)} tracked, {untouched} still untouched")
    print(f"Fresh hits: {fresh}")

    for name in fresh:
        send_alert(f"MNQ hit {name} at {prices[name]:.2f}")


if __name__ == "__main__":
    main()

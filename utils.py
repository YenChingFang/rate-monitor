"""共用工具：Telegram 發送、狀態管理"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = Path("last_alert.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(data: dict):
    STATE_FILE.write_text(json.dumps(data))


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10).raise_for_status()
    print("Telegram 訊息發送成功")


def can_send_alert(state: dict, key: str = "last_alert_time", cooldown_minutes: int = 60) -> bool:
    if key not in state:
        return True
    last = datetime.fromisoformat(state[key])
    return (datetime.now(timezone.utc) - last).total_seconds() > cooldown_minutes * 60


def record_alert(state: dict, key: str = "last_alert_time") -> dict:
    state[key] = datetime.now(timezone.utc).isoformat()
    return state


def already_alerted_today(state: dict, key: str) -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return state.get(key) == today


def record_today_alert(state: dict, key: str) -> dict:
    state[key] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return state


def already_sent_daily(state: dict) -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return state.get("last_daily_date") == today


def record_daily(state: dict) -> dict:
    state["last_daily_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return state


def is_daily_report_time() -> bool:
    """台灣時間 09:00 = UTC 01:xx"""
    return datetime.now(timezone.utc).hour == 1

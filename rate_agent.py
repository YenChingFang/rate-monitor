"""
人民幣/台幣匯率監控 Agent
- 每天抓取當日匯率（ExchangeRate-API，免費無需 key）
- 記錄30天歷史（存在 JSON 檔）
- 創30天低點時發 Telegram 提醒
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

# ── 設定（從環境變數讀取）──────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
HISTORY_FILE = Path("rate_history.json")
DAYS_WINDOW = 30


def get_cny_twd_rate() -> float:
    url = "https://open.er-api.com/v6/latest/CNY"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return round(resp.json()["rates"]["TWD"], 4)


def load_history() -> list:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []

def save_history(history: list):
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2))

def update_history(history: list, today_rate: float) -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    history = [h for h in history if h["date"] != today]
    history.append({"date": today, "rate": today_rate})
    cutoff = (datetime.now() - timedelta(days=DAYS_WINDOW)).strftime("%Y-%m-%d")
    history = [h for h in history if h["date"] >= cutoff]
    return sorted(history, key=lambda x: x["date"])

def analyze(history: list, today_rate: float) -> dict:
    rates = [h["rate"] for h in history]
    if not rates:
        return {"is_low": False, "min_30d": today_rate, "max_30d": today_rate, "avg_30d": today_rate, "days": 1}
    return {
        "is_low": today_rate <= min(rates),
        "min_30d": min(rates),
        "max_30d": max(rates),
        "avg_30d": round(sum(rates) / len(rates), 4),
        "days": len(rates),
    }

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10).raise_for_status()
    print("Telegram 訊息發送成功")

def build_message(today_rate: float, a: dict) -> str:
    today = datetime.now().strftime("%Y/%m/%d")
    trend = "📉" if today_rate < a["avg_30d"] else "📈"
    lines = [
        f"💱 人民幣匯率日報 {today}",
        f"",
        f"今日匯率：1 CNY = {today_rate} TWD {trend}",
        f"",
        f"📊 近 {a['days']} 天統計",
        f"  最低：{a['min_30d']} TWD",
        f"  最高：{a['max_30d']} TWD",
        f"  平均：{a['avg_30d']} TWD",
    ]
    if a["is_low"]:
        lines += ["", "🔔 創30天新低！", "現在是近一個月最划算的時機，", "趕快去淘寶下單吧 🛒"]
    return "\n".join(lines)

def main():
    print(f"[{datetime.now()}] 開始執行...")
    today_rate = get_cny_twd_rate()
    print(f"今日匯率：1 CNY = {today_rate} TWD")
    history = update_history(load_history(), today_rate)
    save_history(history)
    analysis = analyze(history, today_rate)
    message = build_message(today_rate, analysis)
    print(f"\n{message}\n")
    send_telegram(message)
    print("完成！")

if __name__ == "__main__":
    main()

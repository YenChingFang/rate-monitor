"""
人民幣/台幣匯率監控 Agent
- 每5分鐘檢查一次（由 GitHub Actions 觸發）
- 每天早上9點發日報
- 7天內創低點時立即發警報（每小時最多通知一次，避免洗版）
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

ALERT_COOLDOWN_FILE = Path("last_alert.json")  # 記錄上次警報時間


# ── 1. 取得當前匯率 ────────────────────────────────────

def get_latest_rate() -> float:
    urls = [
        "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/cny.json",
        "https://latest.currency-api.pages.dev/v1/currencies/cny.json",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return round(resp.json()["cny"]["twd"], 4)
        except Exception:
            continue
    raise Exception("無法取得最新匯率")


def get_rate_on_date(date_str: str) -> float:
    urls = [
        f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/cny.json",
        f"https://{date_str}.currency-api.pages.dev/v1/currencies/cny.json",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return round(resp.json()["cny"]["twd"], 4)
        except Exception:
            continue
    raise Exception(f"無法取得 {date_str} 匯率")


# ── 2. 拉取N天歷史匯率 ────────────────────────────────

def fetch_history(days: int) -> list:
    rates = []
    today = datetime.now()
    for i in range(days, 0, -1):  # 不含今天
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            rate = get_rate_on_date(date_str)
            rates.append({"date": date_str, "rate": rate})
        except Exception:
            pass
    return rates


# ── 3. 冷卻時間控制（避免重複通知）────────────────────

def load_last_alert() -> dict:
    if ALERT_COOLDOWN_FILE.exists():
        return json.loads(ALERT_COOLDOWN_FILE.read_text())
    return {}

def save_last_alert(data: dict):
    ALERT_COOLDOWN_FILE.write_text(json.dumps(data))

def can_send_alert(cooldown_minutes: int = 60) -> bool:
    """距離上次警報超過 cooldown_minutes 分鐘才能再發"""
    data = load_last_alert()
    if "last_alert_time" not in data:
        return True
    last = datetime.fromisoformat(data["last_alert_time"])
    return (datetime.now() - last).total_seconds() > cooldown_minutes * 60

def record_alert():
    save_last_alert({"last_alert_time": datetime.now().isoformat()})


# ── 4. 判斷是否為每天日報時間 ──────────────────────────

def is_daily_report_time() -> bool:
    """台灣時間 09:00（UTC 01:00），允許±5分鐘誤差"""
    now_utc = datetime.utcnow()
    return now_utc.hour == 1 and now_utc.minute < 5


# ── 5. 發送 Telegram ───────────────────────────────────

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10).raise_for_status()
    print("Telegram 訊息發送成功")


# ── 6. 組裝訊息 ────────────────────────────────────────

def build_alert_message(today_rate: float, min_7d: float) -> str:
    now = datetime.now().strftime("%Y/%m/%d %H:%M")
    drop = round(min_7d - today_rate, 4)
    return "\n".join([
        f"🚨 人民幣匯率警報 {now}",
        f"",
        f"現在匯率：1 CNY = {today_rate} TWD",
        f"7天最低：{min_7d} TWD",
        f"比近7天最低還低 {drop} TWD！",
        f"",
        f"💰 現在換人民幣最划算，",
        f"趕快去淘寶下單吧 🛒",
    ])


def build_daily_message(today_rate: float, history_7d: list, history_30d: list) -> str:
    today = datetime.now().strftime("%Y/%m/%d")

    def stats(history):
        rates = [h["rate"] for h in history]
        if not rates:
            return None
        return {
            "min": min(rates),
            "max": max(rates),
            "avg": round(sum(rates) / len(rates), 4),
            "days": len(rates),
        }

    s7 = stats(history_7d)
    s30 = stats(history_30d)
    trend = "📉" if s7 and today_rate < s7["avg"] else "📈"

    lines = [
        f"💱 人民幣匯率日報 {today}",
        f"",
        f"今日匯率：1 CNY = {today_rate} TWD {trend}",
    ]

    if s7:
        rate_range = s7["max"] - s7["min"]
        if rate_range > 0:
            position = int((today_rate - s7["min"]) / rate_range * 100)
            bar = "🟩" * (position // 20) + "⬜" * (5 - position // 20)
            lines += [f"便宜程度(7天)：{bar}（{100 - position}% 划算）"]
        lines += [
            f"",
            f"📊 近7天統計",
            f"  最低：{s7['min']} TWD ← 最划算",
            f"  最高：{s7['max']} TWD",
            f"  平均：{s7['avg']} TWD",
        ]

    if s30:
        lines += [
            f"",
            f"📊 近30天統計",
            f"  最低：{s30['min']} TWD",
            f"  最高：{s30['max']} TWD",
            f"  平均：{s30['avg']} TWD",
        ]

    return "\n".join(lines)


# ── 7. 主流程 ──────────────────────────────────────────

def main():
    now = datetime.now()
    print(f"[{now}] 開始執行...")

    # 取得當前匯率
    current_rate = get_latest_rate()
    print(f"當前匯率：1 CNY = {current_rate} TWD")

    # 拉取7天和30天歷史
    history_7d = fetch_history(7)
    history_30d = fetch_history(30)

    # ── 每日日報（台灣時間 09:00）──
    if is_daily_report_time():
        print("發送每日日報...")
        msg = build_daily_message(current_rate, history_7d, history_30d)
        send_telegram(msg)

    # ── 即時警報（7天低點）──
    rates_7d = [h["rate"] for h in history_7d]
    if rates_7d:
        min_7d = min(rates_7d)
        print(f"7天最低：{min_7d} TWD")
        if current_rate < min_7d:
            if can_send_alert(cooldown_minutes=60):
                print("🚨 創7天新低！發送警報...")
                msg = build_alert_message(current_rate, min_7d)
                send_telegram(msg)
                record_alert()
            else:
                print("警報冷卻中，跳過（避免重複通知）")
        else:
            print("未創新低，不發警報")

    print("完成！")


if __name__ == "__main__":
    main()

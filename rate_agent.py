"""
人民幣/台幣匯率監控 Agent
- 即時從 API 拉取30天歷史匯率計算統計
- 創30天低點時發 Telegram 提醒（台幣越少越划算）
"""

import os
from datetime import datetime, timedelta

import requests

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
DAYS_WINDOW = 30


def get_rate_on_date(date_str: str) -> float:
    """取得指定日期的 CNY→TWD 匯率，date_str 格式：YYYY-MM-DD"""
    url = f"https://open.er-api.com/v6/history/CNY/{date_str}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return round(data["rates"]["TWD"], 4)


def fetch_30d_rates() -> list:
    """拉取最近30天每天的匯率"""
    rates = []
    today = datetime.now()
    print("正在拉取30天歷史匯率...")

    for i in range(DAYS_WINDOW, -1, -1):  # 從30天前到今天
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        try:
            rate = get_rate_on_date(date_str)
            rates.append({"date": date_str, "rate": rate})
            print(f"  {date_str}: {rate} TWD")
        except Exception as e:
            print(f"  {date_str}: 跳過（{e}）")

    return rates


def analyze(history: list, today_rate: float) -> dict:
    # 排除今天，用前29天來比較
    past_rates = [h["rate"] for h in history if h["date"] != datetime.now().strftime("%Y-%m-%d")]

    if not past_rates:
        return {"is_low": False, "min_30d": today_rate, "max_30d": today_rate, "avg_30d": today_rate, "days": 1}

    return {
        "is_low": today_rate <= min(past_rates),
        "min_30d": min(past_rates),
        "max_30d": max(past_rates),
        "avg_30d": round(sum(past_rates) / len(past_rates), 4),
        "days": len(past_rates) + 1,
    }


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10).raise_for_status()
    print("Telegram 訊息發送成功")


def build_message(today_rate: float, a: dict) -> str:
    today = datetime.now().strftime("%Y/%m/%d")
    trend = "📉" if today_rate < a["avg_30d"] else "📈"

    rate_range = a["max_30d"] - a["min_30d"]
    if rate_range > 0:
        position = int((today_rate - a["min_30d"]) / rate_range * 100)
        bar = "🟩" * (position // 20) + "⬜" * (5 - position // 20)
        position_text = f"\n便宜程度：{bar}（{100 - position}% 划算）"
    else:
        position_text = ""

    lines = [
        f"💱 人民幣匯率日報 {today}",
        f"",
        f"今日匯率：1 CNY = {today_rate} TWD {trend}",
        position_text,
        f"",
        f"📊 近 {a['days']} 天統計",
        f"  最低（最划算）：{a['min_30d']} TWD",
        f"  最高（最貴）：  {a['max_30d']} TWD",
        f"  平均：          {a['avg_30d']} TWD",
    ]

    if a["is_low"]:
        lines += [
            f"",
            f"🔔 創30天新低！",
            f"現在換人民幣最划算，",
            f"趕快去淘寶下單吧 🛒",
        ]

    return "\n".join(lines)


def main():
    print(f"[{datetime.now()}] 開始執行...")

    history = fetch_30d_rates()
    if not history:
        print("無法取得匯率資料，中止執行")
        return

    today_rate = history[-1]["rate"]
    print(f"\n今日匯率：1 CNY = {today_rate} TWD")

    analysis = analyze(history, today_rate)
    message = build_message(today_rate, analysis)
    print(f"\n--- 訊息預覽 ---\n{message}\n---")
    send_telegram(message)
    print("完成！")


if __name__ == "__main__":
    main()

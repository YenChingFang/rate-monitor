"""人民幣/台幣匯率即時監控 — 7天創低時發 Telegram 警報"""

from datetime import datetime, timezone, timedelta

import requests

from utils import can_send_alert, load_state, record_alert, save_state, send_telegram

CNY_ALERT_KEY = "cny_last_alert_time"


def get_rate(base: str, target: str, date_str: str = "latest") -> float:
    if date_str == "latest":
        urls = [
            f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{base}.json",
            f"https://latest.currency-api.pages.dev/v1/currencies/{base}.json",
        ]
    else:
        urls = [
            f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/{base}.json",
            f"https://{date_str}.currency-api.pages.dev/v1/currencies/{base}.json",
        ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return round(resp.json()[base][target], 4)
        except Exception:
            continue
    raise Exception(f"無法取得 {base.upper()}/{target.upper()} 匯率")


def fetch_history(days: int) -> list:
    today = datetime.now(timezone.utc)
    rates = []
    for i in range(days, 0, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            rate = get_rate("cny", "twd", date_str)
            rates.append({"date": date_str, "rate": rate})
        except Exception:
            pass
    return rates


def build_alert_message(current: float, min_7d: float) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    drop = round(min_7d - current, 4)
    return "\n".join([
        f"🚨 人民幣匯率警報 {now}",
        "",
        f"現在匯率：1 CNY = {current} TWD",
        f"7天最低：{min_7d} TWD",
        f"比近7天最低還低 {drop} TWD！",
        "",
        "💰 現在換人民幣最划算，",
        "趕快去淘寶下單吧 🛒",
    ])


def main():
    print(f"[{datetime.now(timezone.utc)}] CNY 監控開始...")

    state = load_state()
    current = get_rate("cny", "twd")
    print(f"CNY/TWD: {current}")

    history_7d = fetch_history(7)
    rates_7d = [h["rate"] for h in history_7d]

    if rates_7d:
        min_7d = min(rates_7d)
        print(f"7天最低：{min_7d}")
        if current < min_7d:
            if can_send_alert(state, CNY_ALERT_KEY):
                print("🚨 創7天新低！發送警報...")
                send_telegram(build_alert_message(current, min_7d))
                state = record_alert(state, CNY_ALERT_KEY)
            else:
                print("警報冷卻中，跳過")
        else:
            print("未創新低，不發警報")

    save_state(state)
    print("完成！")


if __name__ == "__main__":
    main()

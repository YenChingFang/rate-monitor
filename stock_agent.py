"""
美股股價監控 Agent
- 監控 VT, VTI, TQQQ 等股票
- 當日跌幅達閾值時發 Telegram 警報（買入提醒）
- 每支股票每天最多通知一次
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import yfinance as yf

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = Path("last_alert.json")

WATCHLIST = {
    "VT":   {"threshold": 5.0,  "name": "Vanguard Total World Stock ETF"},
    "VTI":  {"threshold": 5.0,  "name": "Vanguard Total Stock Market ETF"},
    "TQQQ": {"threshold": 10.0, "name": "ProShares UltraPro QQQ"},
}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(data: dict):
    STATE_FILE.write_text(json.dumps(data))


def already_alerted_today(state: dict, ticker: str) -> bool:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return state.get(f"stock_{ticker}_last_alert_date") == today


def record_stock_alert(state: dict, ticker: str) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state[f"stock_{ticker}_last_alert_date"] = today
    return state


def get_stock_info(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        current = round(info.last_price, 2)
        prev_close = round(info.previous_close, 2)
        change_pct = round((current - prev_close) / prev_close * 100, 2)
        return {
            "current": current,
            "prev_close": prev_close,
            "change_pct": change_pct,
        }
    except Exception as e:
        print(f"[{ticker}] 取得股價失敗: {e}")
        return None


def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10).raise_for_status()
    print("Telegram 訊息發送成功")


def build_stock_alert(ticker: str, name: str, info: dict, threshold: float) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    return "\n".join([
        f"📉 美股下跌警報 {now}",
        f"",
        f"{ticker}｜{name}",
        f"現價：${info['current']}",
        f"昨日收盤：${info['prev_close']}",
        f"今日跌幅：{info['change_pct']}%（閾值 -{threshold}%）",
        f"",
        f"💡 買入訊號，請評估進場時機",
    ])


def main():
    print(f"[{datetime.now(timezone.utc)}] 美股監控開始...")

    state = load_state()

    for ticker, config in WATCHLIST.items():
        print(f"檢查 {ticker}...")

        if already_alerted_today(state, ticker):
            print(f"[{ticker}] 今日已通知，跳過")
            continue

        info = get_stock_info(ticker)
        if not info:
            continue

        print(f"[{ticker}] 現價: ${info['current']}, 跌幅: {info['change_pct']}%")

        if info["change_pct"] <= -config["threshold"]:
            print(f"[{ticker}] 跌幅超過閾值，發送警報！")
            msg = build_stock_alert(ticker, config["name"], info, config["threshold"])
            send_telegram(msg)
            state = record_stock_alert(state, ticker)
        else:
            print(f"[{ticker}] 跌幅未達閾值，不通知")

    save_state(state)
    print("完成！")


if __name__ == "__main__":
    main()

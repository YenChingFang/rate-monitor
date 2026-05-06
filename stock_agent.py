"""美股下跌即時監控 — 跌幅超過閾值時發 Telegram 買入警報"""

from datetime import datetime, timezone, timedelta

import yfinance as yf

from utils import already_alerted_today, load_state, record_today_alert, save_state, send_telegram

WATCHLIST = {
    "VT":   {"threshold": 5.0,  "name": "Vanguard Total World Stock ETF"},
    "VTI":  {"threshold": 5.0,  "name": "Vanguard Total Stock Market ETF"},
    "TQQQ": {"threshold": 10.0, "name": "ProShares UltraPro QQQ"},
}


def get_stock_info(ticker: str) -> dict | None:
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        current = round(info.last_price, 2)
        prev_close = round(info.previous_close, 2)
        change_pct = round((current - prev_close) / prev_close * 100, 2)
        return {"current": current, "prev_close": prev_close, "change_pct": change_pct}
    except Exception as e:
        print(f"[{ticker}] 取得股價失敗: {e}")
        return None


def build_alert(ticker: str, name: str, info: dict, threshold: float) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    return "\n".join([
        f"📉 美股下跌警報 {now}",
        "",
        f"{ticker}｜{name}",
        f"現價：${info['current']}",
        f"昨日收盤：${info['prev_close']}",
        f"今日跌幅：{info['change_pct']}%（閾值 -{threshold}%）",
        "",
        "💡 買入訊號，請評估進場時機",
    ])


def main():
    print(f"[{datetime.now(timezone.utc)}] 美股監控開始...")

    state = load_state()

    for ticker, config in WATCHLIST.items():
        print(f"檢查 {ticker}...")
        alert_key = f"stock_{ticker}_last_alert_date"

        if already_alerted_today(state, alert_key):
            print(f"[{ticker}] 今日已通知，跳過")
            continue

        info = get_stock_info(ticker)
        if not info:
            continue

        print(f"[{ticker}] 現價: ${info['current']}, 跌幅: {info['change_pct']}%")

        if info["change_pct"] <= -config["threshold"]:
            print(f"[{ticker}] 跌幅超過閾值，發送警報！")
            send_telegram(build_alert(ticker, config["name"], info, config["threshold"]))
            state = record_today_alert(state, alert_key)
        else:
            print(f"[{ticker}] 跌幅未達閾值，不通知")

    save_state(state)
    print("完成！")


if __name__ == "__main__":
    main()

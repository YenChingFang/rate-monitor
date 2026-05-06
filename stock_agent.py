"""大盤即時監控 — 近1小時跌幅超過閾值時發 Telegram 警報"""

from datetime import datetime, timezone, timedelta

import yfinance as yf

from utils import can_send_alert, load_state, record_alert, save_state, send_telegram

MARKET_INDICES = {
    "^GSPC": {"name": "S&P 500",           "threshold": 2.0, "region": "🇺🇸"},
    "^IXIC": {"name": "NASDAQ Composite",   "threshold": 2.5, "region": "🇺🇸"},
    "^TWII": {"name": "加權指數（TAIEX）",   "threshold": 2.0, "region": "🇹🇼"},
}

COOLDOWN_MINUTES = 60


def get_1h_change(ticker: str) -> dict | None:
    try:
        hist = yf.Ticker(ticker).history(period="1d", interval="1m")
        if len(hist) < 2:
            print(f"[{ticker}] 資料不足，跳過")
            return None

        last_time = hist.index[-1].to_pydatetime().astimezone(timezone.utc)
        if (datetime.now(timezone.utc) - last_time).total_seconds() > 1800:
            print(f"[{ticker}] 市場已收盤，跳過")
            return None

        current = round(hist["Close"].iloc[-1], 2)
        idx_1h = max(0, len(hist) - 61)
        price_1h_ago = round(hist["Close"].iloc[idx_1h], 2)
        change_pct = round((current - price_1h_ago) / price_1h_ago * 100, 2)
        return {"current": current, "price_1h_ago": price_1h_ago, "change_pct": change_pct}
    except Exception as e:
        print(f"[{ticker}] 取得資料失敗: {e}")
        return None


def build_alert(ticker: str, config: dict, info: dict) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    label = "美股" if config["region"] == "🇺🇸" else "台股"
    return "\n".join([
        f"📉 {config['region']} {label}大盤下跌警報 {now}",
        "",
        config["name"],
        f"現值：{info['current']:,.2f}",
        f"1小時前：{info['price_1h_ago']:,.2f}",
        f"近1小時跌幅：{info['change_pct']}%（閾值 -{config['threshold']}%）",
        "",
        "⚠️ 大盤急跌，留意進場時機",
    ])


def main():
    print(f"[{datetime.now(timezone.utc)}] 大盤監控開始...")

    state = load_state()

    for ticker, config in MARKET_INDICES.items():
        print(f"檢查 {config['name']}...")
        alert_key = f"index_{ticker}_last_alert_time"

        if not can_send_alert(state, alert_key, COOLDOWN_MINUTES):
            print(f"[{ticker}] 警報冷卻中，跳過")
            continue

        info = get_1h_change(ticker)
        if not info:
            continue

        print(f"[{ticker}] 現值: {info['current']}, 近1小時跌幅: {info['change_pct']}%")

        if info["change_pct"] <= -config["threshold"]:
            print(f"[{ticker}] 跌幅超過閾值，發送警報！")
            send_telegram(build_alert(ticker, config, info))
            state = record_alert(state, alert_key)
        else:
            print(f"[{ticker}] 跌幅未達閾值，不通知")

    save_state(state)
    print("完成！")


if __name__ == "__main__":
    main()

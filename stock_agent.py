"""股票即時監控
- 美股：當日跌幅超過閾值（相對前一日收盤），每支每天通知一次
- 台股大盤：近1小時跌幅超過 5%，60 分鐘冷卻
"""

from datetime import datetime, timezone, timedelta

import yfinance as yf

from utils import (
    already_alerted_today, can_send_alert, load_state,
    record_alert, record_today_alert, save_state, send_telegram,
)

US_WATCHLIST = {
    "VT":   {"threshold": 5.0,  "name": "Vanguard Total World Stock ETF"},
    "VTI":  {"threshold": 5.0,  "name": "Vanguard Total Stock Market ETF"},
    "TQQQ": {"threshold": 10.0, "name": "ProShares UltraPro QQQ"},
}

TAIEX_TICKER = "^TWII"
TAIEX_THRESHOLD = 5.0
TAIEX_ALERT_KEY = "taiex_last_alert_time"


# ── 美股：比對前一日收盤 ───────────────────────────────

def get_us_stock_info(ticker: str) -> dict | None:
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


def build_us_alert(ticker: str, name: str, info: dict, threshold: float) -> str:
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


# ── 台股大盤：比對近1小時價格 ─────────────────────────

def get_taiex_1h_change() -> dict | None:
    try:
        hist = yf.Ticker(TAIEX_TICKER).history(period="1d", interval="1m")
        if len(hist) < 2:
            print("[TAIEX] 資料不足，跳過")
            return None

        last_time = hist.index[-1].to_pydatetime().astimezone(timezone.utc)
        if (datetime.now(timezone.utc) - last_time).total_seconds() > 1800:
            print("[TAIEX] 市場已收盤，跳過")
            return None

        current = round(hist["Close"].iloc[-1], 2)
        idx_1h = max(0, len(hist) - 61)
        price_1h_ago = round(hist["Close"].iloc[idx_1h], 2)
        change_pct = round((current - price_1h_ago) / price_1h_ago * 100, 2)
        return {"current": current, "price_1h_ago": price_1h_ago, "change_pct": change_pct}
    except Exception as e:
        print(f"[TAIEX] 取得資料失敗: {e}")
        return None


def build_taiex_alert(info: dict) -> str:
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d %H:%M")
    return "\n".join([
        f"📉 台股大盤下跌警報 {now}",
        "",
        "加權指數（TAIEX）",
        f"現值：{info['current']:,.0f}",
        f"1小時前：{info['price_1h_ago']:,.0f}",
        f"近1小時跌幅：{info['change_pct']}%（閾值 -{TAIEX_THRESHOLD}%）",
        "",
        "⚠️ 大盤急跌，留意進場時機",
    ])


# ── 主流程 ─────────────────────────────────────────────

def main():
    print(f"[{datetime.now(timezone.utc)}] 股票監控開始...")

    state = load_state()

    # 美股監控
    for ticker, config in US_WATCHLIST.items():
        print(f"檢查 {ticker}...")
        alert_key = f"stock_{ticker}_last_alert_date"

        if already_alerted_today(state, alert_key):
            print(f"[{ticker}] 今日已通知，跳過")
            continue

        info = get_us_stock_info(ticker)
        if not info:
            continue

        print(f"[{ticker}] 現價: ${info['current']}, 跌幅: {info['change_pct']}%")

        if info["change_pct"] <= -config["threshold"]:
            print(f"[{ticker}] 跌幅超過閾值，發送警報！")
            send_telegram(build_us_alert(ticker, config["name"], info, config["threshold"]))
            state = record_today_alert(state, alert_key)
        else:
            print(f"[{ticker}] 跌幅未達閾值，不通知")

    # 台股大盤監控
    print("檢查台股大盤（TAIEX）...")
    if can_send_alert(state, TAIEX_ALERT_KEY, cooldown_minutes=60):
        info = get_taiex_1h_change()
        if info:
            print(f"[TAIEX] 現值: {info['current']}, 近1小時跌幅: {info['change_pct']}%")
            if info["change_pct"] <= -TAIEX_THRESHOLD:
                print("[TAIEX] 急跌超過閾值，發送警報！")
                send_telegram(build_taiex_alert(info))
                state = record_alert(state, TAIEX_ALERT_KEY)
            else:
                print("[TAIEX] 跌幅未達閾值，不通知")
    else:
        print("[TAIEX] 警報冷卻中，跳過")

    save_state(state)
    print("完成！")


if __name__ == "__main__":
    main()

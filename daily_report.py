"""每日市場日報 — 台灣時間早上9點發送，包含美股、台股、美金、人民幣"""

from datetime import datetime, timezone, timedelta

import requests
import yfinance as yf

from utils import (
    already_sent_daily, load_state,
    record_daily, save_state, send_telegram,
)

US_INDICES = {
    "^GSPC": {"name": "S&P 500"},
    "^IXIC": {"name": "NASDAQ Composite"},
}

TW_INDICES = {
    "^TWII": {"name": "加權指數（TAIEX）"},
}

US_STOCKS = {
    "VT":   {"threshold": 5.0},
    "VTI":  {"threshold": 5.0},
    "TQQQ": {"threshold": 10.0},
}

TW_STOCKS = {
    "0050.TW": {"name": "元大台灣50"},
    "2330.TW": {"name": "台積電"},
}


# ── 資料取得 ───────────────────────────────────────────

def get_exchange_rate(base: str, target: str, date_str: str = "latest") -> float:
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
    raise Exception(f"無法取得 {base.upper()}/{target.upper()} ({date_str}) 匯率")


def fetch_history(base: str, target: str, days: int) -> list:
    today = datetime.now(timezone.utc)
    rates = []
    for i in range(days, 0, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            rate = get_exchange_rate(base, target, date_str)
            rates.append({"date": date_str, "rate": rate})
        except Exception:
            pass
    return rates


def fetch_stock(ticker: str) -> dict | None:
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


# ── 訊息組裝 ───────────────────────────────────────────

def _pct_str(pct: float) -> str:
    emoji = "📉" if pct < 0 else "🟢"
    return f"{pct:+.2f}% {emoji}"


def _rate_section(label: str, rate: float, history_7d: list, history_30d: list, unit: str) -> list:
    def stats(history):
        rates = [h["rate"] for h in history]
        if not rates:
            return None
        return {"min": min(rates), "max": max(rates), "avg": round(sum(rates) / len(rates), 4)}

    s7 = stats(history_7d)
    s30 = stats(history_30d)
    trend = "📉" if s7 and rate < s7["avg"] else "📈"
    lines = [label, f"  1 {unit} = {rate} TWD {trend}"]

    if s7:
        rate_range = s7["max"] - s7["min"]
        if rate_range > 0:
            position = int((rate - s7["min"]) / rate_range * 100)
            bar = "🟩" * (position // 20) + "⬜" * (5 - position // 20)
            lines.append(f"  便宜程度(7天)：{bar}（{100 - position}% 划算）")
        lines.append(f"  近7天：最低 {s7['min']} ← 最划算  最高 {s7['max']}  平均 {s7['avg']}")

    if s30:
        lines.append(f"  近30天：最低 {s30['min']}  最高 {s30['max']}  平均 {s30['avg']}")

    return lines


def build_message(
    us_indices: dict,
    tw_indices: dict,
    us_stocks: dict,
    tw_stocks: dict,
    usd_rate: float,
    usd_7d: list,
    usd_30d: list,
    cny_rate: float,
    cny_7d: list,
    cny_30d: list,
) -> str:
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y/%m/%d")
    lines = [f"📊 每日市場日報 {today}", ""]

    # 美股大盤
    if us_indices:
        lines.append("🇺🇸 美股大盤")
        for ticker, data in us_indices.items():
            name = US_INDICES[ticker]["name"]
            lines.append(f"  {name:<22} {data['current']:>10,.2f}  {_pct_str(data['change_pct'])}")

    # 美股個股
    if us_stocks:
        lines += ["", "🇺🇸 美股"]
        for ticker, data in us_stocks.items():
            threshold = US_STOCKS[ticker]["threshold"]
            pct = data["change_pct"]
            alert = f"  ⚠️ 跌>{threshold}%，已觸發通知" if pct <= -threshold else ""
            lines.append(f"  {ticker:<5} ${data['current']}  {_pct_str(pct)}{alert}")

    # 台股大盤
    if tw_indices:
        lines += ["", "🇹🇼 台股大盤"]
        for ticker, data in tw_indices.items():
            name = TW_INDICES[ticker]["name"]
            lines.append(f"  {name}  {data['current']:,.2f}  {_pct_str(data['change_pct'])}")

    # 台股個股
    if tw_stocks:
        lines += ["", "🇹🇼 台股"]
        for ticker, data in tw_stocks.items():
            short = ticker.replace(".TW", "")
            lines.append(f"  {short} {data['name']}  NT${data['current']}  {_pct_str(data['change_pct'])}")

    # 美金匯率
    lines += [""] + _rate_section("💵 美金匯率", usd_rate, usd_7d, usd_30d, "USD")

    # 人民幣匯率
    lines += [""] + _rate_section("🀄 人民幣匯率", cny_rate, cny_7d, cny_30d, "CNY")

    return "\n".join(lines)


# ── 主流程 ─────────────────────────────────────────────

def main():
    import os
    force = os.getenv("FORCE_DAILY", "").lower() in ("true", "1")
    daily_trigger = os.getenv("DAILY_TRIGGER", "").lower() in ("true", "1")

    print(f"[{datetime.now(timezone.utc)}] 日報檢查{'（強制模式）' if force else '（專屬 cron）' if daily_trigger else ''}...")

    if not force and not daily_trigger:
        print("非日報時間，跳過")
        return

    state = load_state()
    if not force and already_sent_daily(state):
        print("今天日報已發過，跳過")
        return

    print("開始收集市場資料...")

    us_indices = {}
    for ticker, config in US_INDICES.items():
        info = fetch_stock(ticker)
        if info:
            us_indices[ticker] = info

    tw_indices = {}
    for ticker, config in TW_INDICES.items():
        info = fetch_stock(ticker)
        if info:
            tw_indices[ticker] = info

    us_stocks = {}
    for ticker in US_STOCKS:
        info = fetch_stock(ticker)
        if info:
            us_stocks[ticker] = info

    tw_stocks = {}
    for ticker, config in TW_STOCKS.items():
        info = fetch_stock(ticker)
        if info:
            tw_stocks[ticker] = {**info, "name": config["name"]}

    usd_rate = get_exchange_rate("usd", "twd")
    usd_7d = fetch_history("usd", "twd", 7)
    usd_30d = fetch_history("usd", "twd", 30)

    cny_rate = get_exchange_rate("cny", "twd")
    cny_7d = fetch_history("cny", "twd", 7)
    cny_30d = fetch_history("cny", "twd", 30)

    msg = build_message(us_indices, tw_indices, us_stocks, tw_stocks, usd_rate, usd_7d, usd_30d, cny_rate, cny_7d, cny_30d)
    send_telegram(msg)

    state = record_daily(state)
    save_state(state)
    print("日報發送完成！")


if __name__ == "__main__":
    main()

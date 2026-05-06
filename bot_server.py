"""
市場監控 Telegram Bot - Webhook 伺服器
支援指令：
  /rate               → 查詢 CNY 對 TWD
  /rate USD           → 查詢 USD 對 TWD
  /rate CNY/USD       → 查詢任意幣別對
  /price 0050         → 查詢台股即時股價（純數字自動補 .TW）
  /price TQQQ         → 查詢美股即時股價
  /help               → 查看所有指令
"""

import os

import yfinance as yf
from flask import Flask, request
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

KNOWN_NAMES = {
    "0050.TW": "元大台灣50",
    "2330.TW": "台積電",
    "^TWII":   "加權指數（TAIEX）",
    "^GSPC":   "S&P 500",
    "^IXIC":   "NASDAQ Composite",
    "VT":      "Vanguard Total World",
    "VTI":     "Vanguard Total Market",
    "TQQQ":    "ProShares UltraPro QQQ",
    "QQQ":     "Invesco QQQ",
    "SPY":     "SPDR S&P 500 ETF",
}


# ── 匯率查詢 ───────────────────────────────────────────

def get_rate(from_currency: str, to_currency: str) -> float:
    from_c = from_currency.lower()
    to_c = to_currency.lower()
    urls = [
        f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/{from_c}.json",
        f"https://latest.currency-api.pages.dev/v1/currencies/{from_c}.json",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if to_c in data[from_c]:
                    return round(data[from_c][to_c], 4)
        except Exception:
            continue
    raise Exception(f"查不到 {from_currency.upper()} → {to_currency.upper()} 的匯率，請確認幣別代碼是否正確")


CURRENCY_NAMES = {
    "CNY": "人民幣", "TWD": "新台幣", "NTD": "新台幣",
    "USD": "美元",  "JPY": "日圓",   "EUR": "歐元",
    "HKD": "港幣",  "GBP": "英鎊",   "KRW": "韓元",
    "SGD": "新加坡幣", "AUD": "澳幣", "CAD": "加幣", "THB": "泰銖",
}

def get_currency_name(code: str) -> str:
    return CURRENCY_NAMES.get(code.upper(), code.upper())

def normalize(code: str) -> str:
    return "TWD" if code.upper() == "NTD" else code.upper()


# ── 股價查詢 ───────────────────────────────────────────

def parse_ticker(raw: str) -> str:
    """純數字視為台股，補 .TW；其他直接大寫"""
    raw = raw.strip()
    if raw.isdigit():
        return f"{raw}.TW"
    return raw.upper()


def get_stock_price(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.fast_info
    current = info.last_price
    prev_close = info.previous_close
    if current is None or prev_close is None:
        raise Exception(f"查不到 {ticker} 的股價，請確認代碼是否正確")
    change = round(current - prev_close, 2)
    change_pct = round((current - prev_close) / prev_close * 100, 2)
    currency = getattr(info, "currency", "USD")
    day_high = getattr(info, "day_high", None)
    day_low = getattr(info, "day_low", None)
    return {
        "current": round(current, 2),
        "prev_close": round(prev_close, 2),
        "change": change,
        "change_pct": change_pct,
        "currency": currency,
        "day_high": round(day_high, 2) if day_high else None,
        "day_low": round(day_low, 2) if day_low else None,
    }


# ── 指令處理 ───────────────────────────────────────────

def handle_rate(args: list) -> str:
    try:
        if len(args) == 0:
            rate = get_rate("CNY", "TWD")
            return (
                f"💱 即時匯率\n\n"
                f"1 人民幣 (CNY) = {rate} 新台幣 (TWD)\n\n"
                f"💡 /rate USD     查詢美元對台幣\n"
                f"💡 /rate CNY/USD 查詢人民幣對美元"
            )
        raw = args[0]
        if "/" in raw:
            parts = raw.split("/")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return "❌ 格式錯誤，範例：/rate CNY/USD"
            from_c = normalize(parts[0])
            to_c = normalize(parts[1])
        else:
            from_c = normalize(raw)
            to_c = "TWD"
        rate = get_rate(from_c, to_c)
        from_name = get_currency_name(from_c)
        to_name = get_currency_name(to_c)
        return f"💱 即時匯率\n\n1 {from_name} ({from_c}) = {rate} {to_name} ({to_c})"
    except Exception as e:
        return f"❌ {e}"


def handle_price(args: list) -> str:
    if not args:
        return (
            "❌ 請輸入股票代碼\n\n"
            "範例：\n"
            "  /price 0050    台股（純數字自動補 .TW）\n"
            "  /price 2330\n"
            "  /price TQQQ   美股\n"
            "  /price SPY"
        )
    try:
        ticker = parse_ticker(args[0])
        name = KNOWN_NAMES.get(ticker, "")
        data = get_stock_price(ticker)

        prefix = "NT$" if data["currency"] == "TWD" else "$"
        emoji = "🟢" if data["change_pct"] >= 0 else "📉"
        sign = "+" if data["change"] >= 0 else ""
        display_ticker = ticker.replace(".TW", "") if ticker.endswith(".TW") else ticker

        lines = [
            f"📊 {display_ticker}" + (f"  {name}" if name else ""),
            "",
            f"現價：{prefix}{data['current']:,}",
            f"今日漲跌：{sign}{data['change']} ({sign}{data['change_pct']}%) {emoji}",
            f"昨日收盤：{prefix}{data['prev_close']:,}",
        ]
        if data["day_high"] and data["day_low"]:
            lines.append(f"今日區間：{prefix}{data['day_low']:,} – {prefix}{data['day_high']:,}")

        return "\n".join(lines)
    except Exception as e:
        return f"❌ {e}"


def handle_start() -> str:
    return (
        "👋 歡迎使用市場監控 Bot！\n"
        "\n"
        "這個 Bot 幫你追蹤匯率與股市，在最佳時機提醒你。\n"
        "\n"
        "🔔 自動通知功能\n"
        "  • 每天早上 9 點發送市場日報\n"
        "    （美股、台股、美金、人民幣匯率）\n"
        "  • S&P 500 / NASDAQ 近1小時急跌 → 即時警報\n"
        "  • 台股大盤近1小時急跌 → 即時警報\n"
        "  • 人民幣匯率創7天新低 → 即時警報\n"
        "\n"
        "🤖 互動查詢功能\n"
        "  /price 0050   查詢台股即時股價\n"
        "  /price TQQQ   查詢美股即時股價\n"
        "  /rate         查詢人民幣對新台幣\n"
        "  /rate USD     查詢美金對新台幣\n"
        "\n"
        "輸入 /help 查看完整指令說明 📖"
    )


def handle_help() -> str:
    return (
        "📖 指令說明\n"
        "\n"
        "/price [代碼]\n"
        "  查詢即時股價\n"
        "  台股（純數字自動補 .TW）：\n"
        "    /price 0050   /price 2330\n"
        "  美股：\n"
        "    /price TQQQ   /price SPY\n"
        "\n"
        "/rate\n"
        "  查詢人民幣對新台幣匯率\n"
        "\n"
        "/rate [幣別]\n"
        "  查詢指定幣別對新台幣\n"
        "  例：/rate USD   /rate JPY\n"
        "\n"
        "/rate [幣別A]/[幣別B]\n"
        "  查詢任意兩種幣別\n"
        "  例：/rate CNY/USD   /rate USD/JPY\n"
        "\n"
        "常用幣別：CNY USD JPY EUR HKD SGD AUD GBP"
    )


def process_message(chat_id: int, text: str):
    text = text.strip()
    if not text.startswith("/"):
        reply = "請輸入 /help 查看可用指令 😊"
    else:
        parts = text.split()
        command = parts[0].lower().split("@")[0]
        args = parts[1:]

        if command == "/rate":
            reply = handle_rate(args)
        elif command == "/price":
            reply = handle_price(args)
        elif command == "/start":
            reply = handle_start()
        elif command == "/help":
            reply = handle_help()
        else:
            reply = "❓ 不認識這個指令，請輸入 /help 查看可用指令"

    send_message(chat_id, reply)


# ── Telegram 發送訊息 ──────────────────────────────────

def send_message(chat_id: int, text: str):
    requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


# ── Flask Webhook ──────────────────────────────────────

@app.route(f"/webhook/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message") or data.get("edited_message")
    if message and "text" in message:
        chat_id = message["chat"]["id"]
        text = message["text"]
        process_message(chat_id, text)
    return "ok"


@app.route("/")
def index():
    return "Bot is running! 🤖"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

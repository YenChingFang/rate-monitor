"""
人民幣匯率 Telegram Bot - Webhook 伺服器
支援指令：
  /rate           → 查詢 CNY 對 TWD
  /rate USD       → 查詢 USD 對 TWD
  /rate CNY/USD   → 查詢 CNY 對 USD（斜線分隔）
  /help           → 查看所有指令
"""

import os
from flask import Flask, request
import requests

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


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
    """NTD 統一轉成 TWD"""
    return "TWD" if code.upper() == "NTD" else code.upper()


# ── 指令處理 ───────────────────────────────────────────

def handle_rate(args: list) -> str:
    try:
        if len(args) == 0:
            # /rate → CNY 對 TWD
            rate = get_rate("CNY", "TWD")
            return (
                f"💱 即時匯率\n"
                f"\n"
                f"1 人民幣 (CNY) = {rate} 新台幣 (TWD)\n"
                f"\n"
                f"💡 /rate USD     查詢美元對台幣\n"
                f"💡 /rate CNY/USD 查詢人民幣對美元"
            )

        raw = args[0]

        if "/" in raw:
            # /rate CNY/USD
            parts = raw.split("/")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                return "❌ 格式錯誤，範例：/rate CNY/USD"
            from_c = normalize(parts[0])
            to_c = normalize(parts[1])
        else:
            # /rate USD → USD 對 TWD
            from_c = normalize(raw)
            to_c = "TWD"

        rate = get_rate(from_c, to_c)
        from_name = get_currency_name(from_c)
        to_name = get_currency_name(to_c)
        return (
            f"💱 即時匯率\n"
            f"\n"
            f"1 {from_name} ({from_c}) = {rate} {to_name} ({to_c})"
        )

    except Exception as e:
        return f"❌ {e}"


def handle_help() -> str:
    return (
        "📖 指令說明\n"
        "\n"
        "/rate\n"
        "  查詢人民幣對新台幣匯率\n"
        "\n"
        "/rate [幣別]\n"
        "  查詢指定幣別對新台幣匯率\n"
        "  例：/rate USD\n"
        "  例：/rate JPY\n"
        "\n"
        "/rate [幣別A]/[幣別B]\n"
        "  查詢任意兩種幣別匯率\n"
        "  例：/rate CNY/USD\n"
        "  例：/rate USD/JPY\n"
        "\n"
        "常用幣別代碼：\n"
        "  CNY 人民幣   USD 美元\n"
        "  JPY 日圓     EUR 歐元\n"
        "  HKD 港幣     KRW 韓元\n"
        "  GBP 英鎊     SGD 新加坡幣\n"
        "  AUD 澳幣     THB 泰銖"
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
        elif command in ("/help", "/start"):
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

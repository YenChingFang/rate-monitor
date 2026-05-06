"""
執行這個腳本來設定 Telegram Webhook URL 與指令清單
在 Render 部署完成後執行一次即可

用法：
  TELEGRAM_TOKEN=你的token WEBHOOK_URL=https://你的render網址 python set_webhook.py
"""
import os
import requests

token = os.environ["TELEGRAM_TOKEN"]
webhook_url = os.environ["WEBHOOK_URL"]
api = f"https://api.telegram.org/bot{token}"

# 設定 Webhook
full_url = f"{webhook_url}/webhook/{token}"
resp = requests.post(f"{api}/setWebhook", json={"url": full_url})
print("setWebhook:", resp.json())

# 設定指令清單（輸入 / 時自動顯示）
commands = [
    {"command": "price", "description": "查詢即時股價，例：/price 0050 或 /price TQQQ"},
    {"command": "rate",  "description": "查詢匯率，例：/rate 或 /rate USD"},
    {"command": "help",  "description": "查看所有指令說明"},
]
resp = requests.post(f"{api}/setMyCommands", json={"commands": commands})
print("setMyCommands:", resp.json())

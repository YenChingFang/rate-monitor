"""
執行這個腳本來設定 Telegram Webhook URL
在 Render 部署完成後執行一次即可

用法：
  TELEGRAM_TOKEN=你的token WEBHOOK_URL=https://你的render網址 python set_webhook.py
"""
import os
import requests

token = os.environ["TELEGRAM_TOKEN"]
webhook_url = os.environ["WEBHOOK_URL"]

full_url = f"{webhook_url}/webhook/{token}"
resp = requests.post(
    f"https://api.telegram.org/bot{token}/setWebhook",
    json={"url": full_url}
)
print(resp.json())

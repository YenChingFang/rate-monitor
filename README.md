# 💱 CNY/TWD Exchange Rate Monitor Bot

A Telegram bot that monitors CNY to TWD exchange rates, sends daily reports every morning, and alerts you instantly when the rate hits a 7-day low — so you know the best time to shop on Taobao.

---

## Features

- **Instant Alerts**: Checks every 5 minutes via GitHub Actions; notifies you when the rate drops below the 7-day low
- **Daily Report**: Sends a morning summary at 09:00 (Taiwan time) with 7-day and 30-day statistics
- **Interactive Commands**: Query any currency pair on demand via Telegram
- **Anti-spam**: Alert cooldown of 60 minutes to avoid repeated notifications
- **Completely Free**: GitHub Actions free tier + Render free tier + no-key exchange rate API

---

## Notification Examples

**Instant Alert**
```
🚨 Exchange Rate Alert 2026/03/31 14:35

Current Rate: 1 CNY = 4.5800 TWD
7-Day Low: 4.5950 TWD
0.015 TWD lower than the 7-day low!

💰 Best time to buy CNY — go shop on Taobao! 🛒
```

**Daily Report**
```
💱 Daily Rate Report 2026/03/31

Today: 1 CNY = 4.6361 TWD 📈
Value (7-day): 🟩🟩⬜⬜⬜ (38% cheap)

📊 7-Day Stats
  Low (best):  4.5800 TWD
  High:        4.6800 TWD
  Average:     4.6300 TWD

📊 30-Day Stats
  Low:         4.5500 TWD
  High:        4.7100 TWD
  Average:     4.6200 TWD
```

**Bot Commands**
```
/rate              → CNY to TWD (default)
/rate USD          → USD to TWD
/rate CNY/USD      → CNY to USD (any pair)
/help              → Show all commands
```

---

## Architecture

```
GitHub Actions (every 5 min)
  └── rate_agent.py
        ├── Fetch latest rate (fawazahmed0/exchange-api)
        ├── Compare against 7-day history
        ├── Send alert if new 7-day low
        └── Send daily report at 09:00 TWD

Render (always on webhook server)
  └── bot_server.py (Flask)
        └── Handle /rate and /help commands
```

---

## Setup

### 1. Create a Telegram Bot

1. Search `@BotFather` on Telegram, send `/newbot`
2. Follow the prompts to get your **Bot Token**
3. Send any message to your bot, then open:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Find `"chat":{"id": <number>}` — that number is your **Chat ID**

### 2. GitHub Actions (Daily Report + Alerts)

**File structure:**
```
your-repo/
├── README.md
├── rate_agent.py
└── .github/
    └── workflows/
        └── rate_monitor.yml
```

**Add GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `TELEGRAM_TOKEN` | Your Bot Token |
| `TELEGRAM_CHAT_ID` | Your Chat ID |

### 3. Render (Bot Commands)

**File structure:**
```
your-repo/
├── bot_server.py
├── requirements.txt
└── render.yaml
```

1. Sign up at [render.com](https://render.com) and connect your GitHub repo
2. Create a **Web Service**, set start command to:
   ```
   gunicorn bot_server:app
   ```
3. Add environment variable: `TELEGRAM_TOKEN` = your Bot Token
4. Deploy and note your Render URL (e.g. `https://rate-monitor.onrender.com`)

### 4. Register Webhook (once only)

After Render deployment completes, run locally:

```bash
pip3 install requests
TELEGRAM_TOKEN=your_token WEBHOOK_URL=https://your-app.onrender.com python3 set_webhook.py
```

You should see `{"ok": true}` — setup complete!

---

## Tech Stack

| Item | Detail |
|---|---|
| Exchange Rate API | [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api) — free, no key required |
| Scheduled Jobs | GitHub Actions (free tier, ~1500 min/month) |
| Check Frequency | Every 5 minutes (`*/5 * * * *`) |
| Daily Report Time | 09:00 Taiwan time (UTC+8) |
| Alert Cooldown | 60 minutes |
| Bot Server | Render free tier (Flask + Gunicorn) |
| Notifications | Telegram Bot API |

---

## Notes

- GitHub Actions free tier provides 2,000 min/month; running every 5 minutes uses ~1,500 min/month, staying within the free limit
- Render free tier sleeps after 15 minutes of inactivity; the bot will wake up automatically when a command is received (first response may take a few seconds)
- `fawazahmed0/exchange-api` updates rates once per day, so the 5-minute checks will return the same value within the same day — upgrade to a paid real-time API if you need live tick data
- Exchange rates are for reference only; actual rates may vary by bank or platform

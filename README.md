# 📊 Market Monitor Bot

A Telegram bot that monitors exchange rates and global market indices, sends a daily morning report, and alerts you instantly when rates or markets make significant moves.

---

## Features

- **Daily Report** — Every morning at 09:00 (Taiwan time): US stocks, Taiwan stocks, USD/TWD, CNY/TWD with 7-day and 30-day stats
- **Market Index Alerts** — Notifies you when S&P 500, NASDAQ, or TAIEX drops significantly within an hour
- **CNY Rate Alert** — Instant alert when CNY/TWD hits a 7-day low (best time to buy CNY)
- **Interactive Bot** — Query any stock price or currency pair on demand via Telegram commands
- **Anti-spam** — Per-index 60-minute cooldown; daily report sent only once per day
- **Completely Free** — GitHub Actions free tier + Render free tier + no-key APIs

---

## Notification Examples

**Daily Report**
```
📊 每日市場日報 2026/05/07

🇺🇸 美股
  VT    $152.12  +0.81% 🟢
  VTI   $356.99  -0.83% 📉
  TQQQ  $67.39   -4.19% 📉

🇹🇼 台股
  0050 元大台灣50  NT$185.5  +1.50% 🟢
  2330 台積電      NT$935.0  -0.85% 📉

💵 美金匯率
  1 USD = 32.45 TWD 📈
  便宜程度(7天)：🟩🟩⬜⬜⬜（60% 划算）
  近7天：最低 32.10 ← 最划算  最高 32.80  平均 32.44
  近30天：最低 31.90  最高 33.10  平均 32.50

🀄 人民幣匯率
  1 CNY = 4.43 TWD 📈
  便宜程度(7天)：🟩🟩⬜⬜⬜（60% 划算）
  近7天：最低 4.40 ← 最划算  最高 4.45  平均 4.42
  近30天：最低 4.38  最高 4.48  平均 4.43
```

**Market Index Alert**
```
📉 🇺🇸 美股大盤下跌警報 2026/05/07 22:45

S&P 500
現值：5,102.45
1小時前：5,210.20
近1小時跌幅：-2.07%（閾值 -2%）

⚠️ 大盤急跌，留意進場時機
```

**CNY Rate Alert**
```
🚨 人民幣匯率警報 2026/05/07 14:35

現在匯率：1 CNY = 4.3800 TWD
7天最低：4.3950 TWD
比近7天最低還低 0.015 TWD！

💰 現在換人民幣最划算，
趕快去淘寶下單吧 🛒
```

**Bot Commands**
```
/price 0050     → 台股即時股價（純數字自動補 .TW）
/price TQQQ     → 美股即時股價
/rate           → CNY 對 TWD 匯率
/rate USD       → USD 對 TWD 匯率
/rate CNY/USD   → 任意幣別對
/help           → 查看所有指令
```

---

## Architecture

```
GitHub Actions (every 10 min)
  ├── rate_agent.py     → CNY/TWD 7-day low alert
  ├── stock_agent.py    → Market index 1-hour drop alerts
  └── daily_report.py   → Morning report at 09:00 TWD

Render (always-on webhook server)
  └── bot_server.py (Flask)
        ├── /price [ticker]  Real-time stock price
        ├── /rate [pair]     Exchange rate query
        └── /help            Command list

Shared
  └── utils.py          → Telegram sender, state management
```

---

## Alert Thresholds

| Monitor | Condition | Cooldown |
|---|---|---|
| S&P 500 | 1-hour drop ≥ 2% | 60 min |
| NASDAQ | 1-hour drop ≥ 2.5% | 60 min |
| TAIEX | 1-hour drop ≥ 2% | 60 min |
| CNY/TWD | New 7-day low | 60 min |

---

## Setup

### 1. Create a Telegram Bot

1. Search `@BotFather` on Telegram, send `/newbot`
2. Follow prompts to get your **Bot Token**
3. Send any message to your bot, then open:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
4. Find `"chat":{"id": <number>}` — that's your **Chat ID**

### 2. GitHub Actions (Alerts + Daily Report)

Add **GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `TELEGRAM_TOKEN` | Your Bot Token |
| `TELEGRAM_CHAT_ID` | Your Chat ID |

### 3. Render (Bot Commands)

1. Sign up at [render.com](https://render.com) and connect your GitHub repo
2. Create a **Web Service** — `render.yaml` will auto-configure it
3. Add environment variable: `TELEGRAM_TOKEN` = your Bot Token
4. Deploy and note your Render URL (e.g. `https://rate-bot.onrender.com`)

### 4. Register Webhook + Commands (once only)

After Render deployment completes, run:

```bash
TELEGRAM_TOKEN=your_token WEBHOOK_URL=https://your-app.onrender.com python set_webhook.py
```

This sets the webhook URL and registers slash commands for autocomplete in Telegram.

### 5. Manual Triggers (GitHub Actions)

Go to **Actions → 市場監控 → Run workflow** to access manual options:

| Option | Description |
|---|---|
| Force daily report | Send the daily report immediately, ignoring time |
| Test notification | Send a Telegram ping to confirm the system works |
| Test alerts | Send sample market drop alerts with real current prices |

---

## Tech Stack

| Item | Detail |
|---|---|
| Exchange Rate API | [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api) — free, no key |
| Stock Price API | [yfinance](https://github.com/ranaroussi/yfinance) — free, no key |
| Scheduled Jobs | GitHub Actions (free tier) |
| Check Frequency | Every 10 minutes |
| Daily Report Time | 09:00 Taiwan time (UTC+8) |
| Alert Cooldown | 60 minutes per index/rate |
| Bot Server | Render free tier (Flask + Gunicorn) |
| Notifications | Telegram Bot API |

---

## Notes

- GitHub Actions free tier: 2,000 min/month. Running every 10 minutes uses ~1,500 min/month
- Render free tier sleeps after 15 minutes of inactivity; bot wakes automatically on command (first response may take a few seconds)
- Exchange rates update once per day; stock prices from yfinance reflect the latest market session
- Market data is for reference only; actual rates and prices may vary by platform

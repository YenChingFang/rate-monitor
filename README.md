# 📊 Market Monitor Bot

A Telegram bot that monitors exchange rates and global market indices, sends a daily morning report, and alerts you instantly when markets make significant moves.

---

## Features

- **Daily Report** — Every morning at 09:00 (Taiwan time): US stocks, Taiwan stocks, USD/TWD, CNY/TWD with 7-day and 30-day stats
- **Market Index Alerts** — Notifies you when S&P 500, NASDAQ, or TAIEX drops significantly within an hour
- **Individual Stock Alerts** — Notifies you when TSMC, 0050, VTI, VT, or TQQQ drops beyond its threshold within an hour
- **Smart Scheduling** — GitHub Actions only run during Taiwan or US market hours, minimizing unnecessary usage
- **Interactive Bot** — Query any stock price or currency pair on demand via Telegram commands
- **Anti-spam** — Per-ticker 60-minute cooldown; daily report sent only once per day
- **Completely Free** — GitHub Actions free tier + Render free tier + no-key APIs

---

## Notification Examples

**Daily Report**
```
📊 每日市場日報 2026/05/07

🇺🇸 美股大盤
  S&P 500                5,102.45  -2.07% 📉
  NASDAQ Composite      16,234.10  -1.52% 📉

🇺🇸 美股
  VT    $152.12  +0.81% 🟢
  VTI   $356.99  -0.83% 📉
  TQQQ  $67.39   -4.19% 📉

🇹🇼 台股大盤
  加權指數（TAIEX）  19,234.56  +0.52% 🟢

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

**Individual Stock Alert**
```
📉 🇹🇼 個股下跌警報 2026/05/07 11:20

台積電（2330.TW）
現值：910.00
1小時前：960.00
近1小時跌幅：-5.21%（閾值 -5%）

⚠️ 注意持倉，留意進場時機
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
GitHub Actions（台股盤中 UTC 01-05 / 美股盤中 UTC 13-21）
  ├── stock_agent.py    → 大盤 & 個股 1-hour drop alerts
  └── daily_report.py   → Morning report at 09:05 TWD（UTC 01:05, 獨立 cron）

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

| Monitor | Ticker | Condition | Cooldown |
|---|---|---|---|
| S&P 500 | ^GSPC | 1-hour drop ≥ 2% | 60 min |
| NASDAQ | ^IXIC | 1-hour drop ≥ 2.5% | 60 min |
| TAIEX | ^TWII | 1-hour drop ≥ 2% | 60 min |
| 台積電 | 2330.TW | 1-hour drop ≥ 5% | 60 min |
| 元大台灣50 | 0050.TW | 1-hour drop ≥ 5% | 60 min |
| VTI | VTI | 1-hour drop ≥ 3% | 60 min |
| VT | VT | 1-hour drop ≥ 3% | 60 min |
| TQQQ | TQQQ | 1-hour drop ≥ 10% | 60 min |

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

**Actions → 每日市場日報 → Run workflow**

| Option | Description |
|---|---|
| Force daily report | Send the daily report immediately, ignoring the already-sent check |

**Actions → 市場監控 → Run workflow**

| Option | Description |
|---|---|
| Test notification | Send a Telegram ping to confirm the system works |
| Test alerts | Send sample market drop alerts with real current prices |

---

## Tech Stack

| Item | Detail |
|---|---|
| Exchange Rate API | [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api) — free, no key |
| Stock Price API | [yfinance](https://github.com/ranaroussi/yfinance) — free, no key |
| Scheduled Jobs | GitHub Actions (free tier) |
| Check Frequency | 台股盤中每10分鐘（UTC 01–05）；美股盤中每10分鐘（UTC 13–21） |
| Daily Report Time | 09:05 Taiwan time (UTC+8) |
| Alert Cooldown | 60 minutes per ticker |
| Bot Server | Render free tier (Flask + Gunicorn) |
| Notifications | Telegram Bot API |

---

## Notes

- GitHub Actions free tier: 2,000 min/month. Market-hours-only schedule uses ~650 min/month
- Render free tier sleeps after 15 minutes of inactivity; bot wakes automatically on command (first response may take a few seconds)
- Exchange rates update once per day; stock prices from yfinance reflect the latest market session
- Market data is for reference only; actual rates and prices may vary by platform

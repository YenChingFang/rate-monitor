# 💱 人民幣匯率監控 Bot

自動監控人民幣對台幣匯率，7天內創低點時立即發 Telegram 通知，每天早上也會發送日報。

---

## 功能

- **即時警報**：每5分鐘檢查一次，匯率低於7天最低價時立即通知
- **每日日報**：每天早上 09:00 發送包含7天與30天統計的匯率摘要
- **防洗版機制**：警報發出後冷卻60分鐘，不會重複轟炸
- **完全免費**：GitHub Actions 免費方案 + 免費匯率 API，無需任何付費服務

---

## 通知範例

**即時警報**
```
🚨 人民幣匯率警報 2026/03/31 14:35

現在匯率：1 CNY = 4.5800 TWD
7天最低：4.5950 TWD
比近7天最低還低 0.015 TWD！

💰 現在換人民幣最划算，
趕快去淘寶下單吧 🛒
```

**每日日報**
```
💱 人民幣匯率日報 2026/03/31

今日匯率：1 CNY = 4.6361 TWD 📈
便宜程度(7天)：🟩🟩⬜⬜⬜（38% 划算）

📊 近7天統計
  最低：4.5800 TWD ← 最划算
  最高：4.6800 TWD
  平均：4.6300 TWD

📊 近30天統計
  最低：4.5500 TWD
  最高：4.7100 TWD
  平均：4.6200 TWD
```

---

## 設定步驟

### 1. 建立 Telegram Bot

1. 在 Telegram 搜尋 `@BotFather`，發送 `/newbot`
2. 照指示建立 bot，取得 **Bot Token**
3. 對 bot 發任意訊息後，開啟以下網址取得 **Chat ID**：
   ```
   https://api.telegram.org/bot你的TOKEN/getUpdates
   ```
   找到 `"chat":{"id": 數字}` 的數字即為 Chat ID

### 2. 設定 GitHub Secrets

到 repo 的 **Settings → Secrets and variables → Actions**，新增兩個 secret：

| 名稱 | 說明 |
|---|---|
| `TELEGRAM_TOKEN` | BotFather 提供的 Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Telegram Chat ID |

### 3. 檔案結構

```
your-repo/
├── README.md
├── rate_agent.py
└── .github/
    └── workflows/
        └── rate_monitor.yml
```

### 4. 測試

到 **Actions → 人民幣匯率監控 → Run workflow** 手動觸發，確認 Telegram 收到訊息。

---

## 技術說明

| 項目 | 說明 |
|---|---|
| 匯率來源 | [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api)（免費、無需 key） |
| 執行環境 | GitHub Actions（免費方案每月 2000 分鐘） |
| 檢查頻率 | 每5分鐘（cron: `*/5 * * * *`） |
| 日報時間 | 每天台灣時間 09:00 |
| 警報冷卻 | 60 分鐘內不重複發送 |
| 通知方式 | Telegram Bot |

---

## 注意事項

- GitHub Actions 免費方案每月有 2000 分鐘上限，每5分鐘跑一次每月約用 1500 分鐘，在免費額度內
- 匯率資料為參考用，實際購匯匯率以各銀行或平台為準
- `fawazahmed0/exchange-api` 匯率每天更新一次，每5分鐘抓到的數值在同一天內不會有變化；若需真正即時匯率需改用付費 API

# 🔍 網站變動監控機器人

每天自動偵測指定網站是否有內容變化，並透過 Telegram 機器人通知你。
使用 **GitHub Actions**（免費）+ **Telegram Bot** 實現，無需伺服器。

---

## 📁 專案結構

```
website-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml      ← GitHub Actions 排程設定
├── data/
│   └── snapshots.json       ← 自動產生，儲存快照（勿手動編輯）
├── monitor.py               ← 主程式
└── README.md
```

---

## 🚀 設定步驟

### 第一步：建立 Telegram Bot

1. 在 Telegram 搜尋 **@BotFather**，傳送 `/newbot`
2. 依指示輸入 Bot 名稱，取得 **Bot Token**（格式：`123456:ABC-DEF...`）
3. 開啟你的 Bot 對話，傳送任意訊息
4. 瀏覽器開啟以下網址取得你的 **Chat ID**：
   ```
   https://api.telegram.org/bot<你的Token>/getUpdates
   ```
   在回傳的 JSON 中找 `"chat": {"id": 這個數字就是 Chat ID}`

---

### 第二步：建立 GitHub Repository

1. 前往 [github.com](https://github.com) 建立新的 **public 或 private** repository
2. 將本專案所有檔案上傳到 repository（或用 `git push`）

---

### 第三步：設定 GitHub Secrets

在 GitHub repository 頁面：
**Settings → Secrets and variables → Actions → New repository secret**

新增以下兩個 Secrets：

| Secret 名稱 | 值 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | 你的 Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Chat ID |

---

### 第四步：設定監控網站

編輯 `monitor.py` 頂部的 `SITES` 清單：

```python
SITES = [
    {"name": "我的網站A", "url": "https://example.com"},
    {"name": "新聞頁面",  "url": "https://news.example.com/latest"},
]
```

---

### 第五步：設定執行時間

編輯 `.github/workflows/monitor.yml` 中的 cron 時間（UTC 時區）：

```yaml
- cron: "0 1 * * *"   # 每天 UTC 01:00 = 台灣時間 09:00
```

常用時間對照（台灣時間 = UTC + 8）：

| 台灣時間 | cron 設定 |
|---|---|
| 每天 08:00 | `0 0 * * *` |
| 每天 09:00 | `0 1 * * *` |
| 每天 12:00 | `0 4 * * *` |
| 每天 18:00 | `0 10 * * *` |
| 每天 22:00 | `0 14 * * *` |

---

## ▶️ 手動測試

在 GitHub repository 頁面：
**Actions → 網站變動監控 → Run workflow**

首次執行會發送「首次快照完成」通知，之後每次執行若偵測到變動就會通知你。

---

## 📬 通知格式範例

**偵測到變動時：**
```
🚨 網站內容有變動！
網站：我的網站A
網址：https://example.com
時間：2025-03-20 09:00

➕ 新增詞彙：公告 最新 更新 活動...
➖ 移除詞彙：舊文字 過期 ...
```

**無變動時：** 靜默，不發送通知。

---

## ⚠️ 注意事項

- GitHub Actions 免費方案每月提供 **2,000 分鐘**，每天執行一次約用 1 分鐘，一個月約 30 分鐘，遠低於上限
- 部分網站有反爬蟲機制，可能無法抓取（會發送錯誤通知）
- 快照內容透過 GitHub Actions Cache 保存，cache 預設保留 7 天；若超過 7 天未執行會重新建立快照

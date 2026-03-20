import os
import json
import hashlib
import requests
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# ── 設定區 ──────────────────────────────────────────────
SITES = [
    {"name": "聯贏",  "url": "https://www.ly77m.com/"},
    {"name": "双贏2", "url": "https://www.sy05a.com/"},
    {"name": "汇富",  "url": "https://www.hf98w.com/"},
    # 新增更多網站：
    # {"name": "網站名稱", "url": "https://網址"},
]

SNAPSHOT_FILE = "data/snapshots.json"
WAIT_SECONDS = 8  # 等待頁面 JavaScript 載入的秒數
# ────────────────────────────────────────────────────────


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    return driver


def get_text(driver, url: str) -> tuple:
    driver.get(url)
    WebDriverWait(driver, WAIT_SECONDS).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(WAIT_SECONDS)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    full_text = " ".join(soup.get_text(separator=" ").split())
    categories = extract_categories(full_text)

    return full_text, categories


def extract_categories(full_text: str) -> dict:
    keywords = {
        "彩種/玩法": [
            "彩票", "彩種", "六合彩", "時時彩", "快三", "11選5",
            "快樂彩", "雙色球", "大樂透", "體彩", "福彩",
            "真人", "棋牌", "電子", "捕魚", "體育", "電競",
            "百家樂", "龍虎", "輪盤", "老虎機", "沙巴"
        ],
        "充值方式": [
            "充值", "存款", "入金", "銀行卡", "支付寶", "微信",
            "USDT", "加密貨幣", "虛擬幣", "快捷支付",
            "網銀", "轉帳", "掃碼"
        ],
        "活動/優惠": [
            "活動", "優惠", "紅包", "彩金", "返水", "回饋",
            "首存", "首充", "獎勵", "禮金", "贈送",
            "VIP", "代理", "推薦", "佣金", "福利"
        ],
    }

    found = {}
    for category, words in keywords.items():
        hits = [w for w in words if w in full_text]
        found[category] = hits

    return found


def format_categories(categories: dict) -> str:
    lines = []
    for cat, items in categories.items():
        if items:
            lines.append(f"• {cat}：{', '.join(items[:10])}")
        else:
            lines.append(f"• {cat}：（未偵測到）")
    return "\n".join(lines)


def diff_categories(old_cats: dict, new_cats: dict) -> str:
    lines = []
    for cat in new_cats:
        old_set = set(old_cats.get(cat, []))
        new_set = set(new_cats.get(cat, []))
        added = new_set - old_set
        removed = old_set - new_set
        if added:
            lines.append(f"➕ {cat} 新增：{', '.join(added)}")
        if removed:
            lines.append(f"➖ {cat} 移除：{', '.join(removed)}")
    return "\n".join(lines) if lines else "（內容有變動，但關鍵詞分類無明顯差異）"


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_snapshots() -> dict:
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_snapshots(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def send_telegram(token: str, chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    snapshots = load_snapshots()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    changed_count = 0

    driver = get_driver()

    try:
        for site in SITES:
            name = site["name"]
            url = site["url"]
            print(f"🔍 檢查：{name} ({url})")

            try:
                text, categories = get_text(driver, url)
                current_hash = hash_text(text)
                old = snapshots.get(url, {})

                if not old:
                    snapshots[url] = {
                        "hash": current_hash,
                        "text": text[:3000],
                        "categories": categories,
                        "updated": now,
                    }
                    cat_summary = format_categories(categories)
                    preview = text[:300] + ("…" if len(text) > 300 else "")
                    msg = (
                        f"📌 <b>首次快照完成</b>\n"
                        f"網站：<b>{name}</b>\n"
                        f"網址：{url}\n"
                        f"時間：{now}\n\n"
                        f"📊 <b>偵測到的內容分類：</b>\n{cat_summary}\n\n"
                        f"📄 <b>頁面預覽：</b>\n{preview}"
                    )
                    send_telegram(token, chat_id, msg)
                    print(f"  ✅ 首次快照已儲存")

                elif old["hash"] != current_hash:
                    changed_count += 1
                    old_cats = old.get("categories", {})
                    diff = diff_categories(old_cats, categories)
                    cat_summary = format_categories(categories)

                    snapshots[url] = {
                        "hash": current_hash,
                        "text": text[:3000],
                        "categories": categories,
                        "updated": now,
                    }
                    msg = (
                        f"🚨 <b>網站內容有變動！</b>\n"
                        f"網站：<b>{name}</b>\n"
                        f"網址：{url}\n"
                        f"時間：{now}\n\n"
                        f"🔄 <b>變動摘要：</b>\n{diff}\n\n"
                        f"📊 <b>目前內容分類：</b>\n{cat_summary}"
                    )
                    send_telegram(token, chat_id, msg)
                    print(f"  🔔 偵測到變動，已發送通知")

                else:
                    print(f"  ✓ 無變動")

            except Exception as e:
                error_msg = (
                    f"⚠️ <b>監控錯誤</b>\n"
                    f"網站：<b>{name}</b>\n"
                    f"網址：{url}\n"
                    f"錯誤：{e}\n"
                    f"時間：{now}"
                )
                send_telegram(token, chat_id, error_msg)
                print(f"  ❌ 錯誤：{e}")

    finally:
        driver.quit()

    save_snapshots(snapshots)

    if changed_count == 0:
        print(f"\n✅ 所有網站檢查完畢，無異動。")
    else:
        print(f"\n🔔 共 {changed_count} 個網站有變動。")


if __name__ == "__main__":
    main()

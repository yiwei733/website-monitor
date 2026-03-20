import os
import json
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# ── 設定區 ──────────────────────────────────────────────
SITES = [
    {
        "name": "範例網站",
        "url": "https://example.com",
    },
    # 新增更多網站：
    # {"name": "我的網站", "url": "https://mysite.com"},
]

SNAPSHOT_FILE = "data/snapshots.json"
# ────────────────────────────────────────────────────────


def get_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SiteMonitor/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())
    return text


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
        "disable_web_page_preview": False,
    }
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()


def diff_summary(old_text: str, new_text: str) -> str:
    old_words = set(old_text.split())
    new_words = set(new_text.split())
    added = [w for w in new_text.split() if w not in old_words][:15]
    removed = [w for w in old_text.split() if w not in new_words][:15]
    lines = []
    if added:
        lines.append(f"➕ 新增詞彙：{' '.join(added)}")
    if removed:
        lines.append(f"➖ 移除詞彙：{' '.join(removed)}")
    return "\n".join(lines) if lines else "（內容結構有變，但詞彙差異不明顯）"


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    snapshots = load_snapshots()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    changed_count = 0

    for site in SITES:
        name = site["name"]
        url = site["url"]
        print(f"🔍 檢查：{name} ({url})")

        try:
            text = get_text(url)
            current_hash = hash_text(text)
            old = snapshots.get(url, {})

            if not old:
                snapshots[url] = {"hash": current_hash, "text": text[:3000], "updated": now}
                msg = (
                    f"📌 <b>首次快照完成</b>\n"
                    f"網站：<b>{name}</b>\n"
                    f"網址：{url}\n"
                    f"時間：{now}\n\n"
                    f"已記錄初始內容，之後若有變動會通知你。"
                )
                send_telegram(token, chat_id, msg)
                print(f"  ✅ 首次快照已儲存")

            elif old["hash"] != current_hash:
                changed_count += 1
                summary = diff_summary(old.get("text", ""), text)
                snapshots[url] = {"hash": current_hash, "text": text[:3000], "updated": now}
                msg = (
                    f"🚨 <b>網站內容有變動！</b>\n"
                    f"網站：<b>{name}</b>\n"
                    f"網址：{url}\n"
                    f"時間：{now}\n\n"
                    f"{summary}"
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

    save_snapshots(snapshots)

    if changed_count == 0:
        print(f"\n✅ 所有網站檢查完畢，無異動。")
    else:
        print(f"\n🔔 共 {changed_count} 個網站有變動。")


if __name__ == "__main__":
    main()

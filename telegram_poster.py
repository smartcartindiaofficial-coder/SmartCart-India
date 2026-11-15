"""
telegram_poster.py - posts the video/photo/text to your Telegram channel (free Bot API).

Changes vs the old version
  * No more crash at import when the token is missing (it only fails when you post).
  * Plain `requests` only (no pyTelegramBotAPI needed). The old "Retry" adapter never
    retried POST requests; this has a real retry loop for connect errors / 429 / 5xx.
  * A read-timeout is NOT retried, so you don't get duplicate posts when Telegram
    actually received the video but the reply was slow.
  * Product name and link are HTML-escaped (a '&' or '<' used to break the post).
  * Affiliate disclosure added to the caption; stray debug print removed.
  * Videos over the Bot API's 50 MB limit fall back to a text post with the link.
"""
import os
import html
import time
import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "Config.env"))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
API = "https://api.telegram.org/bot{token}/{method}"

MAX_VIDEO_BYTES = 50 * 1024 * 1024  # Bot API upload limit
CONNECT_TIMEOUT = 60
READ_TIMEOUT = 600
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."


def _build_caption(product_name, product_link, youtube_url, price):
    caption = f"📦 <b>{html.escape(product_name)}</b>\n\n"
    if youtube_url:
        caption += f"🎬 <b>Watch on YouTube Shorts:</b>\n{html.escape(youtube_url)}\n\n"
    if price:
        caption += f"💰 <b>Price:</b> {html.escape(str(price))}\n"
    caption += (
        f"🔗 <a href=\"{html.escape(product_link, quote=True)}\">Click here to buy on Amazon</a>\n\n"
        f"<i>{DISCLOSURE}</i>\n\n"
        "#AmazonFinds #SmartCartIndia #Deals"
    )
    return caption[:1024]  # Telegram caption limit for media


def _send(method, data, file_field=None, file_path=None, retries=3):
    """POST to the Bot API. Returns True on success."""
    url = API.format(token=BOT_TOKEN, method=method)
    for attempt in range(1, retries + 1):
        try:
            if file_path:
                with open(file_path, "rb") as fh:
                    resp = requests.post(
                        url, data=data,
                        files={file_field: (os.path.basename(file_path), fh)},
                        timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                    )
            else:
                resp = requests.post(url, data=data, timeout=(CONNECT_TIMEOUT, 60))

            if resp.status_code == 200:
                return True
            if resp.status_code == 429:
                wait = int(resp.json().get("parameters", {}).get("retry_after", 5))
                print(f"⏳ Telegram rate limit; waiting {wait}s...")
                time.sleep(wait + 1)
                continue
            if resp.status_code >= 500:
                print(f"⚠️ Telegram server error {resp.status_code} (attempt {attempt}/{retries}).")
                time.sleep(3 * attempt)
                continue
            print(f"❌ Telegram rejected the request ({resp.status_code}): {resp.text[:300]}")
            return False  # 4xx: retrying won't help
        except requests.exceptions.ReadTimeout:
            print("⚠️ Telegram read-timeout: the post MAY have been delivered. Not retrying (avoids duplicates).")
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout) as e:
            print(f"⚠️ Telegram connection problem (attempt {attempt}/{retries}): {e}")
            time.sleep(3 * attempt)
    return False


def post_to_telegram(product_name, product_link, media_path, youtube_url=None, price=None):
    """Send video / photo / text. Returns True on success, False on failure."""
    if not BOT_TOKEN or not CHANNEL_ID:
        print("❌ TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID missing in Config.env.")
        return False

    caption = _build_caption(product_name, product_link, youtube_url, price)
    base = {"chat_id": CHANNEL_ID, "parse_mode": "HTML"}
    media_ok = bool(media_path) and os.path.exists(media_path)
    ext = os.path.splitext(media_path or "")[1].lower()

    if media_ok and ext in (".mp4", ".mov"):
        if os.path.getsize(media_path) <= MAX_VIDEO_BYTES:
            print(f"📤 Telegram: uploading video {os.path.basename(media_path)}...")
            if _send("sendVideo", {**base, "caption": caption, "supports_streaming": "true"}, "video", media_path):
                print(f"🚀 Telegram video posted: {product_name[:30]}")
                return True
            return False
        print("⚠️ Video is over Telegram's 50 MB limit - posting text with the link instead.")
    elif media_ok and ext in (".jpg", ".jpeg", ".png"):
        if _send("sendPhoto", {**base, "caption": caption}, "photo", media_path):
            print(f"🚀 Telegram photo posted: {product_name[:30]}")
            return True
        return False

    # text-only fallback (no media, or media too large)
    if _send("sendMessage", {**base, "text": caption, "disable_web_page_preview": "false"}):
        print(f"🚀 Telegram text post sent: {product_name[:30]}")
        return True
    return False
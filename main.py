"""
main.py - SmartCart India orchestrator (optimized).

What changed vs the old version
  * ONE shared publish_product() for both the daily run and manual URLs
    (the two ~100-line copies are gone).
  * Amazon Creators API first (amazon_api.py); Selenium scraper only as a
    fallback, and Chrome is started lazily, only when the fallback is needed.
  * A product is recorded in history ONLY if at least one platform succeeded.
  * Each platform is isolated: one crash/failure cannot stop the others.
  * Retry loop is bounded (no infinite loop), and the run exits with code 1
    when nothing was published, so GitHub Actions shows a red X.
  * Hashtags now actually reach the caption; the category flows through.
  * History / category files are committed too, so duplicate protection
    survives on GitHub Actions.
  * Affiliate disclosure near the top of every caption.
  * pandas, google-genai, webdriver_manager and the dead Pinterest/WhatsApp
    imports are gone (faster installs, fewer crashes).

Usage
  python main.py                 # manual_urls.txt first, else daily routine
  python main.py --url <amazon>  # post one specific product
  python main.py --dry-run       # build the video, but do not post/record

Product dict contract (amazon_api.py and scout.py both return this shape):
  asin, name, link, price, specs ("a | b | c"), images [paths],
  offer_percentage (int), category (str)
"""
import os
import re
import sys
import csv
import gc
import html
import glob
import time
import shutil
import argparse
import traceback
import subprocess
from datetime import datetime

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "Config.env"))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import amazon_api       # noqa: E402  (Creators API client)
import editor           # noqa: E402
import thumbnail_engine  # noqa: E402

# ----------------------------------------------------------------------------
# SETTINGS
# ----------------------------------------------------------------------------
HISTORY_ENV = os.getenv("HISTORY_FILE")
HISTORY_FILE = os.path.join(BASE_DIR, HISTORY_ENV) if HISTORY_ENV else os.path.join(BASE_DIR, "upload_history.csv")
BASE_EXPORT_FOLDER = os.path.join(BASE_DIR, "Exports")
SITE_URL = "https://smartcartindiaofficial-coder.github.io/SmartCart-India/"
DISCLOSURE = "#ad As an Amazon Associate I earn from qualifying purchases."

ENABLED_PLATFORMS = {p.strip().lower() for p in os.getenv("ENABLED_PLATFORMS", "youtube,instagram,telegram").split(",") if p.strip()}
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
IN_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

# 5 premium niche tags per category (names match amazon_api.CATEGORIES / scout.py)
CATEGORY_HASHTAGS = {
    "Baby Products": ["#BabyProducts", "#ParentingHacks", "#BabyMustHaves", "#BabyRegistry", "#SmartCartIndia"],
    "Computers & Accessories": ["#TechFinds", "#DeskSetup", "#TechGadgets", "#PCGaming", "#SmartCartIndia"],
    "Electronics": ["#TechDeals", "#GadgetsIndia", "#Electronics", "#TechReview", "#SmartCartIndia"],
    "Home & Kitchen": ["#KitchenGadgets", "#HomeKitchen", "#KitchenHacks", "#SmartHomeTech", "#SmartCartIndia"],
    "Home Improvement": ["#HomeImprovement", "#DIYProjects", "#SmartHome", "#HardwareTools", "#SmartCartIndia"],
    "Car & Motorbike": ["#CarAccessories", "#CarGadgets", "#MotorbikeLife", "#AutomotiveFinds", "#SmartCartIndia"],
    "Clothing & Accessories": ["#FashionFinds", "#OOTDIndia", "#AmazonFashion", "#StyleInspiration", "#SmartCartIndia"],
    "Jewellery": ["#JewelleryDesign", "#FashionJewellery", "#AccessoriesLovers", "#JewelleryDeals", "#SmartCartIndia"],
    "Default": ["#AmazonFinds", "#TrendingGadgets", "#SmartCartIndia", "#ViralProducts", "#DailyDeals", "#Amazon", "#Trending", "#Viral", "#Deals"],
}

FALLBACK_HOOK = "Check out this amazing find on Amazon right now!"
FALLBACK_BODY = "Tap the link below to see today's price and specs."


# ----------------------------------------------------------------------------
# CONFIG CHECK
# ----------------------------------------------------------------------------
def check_config():
    """Fail fast on the one thing that silently costs money; warn on the rest."""
    if not os.getenv("Affiliate_Code"):
        print("❌ Affiliate_Code is missing in Config.env - links would earn nothing. Aborting.")
        sys.exit(2)

    needed = {
        "groq": ["GROQ_API_KEY"],
        "instagram": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID", "SUPABASE_URL"],
        "telegram": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHANNEL_ID"],
    }
    for group, keys in needed.items():
        if group != "groq" and group not in ENABLED_PLATFORMS:
            continue
        for key in keys:
            if not os.getenv(key):
                print(f"⚠️ {key} missing in Config.env ({group} will fail or use fallbacks).")
    if "instagram" in ENABLED_PLATFORMS and not (os.getenv("Superbase_Secret_Key") or os.getenv("SUPABASE_SECRET_KEY")):
        print("⚠️ Supabase secret key missing (Superbase_Secret_Key) - Instagram uploads will fail.")


# ----------------------------------------------------------------------------
# COPYWRITING (Groq, free tier)
# ----------------------------------------------------------------------------
def get_crisp_catchy_title(raw_name):
    """Offline fallback: shorten a bloated Amazon title to ~5 clean words."""
    clean = re.sub(r"\([^)]*\)", "", raw_name)
    clean = re.sub(r"\[[^\]]*\]", "", clean)
    clean = re.sub(r"\b\d+\s*(gb|mb|tb|mah|w|v|cm|mm|inch|ltr|liters|pc|pcs|pack|pk)\b.*", "", clean, flags=re.I)
    clean = re.sub(r"\b(with|for|compatible\s+with)\b.*", "", clean, flags=re.I)
    clean = re.sub(r"[|,\-_:+•]", " ", clean)
    return " ".join(clean.split()[:5]).title().strip()


def _clean_line(text):
    text = re.sub(r"^\s*line\s*\d+\s*[:\-.)]\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*\d+\s*[.)]\s*", "", text)
    text = text.replace("*", "").replace("#", "").replace("<", "").replace(">", "")
    return text.strip().strip("\"'“”‘’").strip()


def _limit_words(text, n):
    words = text.split()
    return " ".join(words[:n]) if len(words) > n else text


def generate_copy(raw_name, raw_specs, offer):
    """Returns (viral_title, voiceover_body, short_product_name). Never raises."""
    crisp = get_crisp_catchy_title(raw_name) or raw_name[:45]
    fallback = (crisp, f"{FALLBACK_HOOK} {FALLBACK_BODY}", _limit_words(crisp, 4))

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ GROQ_API_KEY missing - using offline title/script.")
        return fallback

    discount = f"{offer}% off" if offer else "no discount information (do not mention a discount)"
    prompt = f"""You are an expert viral marketer for YouTube Shorts and Instagram Reels (Indian audience).
Turn the product details below into high-retention content.

PRODUCT NAME: {raw_name}
SPECIFICATIONS: {raw_specs}
DISCOUNT: {discount}

Return EXACTLY 4 lines. No introduction, no markdown, no numbering, no labels.
Line 1: Punchy viral title (max 5 words, no model numbers).
Line 2: Hook for seconds 0-5 about an everyday problem or curiosity (max 10 words).
Line 3: Script body for seconds 6-20 naturally covering 2 lifestyle benefits and the discount (15-20 words).
Line 4: Brand and product type only (max 4 words, no specs, colours or fluff)."""

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Groq unavailable ({e}) - using offline title/script.")
        return fallback

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-20b",
                temperature=0.7,
                max_tokens=1000,  # room for reasoning + the 4 lines
            )
            raw = (resp.choices[0].message.content or "").strip()
            lines = [_clean_line(l) for l in raw.split("\n") if l.strip()]
            lines = [l for l in lines if l]
            if len(lines) >= 4:
                title = _limit_words(lines[0], 5)
                hook = _limit_words(lines[1], 10)
                body = _limit_words(lines[2], 24)
                product_name = _limit_words(lines[3], 4)
                # NOTE: the YouTube API cannot pin comments, so we don't claim "pinned".
                return title, f"{hook} {body} Direct buy link is in the comments below!", product_name
            print(f"⚠️ Groq returned {len(lines)} usable lines (attempt {attempt}).")
        except Exception as e:
            print(f"❌ Groq failure (attempt {attempt}): {e}")
    return fallback


# ----------------------------------------------------------------------------
# FILES / HISTORY
# ----------------------------------------------------------------------------
def get_save_path(asin, prefix="Product"):
    now = datetime.now()
    path = os.path.join(BASE_EXPORT_FOLDER, now.strftime("%Y"), now.strftime("%B"), now.strftime("%d"), f"{prefix}_{asin}")
    os.makedirs(path, exist_ok=True)
    return path


def get_uploaded_asins():
    if not os.path.exists(HISTORY_FILE):
        return set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8", newline="") as f:
            return {(row.get("asin") or "").strip() for row in csv.DictReader(f) if row.get("asin")}
    except Exception as e:
        print(f"⚠️ Could not read history: {e}")
        return set()


def record_upload(asin, name):
    exists = os.path.isfile(HISTORY_FILE)
    with open(HISTORY_FILE, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        if not exists:
            writer.writerow(["asin", "name", "date"])
        writer.writerow([asin, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    print(f"📝 Recorded {asin} to history.")


def cleanup_temp_files():
    """Remove leftover temp images (case-insensitive, so it also works on Linux)."""
    try:
        import cv2
        cv2.destroyAllWindows()
    except Exception:
        pass
    gc.collect()

    for folder in {os.getcwd(), BASE_DIR}:
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        for name in names:
            low = name.lower()
            if low.endswith(".jpg") and low.startswith(("temp_", "manual_temp_", "tn_")):
                path = os.path.join(folder, name)
                for attempt in (1, 2):
                    try:
                        os.remove(path)
                        print(f"🗑️ Removed leftover asset: {name}")
                        break
                    except PermissionError:
                        time.sleep(1)  # Windows may still hold the file for a moment
                    except OSError as e:
                        print(f"⚠️ Could not delete {name}: {e}")
                        break


def archive_images(image_paths, folder):
    """Move scraped/downloaded images into the product folder; drop corrupt ones."""
    archived = []
    for idx, img in enumerate(image_paths or []):
        if not os.path.exists(img):
            continue
        if os.path.getsize(img) < 2048:
            print(f"⚠️ {os.path.basename(img)} is empty or corrupted - skipping.")
            continue
        dest = os.path.join(folder, f"img_{idx}.jpg")
        try:
            shutil.move(img, dest)
            archived.append(dest)
        except Exception as e:
            print(f"⚠️ Could not move image: {e}")
    return archived


# ----------------------------------------------------------------------------
# LANDING PAGE + GIT
# ----------------------------------------------------------------------------
def compile_landing_page(asin, name, product_url, local_image_path, output_dir=None):
    """Adds one product card to index.html (GitHub Pages storefront)."""
    output_dir = output_dir or BASE_DIR
    html_path = os.path.join(output_dir, "index.html")
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    image_ref = f"assets/{asin}.jpg"
    if local_image_path and os.path.exists(local_image_path):
        try:
            shutil.copy2(local_image_path, os.path.join(assets_dir, f"{asin}.jpg"))
        except Exception as e:
            print(f"⚠️ [Landing Page] Failed to copy image: {e}")
            image_ref = "https://via.placeholder.com/150"
    else:
        image_ref = "https://via.placeholder.com/150"

    clean_name = name.replace('"', "'")
    title = clean_name[:50] + ("..." if len(clean_name) > 50 else "")
    card = f"""
        <div class="deal-card" id="card-{html.escape(asin)}">
            <img class="deal-thumb" src="{html.escape(image_ref, quote=True)}" alt="{html.escape(title, quote=True)}" loading="lazy">
            <div class="deal-details">
                <h3 class="deal-title">{html.escape(title)}</h3>
                <a class="deal-btn" href="{html.escape(product_url, quote=True)}" target="_blank" rel="noopener sponsored">Buy on Amazon</a>
            </div>
        </div>
    """

    hook = '<div class="deals-container" id="deals-wrapper">'
    if not os.path.exists(html_path):
        scaffold = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Best Daily Deals - SmartCart India 🔥</title>
    <style>
        :root {{ --bg: #0d0d11; --card-bg: #16161f; --text: #f3f4f6; --accent: #ff9900; --border: #262636; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 15px; display: flex; flex-direction: column; align-items: center; }}
        .header-panel {{ text-align: center; margin: 25px 0; max-width: 480px; width: 100%; }}
        .header-panel h1 {{ font-size: 1.6rem; margin-bottom: 5px; }}
        .header-panel p {{ font-size: 0.9rem; color: #8b8ba7; }}
        .disclosure {{ font-size: 0.75rem; color: #8b8ba7; margin-top: 8px; }}
        .deals-container {{ max-width: 480px; width: 100%; display: flex; flex-direction: column; gap: 15px; }}
        .deal-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; display: flex; padding: 12px; gap: 12px; align-items: center; transition: transform 0.2s; }}
        .deal-card:hover {{ transform: scale(1.01); border-color: var(--accent); }}
        .deal-thumb {{ width: 85px; height: 85px; object-fit: contain; background: #fff; border-radius: 8px; padding: 4px; flex-shrink: 0; }}
        .deal-details {{ flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; min-width: 0; }}
        .deal-title {{ font-size: 0.95rem; font-weight: 600; color: #e5e7eb; line-height: 1.3; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        .deal-btn {{ background: var(--accent); color: #000; text-decoration: none; font-size: 0.85rem; font-weight: 700; padding: 8px 14px; border-radius: 6px; text-align: center; }}
        .deal-btn:hover {{ opacity: 0.9; }}
    </style>
</head>
<body>
    <div class="header-panel">
        <h1>🛒 SmartCart India Deals</h1>
        <p>Click any product below to see the live price on Amazon.</p>
        <p class="disclosure">As an Amazon Associate I earn from qualifying purchases.</p>
    </div>
    {hook}
        {card}
    </div>
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(scaffold)
    else:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        if f'id="card-{asin}"' in content:
            print(f"ℹ️ [Landing Page] {asin} already on the page.")
            return True
        if hook not in content:
            print("⚠️ [Landing Page] deals-wrapper marker not found in index.html - not updated.")
            return False
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content.replace(hook, f"{hook}\n{card}", 1))

    print(f"✅ [Landing Page] Updated {html_path}")
    return True


def _git_exe():
    exe = shutil.which("git")
    if exe:
        return exe
    for path in (r"C:\Program Files\Git\cmd\git.exe",
                 r"C:\Program Files (x86)\Git\cmd\git.exe",
                 os.path.expanduser(r"~\AppData\Local\Programs\Git\cmd\git.exe")):
        if os.path.exists(path):
            return path
    return "git"


def _git(*args, check=True):
    return subprocess.run([_git_exe(), *args], cwd=BASE_DIR, capture_output=True, text=True, check=check)


def _git_branch():
    branch = os.getenv("GITHUB_REF_NAME")
    if branch:
        return branch
    try:
        name = _git("rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
        return name if name and name != "HEAD" else "main"
    except Exception:
        return "main"


def pull_latest_changes():
    if not os.path.isdir(os.path.join(BASE_DIR, ".git")):
        return
    print("Local environment detected. Checking for remote updates...")
    try:
        result = _git("pull", "--autostash", "origin", _git_branch(), check=False)
        print(result.stdout.strip() or result.stderr.strip())
    except Exception as e:
        print(f"⚠️ git pull skipped: {e}")


def sync_landing_page_to_github():
    """Commit + push the storefront AND the history files (so Actions runs remember)."""
    if os.getenv("SKIP_GIT_SYNC") == "1":
        return True
    if not os.path.isdir(os.path.join(BASE_DIR, ".git")):
        print("ℹ️ [GitHub] Not a git repository - skipping deployment.")
        return True
    print("🚀 [GitHub] Pushing updated storefront...")
    try:
        if IN_ACTIONS:  # only set identity in CI; never touch your local git config
            _git("config", "user.name", "Automated Deployer")
            _git("config", "user.email", "actions@github.com")

        for path in ("index.html", "assets", "category_history.json", os.path.relpath(HISTORY_FILE, BASE_DIR)):
            if os.path.exists(os.path.join(BASE_DIR, path)):
                _git("add", path, check=False)  # check=False: ignored paths just no-op

        if _git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("ℹ️ [GitHub] Nothing new to deploy.")
            return True

        _git("commit", "-m", f"Auto-update deals: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        branch = _git_branch()
        _git("pull", "--rebase", "--autostash", "origin", branch, check=False)
        _git("push", "origin", f"HEAD:{branch}")
        print("✅ [GitHub] Storefront deployed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ [GitHub] Sync failed.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
        return False


# ----------------------------------------------------------------------------
# PUBLISHERS - one small function per platform. To add Pinterest/WhatsApp later,
# write fn(ctx) -> truthy on success and add it to PUBLISHERS. Nothing else changes.
# ----------------------------------------------------------------------------
def _pub_youtube(ctx):
    import uploader
    return uploader.upload_to_youtube(ctx["video_path"], ctx["title"], ctx["description_yt"], ctx["yt_tags"])


def _pub_instagram(ctx):
    import insta_uploader
    return insta_uploader.upload_to_instagram(ctx["video_path"], ctx["description"], ctx["product_url"])


def _pub_telegram(ctx):
    import telegram_poster
    return telegram_poster.post_to_telegram(
        ctx["title"], ctx["product_url"], ctx["video_path"], youtube_url=ctx["results"].get("youtube")
    )

PUBLISHERS = [("youtube", _pub_youtube), ("instagram", _pub_instagram), ("telegram", _pub_telegram)]
# PUBLISHERS = []

def post_everywhere(ctx):
    ctx["results"] = {}
    for label, fn in PUBLISHERS:
        if label not in ENABLED_PLATFORMS:
            print(f"⏭️ {label}: disabled via ENABLED_PLATFORMS.")
            continue
        try:
            result = fn(ctx)
        except Exception as e:
            print(f"❌ {label} crashed: {e}")
            traceback.print_exc()
            result = None
        ctx["results"][label] = result
        print(f"{'✅' if result else '❌'} {label}: {result if result else 'failed'}")
    return ctx["results"]


def build_description(title, product_url, hashtags):
    return (
        f"📦 {title} - @amazondotin\n\n"
        f"Buy Link: {product_url}\n"
        f"{DISCLOSURE}\n\n"
        f"{' '.join(hashtags)}\n\n"
        f"website: {SITE_URL}\n"
        "Instagram: https://www.instagram.com/smartcartindiaofficial\n"
        "YouTube: https://www.youtube.com/@SmartCartIndiaOfficial\n"
        "Telegram: t.me/smartCartIndiaOfficial"
    )


# ----------------------------------------------------------------------------
# THE ONE PIPELINE
# ----------------------------------------------------------------------------
def publish_product(product, prefix="Product"):
    """
    Returns one of:
      "published"             at least one platform succeeded (recorded in history)
      "dry_run"               video built, nothing posted
      "failed_before_upload"  images/video problem -> safe to try another product
      "upload_failed"         every platform failed -> NOT recorded, don't spam retries
    """
    asin = product["asin"]
    offer = int(product.get("offer_percentage") or 0)
    specs = (product.get("specs") or "").replace(" | ", "\n-")
    folder = get_save_path(asin, prefix)
    video_path = os.path.join(folder, f"Video_{asin}.mp4")

    images = archive_images(product.get("images"), folder)
    if not images:
        print("❌ No valid product images - skipping this product.")
        return "failed_before_upload"

    title, body, product_name = generate_copy(product["name"], specs, offer)
    voice_script = f"{title}. {body}"
    print(f"💬 Script: {voice_script}")

    thumb_path = None
    try:
        print("🎨 Building thumbnail...")
        thumb_path = thumbnail_engine.generate_thumbnail_multi(
            asin=asin, product_name=title, specifications=[], image_paths_list=images, offer_percentage=offer
        )
    except Exception as e:
        print(f"⚠️ Thumbnail failed (continuing without it): {e}")

    render_images = list(images)
    if thumb_path and os.path.exists(thumb_path):
        render_images.insert(0, thumb_path)

    try:
        editor.create_pro_video(render_images, title, video_path, voice_text=voice_script)
    except Exception as e:
        print(f"❌ Video rendering failed: {e}")
        traceback.print_exc()
        return "failed_before_upload"
    if not (os.path.exists(video_path) and os.path.getsize(video_path) > 0):
        print("❌ Video file missing or empty after rendering.")
        return "failed_before_upload"

    if thumb_path and os.path.exists(thumb_path):
        shutil.move(thumb_path, os.path.join(folder, f"tn_{asin}.jpg"))

    # Standard tag link. (Once the API is stable you may switch to product["link"].)
    product_url = f"https://www.amazon.in/dp/{asin}?tag={os.getenv('Affiliate_Code')}"
    hashtags = CATEGORY_HASHTAGS.get(product.get("category") or "Default", CATEGORY_HASHTAGS["Default"])
    description = build_description(title, product_url, hashtags)
    with open(os.path.join(folder, "description.txt"), "w", encoding="utf-8") as f:
        f.write(description)

    if DRY_RUN:
        print(f"🧪 DRY RUN: video ready at {video_path}. Nothing posted or recorded.")
        return "dry_run"

    ctx = {
        "video_path": video_path,
        "title": title.replace("<", "").replace(">", ""),
        "description": description,
        "description_yt": description.replace(" - @amazondotin", ""),
        "yt_tags": ", ".join(t.replace("#", "").lower() for t in hashtags),
        "product_url": product_url,
    }
    results = post_everywhere(ctx)

    if not any(results.values()):
        print("❌ Every platform failed - product NOT recorded, so it can be retried next run.")
        return "upload_failed"

    record_upload(asin, title)
    compile_landing_page(asin, product_name, product_url, images[0])
    sync_landing_page_to_github()
    print(f"✅ Published {asin} to: {', '.join(k for k, v in results.items() if v)}")
    return "published"


# ----------------------------------------------------------------------------
# PRODUCT DISCOVERY (API first, scraper fallback with lazy Chrome)
# ----------------------------------------------------------------------------
def _make_driver():
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if IN_ACTIONS:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=options)


def _scrape_bestsellers(count):
    import scout
    driver = _make_driver()
    try:
        return scout.get_bestsellers(driver, count=count) or []
    finally:
        driver.quit()


def _scrape_single(url):
    import scout
    driver = _make_driver()
    try:
        return scout.scrape_specific_product(driver, url)
    finally:
        driver.quit()


def find_products(count, exclude):
    products = amazon_api.get_deal_products(count=count, exclude_asins=exclude)
    if products is None:
        print("↩️ Creators API unavailable - using the Selenium scraper fallback.")
        products = _scrape_bestsellers(count)
    return products or []


def run_daily():
    pool_size = int(os.getenv("pool_size") or 5)
    max_attempts = int(os.getenv("MAX_PRODUCT_ATTEMPTS") or 3)
    uploaded = get_uploaded_asins()

    for attempt in range(1, max_attempts + 1):
        print(f"🔎 Product search, attempt {attempt}/{max_attempts}")
        try:
            pool = find_products(pool_size, uploaded)
        except Exception as e:
            print(f"❌ Product search crashed: {e}")
            traceback.print_exc()
            pool = []
        fresh = [p for p in pool if p.get("asin") not in uploaded and p.get("images")]

        if not fresh:
            print(f"😴 No new usable products ({len(pool)} found). Waiting before retry...")
            time.sleep(10 * attempt)
            continue

        for product in fresh:
            print(f"✨ Candidate: {product['name'][:60]}")
            status = publish_product(product, prefix="Product")
            if status in ("published", "dry_run"):
                return True
            if status == "upload_failed":
                return False  # platforms are failing; don't render 5 more videos
            # failed_before_upload -> try the next candidate
        cleanup_temp_files()
    return False


def run_manual(url):
    print(f"🚀 Manual URL: {url}")
    product = amazon_api.get_product_by_url(url)
    if product is None:
        print("↩️ Creators API unavailable - using the Selenium scraper fallback.")
        product = _scrape_single(url)
    if not product:
        print("❌ Could not read product details.")
        return False
    if product["asin"] in get_uploaded_asins():
        print(f"🚫 {product['asin']} was already posted before - skipping.")
        return False
    return publish_product(product, prefix="Manual") in ("published", "dry_run")


def process_manual_queue(file_name="manual_urls.txt"):
    """Returns None if there was nothing queued, else True/False for success."""
    path = os.path.join(BASE_DIR, file_name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        print("ℹ️ Manual queue is empty. Proceeding to daily routine.")
        return None

    match = re.search(r"https?://[^\s]+", content)  # handles Android share-sheet text
    if not match:
        print("⚠️ No valid URL in manual_urls.txt - clearing it.")
        open(path, "w", encoding="utf-8").close()
        return None

    success = False
    try:
        success = run_manual(match.group(0))
    except Exception as e:
        print(f"❌ Manual post failed: {e}")
        traceback.print_exc()
    finally:
        open(path, "w", encoding="utf-8").close()  # always clear, so it can't loop forever
        print("🧹 Cleared manual_urls.txt.")
    return success


# ----------------------------------------------------------------------------
def main():
    global DRY_RUN
    parser = argparse.ArgumentParser(description="SmartCart India pipeline")
    parser.add_argument("--url", help="Post one specific Amazon product URL")
    parser.add_argument("--dry-run", action="store_true", help="Build the video but do not post or record")
    args = parser.parse_args()
    DRY_RUN = DRY_RUN or args.dry_run

    # Every module resolves Exports/, logos, music and temp files from the working
    # directory, so pin it to the project folder no matter where you launch from.
    os.chdir(BASE_DIR)

    if IN_ACTIONS:
        print("Running inside GitHub Actions. Skipping git pull.")
    else:
        pull_latest_changes()
    check_config()

    ok = False
    try:
        if args.url:
            ok = run_manual(args.url)
        else:
            manual_result = process_manual_queue("manual_urls.txt")
            # a manual job runs INSTEAD of the daily routine for this run
            ok = manual_result if manual_result is not None else run_daily()
    finally:
        cleanup_temp_files()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
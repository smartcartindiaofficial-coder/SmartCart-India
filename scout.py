"""
scout.py - FALLBACK Amazon product scraper (Selenium).

main.py now uses amazon_api.py (the official Creators API) first and calls this
module only when the API is unavailable (no credentials yet, or the account does
not meet Amazon's sales requirement).

Note: Amazon's terms restrict automated scraping, and datacenter IPs (GitHub
Actions) are often shown captchas. Treat this as a temporary bridge.

Fixes vs the old version
  * A failed/unavailable/no-discount product no longer ends the whole scan:
    links are collected first, then each product page is visited in its own
    try/except (the old code never went "back", so one failure => zero cards).
  * Products WITHOUT a discount are kept (offer_percentage = 0) instead of dropped.
  * CATEGORIES de-duplicated by Amazon node id (the old dict silently overwrote
    duplicate names such as "Accessories"). 94 entries -> 87 unique categories.
  * Cooldown days come from CATEGORY_COOLDOWN_DAYS (default 4; the old comments
    said 7 but the code used 4).
  * `category` is now returned, so the hashtag table in main.py works.
  * The hard-coded affiliate tag is gone: links use Affiliate_Code from Config.env.
  * Fixed sleeps replaced with waits; bare `except:` replaced with logged errors;
    discount_selectors loop actually uses its selectors now.
  * Images downloaded with `requests` (no global urllib opener); temp files are
    temp_<tag>_<n>.jpg so main.py's cleanup works on Linux too.
"""
import os
import re
import json
import time
import random
import datetime

import requests
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "Config.env"))

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
BLACKLIST = ["credit card", "gift card", "subscription", "recharge", "lpg", "amazon pay", "blink plus"]

CATEGORIES = {
    "Electronics": "https://www.amazon.in/gp/bestsellers/electronics/",
    "Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1388867031/",
    "Cameras & Photography": "https://www.amazon.in/gp/bestsellers/electronics/1388977031/",
    "Car & Vehicle Electronics": "https://www.amazon.in/gp/bestsellers/electronics/1389221031/",
    "Computers & Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1458204031/",
    "Headphones": "https://www.amazon.in/gp/bestsellers/electronics/1388921031/",
    "Hi-Fi & Home Audio": "https://www.amazon.in/gp/bestsellers/electronics/1389335031/",
    "Home Theatre, TV & Video": "https://www.amazon.in/gp/bestsellers/electronics/1389375031/",
    "Mobiles & Tablets": "https://www.amazon.in/gp/bestsellers/electronics/92071051031/",
    "Portable Media Players": "https://www.amazon.in/gp/bestsellers/electronics/1389433031/",
    "Telephones & Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1389481031/",
    "Wearable Technology": "https://www.amazon.in/gp/bestsellers/electronics/11599648031/",
    "eBook Readers & Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1389494031/",
    "Accessories (1388978031)": "https://www.amazon.in/gp/bestsellers/electronics/1388978031/",
    "Accessories (1389316031)": "https://www.amazon.in/gp/bestsellers/electronics/1389316031/",
    "Accessories (1389434031)": "https://www.amazon.in/gp/bestsellers/electronics/1389434031/",
    "Accessories (1389463031)": "https://www.amazon.in/gp/bestsellers/electronics/1389463031/",
    "Accessories (1389482031)": "https://www.amazon.in/gp/bestsellers/electronics/1389482031/",
    "Blank Media Cases & Wallets": "https://www.amazon.in/gp/bestsellers/electronics/1375260031/",
    "Car & Vehicle Electronics Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1389226031/",
    "Memory Cards": "https://www.amazon.in/gp/bestsellers/electronics/1388963031/",
    "Mobile Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1389402031/",
    "Tablet Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1375328031/",
    "Action Cameras": "https://www.amazon.in/gp/bestsellers/electronics/3404636031/",
    "Binoculars, Telescopes & Optics": "https://www.amazon.in/gp/bestsellers/electronics/1389159031/",
    "Body Mounted Cameras": "https://www.amazon.in/gp/bestsellers/electronics/51419882031/",
    "Cases & Bags": "https://www.amazon.in/gp/bestsellers/electronics/1389018031/",
    "Digital Cameras": "https://www.amazon.in/gp/bestsellers/electronics/1389175031/",
    "Film Cameras": "https://www.amazon.in/gp/bestsellers/electronics/1389183031/",
    "Flashes": "https://www.amazon.in/gp/bestsellers/electronics/1389193031/",
    "Lenses": "https://www.amazon.in/gp/bestsellers/electronics/1389197031/",
    "Photo Printers": "https://www.amazon.in/gp/bestsellers/electronics/1375450031/",
    "Photo Studio & Lighting": "https://www.amazon.in/gp/bestsellers/electronics/1389103031/",
    "Professional Video Cameras": "https://www.amazon.in/gp/bestsellers/electronics/51419880031/",
    "Projectors": "https://www.amazon.in/gp/bestsellers/electronics/1389388031/",
    "Security Cameras": "https://www.amazon.in/gp/bestsellers/electronics/1389203031/",
    "Simulated Cameras": "https://www.amazon.in/gp/bestsellers/electronics/1389206031/",
    "Underwater Video & Photography": "https://www.amazon.in/gp/bestsellers/electronics/1389214031/",
    "Video Cameras": "https://www.amazon.in/gp/bestsellers/electronics/1389174031/",
    "Car & Vehicle GPS Devices": "https://www.amazon.in/gp/bestsellers/electronics/1389266031/",
    "Car Electronics": "https://www.amazon.in/gp/bestsellers/electronics/1389267031/",
    "Motorcycle Electronics": "https://www.amazon.in/gp/bestsellers/electronics/1389310031/",
    "Accessories (1375248031)": "https://www.amazon.in/gp/bestsellers/electronics/1375248031/",
    "Audio & Video Accessories": "https://www.amazon.in/gp/bestsellers/electronics/1375459031/",
    "External Devices & Data Storage": "https://www.amazon.in/gp/bestsellers/electronics/1375393031/",
    "Keyboards, Mice & Input Devices": "https://www.amazon.in/gp/bestsellers/electronics/1375412031/",
    "Networking Devices": "https://www.amazon.in/gp/bestsellers/electronics/1375427031/",
    "Car GPS": "https://www.amazon.in/gp/bestsellers/electronics/1389328031/",
    "GPS Trackers": "https://www.amazon.in/gp/bestsellers/electronics/1389329031/",
    "GPS Units": "https://www.amazon.in/gp/bestsellers/electronics/3403901031/",
    "Item Finders": "https://www.amazon.in/gp/bestsellers/electronics/21529666031/",
    "Motorcycle GPS": "https://www.amazon.in/gp/bestsellers/electronics/1389331031/",
    "In-Ear": "https://www.amazon.in/gp/bestsellers/electronics/14146389031/",
    "On-Ear": "https://www.amazon.in/gp/bestsellers/electronics/14146391031/",
    "Open-Ear Headphones": "https://www.amazon.in/gp/bestsellers/electronics/76028196031/",
    "Over-Ear": "https://www.amazon.in/gp/bestsellers/electronics/14146390031/",
    "Accessories (1389336031)": "https://www.amazon.in/gp/bestsellers/electronics/1389336031/",
    "Compact Stereos": "https://www.amazon.in/gp/bestsellers/electronics/1389338031/",
    "Media Streaming Devices": "https://www.amazon.in/gp/bestsellers/electronics/1389339031/",
    "Radios & Boomboxes": "https://www.amazon.in/gp/bestsellers/electronics/1389343031/",
    "Receivers & Separates": "https://www.amazon.in/gp/bestsellers/electronics/1389349031/",
    "Speakers": "https://www.amazon.in/gp/bestsellers/electronics/1389365031/",
    "Accessories (1389377031)": "https://www.amazon.in/gp/bestsellers/electronics/1389377031/",
    "Home Theater Systems": "https://www.amazon.in/gp/bestsellers/electronics/1389387031/",
    "TV Receivers": "https://www.amazon.in/gp/bestsellers/electronics/1389392031/",
    "Televisions": "https://www.amazon.in/gp/bestsellers/electronics/1389396031/",
    "Video Glasses": "https://www.amazon.in/gp/bestsellers/electronics/1389397031/",
    "Smartphones & Basic Mobiles": "https://www.amazon.in/gp/bestsellers/electronics/1389432031/",
    "Tablets": "https://www.amazon.in/gp/bestsellers/electronics/1375458031/",
    "Boomboxes": "https://www.amazon.in/gp/bestsellers/electronics/1389454031/",
    "Cassette Players": "https://www.amazon.in/gp/bestsellers/electronics/1389456031/",
    "MP3/MP4 Players": "https://www.amazon.in/gp/bestsellers/electronics/1389458031/",
    "Radios": "https://www.amazon.in/gp/bestsellers/electronics/1389460031/",
    "Shortwave Receivers": "https://www.amazon.in/gp/bestsellers/electronics/1389347031/",
    "Activity Trackers": "https://www.amazon.in/gp/bestsellers/electronics/4730577031/",
    "Arm & Wristband Accessories": "https://www.amazon.in/gp/bestsellers/electronics/11599650031/",
    "Baby Wearables": "https://www.amazon.in/gp/bestsellers/electronics/11599652031/",
    "Glasses": "https://www.amazon.in/gp/bestsellers/electronics/11599657031/",
    "Pendants": "https://www.amazon.in/gp/bestsellers/electronics/11599655031/",
    "Rings": "https://www.amazon.in/gp/bestsellers/electronics/11599656031/",
    "Single Ear Bluetooth Headsets": "https://www.amazon.in/gp/bestsellers/electronics/21529672031/",
    "Smart Clip Accessories": "https://www.amazon.in/gp/bestsellers/electronics/11599651031/",
    "Smart Watches": "https://www.amazon.in/gp/bestsellers/electronics/5605728031/",
    "Smart Watches & Accessories": "https://www.amazon.in/gp/bestsellers/electronics/74711502031/",
    "Temporary Tattoos": "https://www.amazon.in/gp/bestsellers/electronics/11599658031/",
    "VR Mobile Phone Headsets": "https://www.amazon.in/gp/bestsellers/electronics/12467536031/",
    "Wristbands": "https://www.amazon.in/gp/bestsellers/electronics/11599653031/",
}

# Names that exist in main.py's CATEGORY_HASHTAGS keep their own hashtags;
# every other Electronics sub-category uses the "Electronics" tags.
HASHTAG_CATEGORIES = {"Computers & Accessories", "Electronics"}

CAPTCHA_MARKERS = ("validatecaptcha", "robot check", "enter the characters you see below")


def generate_tags(name, specs):
    base_tags = ["AmazonFinds", "CoolGadgets", "AmazonIndia"]
    keywords = [w for w in name.split() if len(w) > 4][:6]
    return ", ".join(sorted(set(base_tags + keywords)))


def _blocked(driver):
    try:
        html = driver.page_source.lower()
    except Exception:
        return False
    return any(marker in html for marker in CAPTCHA_MARKERS)


def _pick_category():
    """Random category that is not on cooldown; records the pick in category_history.json."""
    history_file = os.path.join(SCRIPT_DIR, "category_history.json")
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not read category history: {e}")

    cooldown_days = int(os.getenv("CATEGORY_COOLDOWN_DAYS", "4"))
    now = datetime.datetime.now()
    available = {}
    for name, url in CATEGORIES.items():
        last = history.get(name)
        if last and (now - datetime.datetime.fromisoformat(last)).days < cooldown_days:
            continue
        available[name] = url

    if not available:
        print("🔄 All categories are on cooldown - resetting the cooldown history.")
        available, history = dict(CATEGORIES), {}

    name, url = random.choice(list(available.items()))
    print(f"🎲 Category pick: {name} ({cooldown_days}-day cooldown applied)")
    history[name] = now.isoformat()
    try:
        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        print(f"⚠️ Failed to write category history: {e}")
    return name, url


def _download_images(urls, tag, limit):
    paths = []
    for idx, url in enumerate(urls):
        if len(paths) >= limit:
            break
        low = url.lower()
        if any(x in low for x in ("video", "play-button", "play-icon", "gif", "icon", "sprite")):
            continue
        path = os.path.join(os.getcwd(), f"temp_{tag}_{idx}.jpg")
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(path, "wb") as f:
                    f.write(resp.content)
                paths.append(path)
        except Exception as e:
            print(f"❌ Image download failed: {e}")
    return paths


def _image_urls(driver):
    """Three strategies, best quality first."""
    urls, seen = [], set()

    # 1. data-a-dynamic-image maps: pick the widest rendition of each distinct image
    for el in driver.find_elements(By.XPATH, "//*[@data-a-dynamic-image]"):
        attr = el.get_attribute("data-a-dynamic-image")
        if not attr:
            continue
        try:
            data = json.loads(attr)
            if not data:
                continue
            best = max(data.items(), key=lambda kv: kv[1][0])[0]
            ident = best.split("/images/I/")[1].split(".")[0] if "/images/I/" in best else best
            if ident not in seen:
                seen.add(ident)
                urls.append(best)
        except Exception:
            continue
        if len(urls) > 7:
            break

    # 2. inline colorImages JSON
    if not urls:
        try:
            m = re.search(r"'colorImages':\s*\{\s*'initial':\s*(\[.+?\])", driver.page_source)
            if m:
                for img in json.loads(m.group(1)):
                    u = (img or {}).get("hiRes") or (img or {}).get("large")
                    if u and u not in urls:
                        urls.append(u)
        except Exception as e:
            print(f"⚠️ Inline image JSON failed: {e}")

    # 3. alt-thumbnails, upgraded to full size
    if not urls:
        for img in driver.find_elements(By.CSS_SELECTOR, "#altImages img, #altimages img, .imgTagWrapper img"):
            alt = (img.get_attribute("alt") or "").lower()
            src = img.get_attribute("data-old-hires") or img.get_attribute("src")
            if not src or src.startswith("data:") or "video" in alt:
                continue
            full = re.sub(r"\._[A-Za-z0-9_,\-]+_\.", ".", src)
            if full not in urls:
                urls.append(full)
    return urls


def _offer_percentage(driver):
    selectors = [
        ".apex-savings-percentage", "span.savingPercentage", "span.reinventPriceSavingsPercentageMargin",
        "span#price_inside_buybox_badging_text", "span.a-size-large.a-color-price",
    ]
    for css in selectors:
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, css):
                m = re.search(r"(\d+)\s*%", el.text or "")
                if m:
                    return int(m.group(1))
        except Exception:
            continue
    return 0


def _specs(driver, limit):
    bullets = driver.find_elements(By.CSS_SELECTOR, "#feature-bullets ul li span, #pqv-feature-bullets ul li span")
    texts = [b.text.strip() for b in bullets if len(b.text.strip()) > 10]
    return " | ".join(texts[:limit])


def _price(driver):
    for css in ("span.a-price-whole", "span.a-offscreen"):
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, css):
                text = (el.text or el.get_attribute("textContent") or "").strip()
                if text:
                    return text if text.startswith("₹") else f"₹{text}"
        except Exception:
            continue
    return "Check Link"


def _is_unavailable(driver):
    for css in (".primary-availability-message", "#availability"):
        try:
            for el in driver.find_elements(By.CSS_SELECTOR, css):
                if "currently unavailable" in (el.text or "").lower():
                    return True
        except Exception:
            continue
    return False


def _read_product_page(driver, asin, tag, spec_limit, image_limit):
    """Driver must already be on the product page. Returns a product dict or None."""
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#productTitle, #title")))
    if _is_unavailable(driver):
        print(f"⏭️ {asin}: currently unavailable.")
        return None

    name = ""
    for css in ("#productTitle", "#title", "h1.a-size-large"):
        els = driver.find_elements(By.CSS_SELECTOR, css)
        if els and els[0].text.strip():
            name = els[0].text.strip()
            break
    if not name:
        return None

    driver.execute_script("window.scrollTo(0, 350);")
    time.sleep(1.5)
    driver.execute_script("window.scrollTo(0, 0);")

    images = _download_images(_image_urls(driver), tag, image_limit)
    offer = _offer_percentage(driver)
    specs = _specs(driver, spec_limit)
    print(f"📈 {asin}: {offer}% off, {len(images)} images")
    return {
        "asin": asin,
        "name": name,
        "link": f"https://www.amazon.in/dp/{asin}?tag={os.getenv('Affiliate_Code')}",
        "price": _price(driver),
        "specs": specs,
        "images": images,
        "tags": generate_tags(name, specs),
        "offer_percentage": offer,
    }


def get_bestsellers(driver, count):
    """Scrape up to `count` products from a random bestseller category."""
    cat_name, cat_url = _pick_category()
    driver.set_window_size(1920, 1080)
    driver.get(cat_url)
    try:
        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".zg-grid-general-faceout")))
    except Exception:
        if _blocked(driver):
            print("❌ Amazon showed a captcha / robot check on the category page.")
        else:
            print("❌ Category page loaded without product cards.")
        return []

    # PHASE 1: collect candidates (links only), so later navigation can't invalidate them
    candidates = []
    for card in driver.find_elements(By.CSS_SELECTOR, ".zg-grid-general-faceout"):
        try:
            lines = [l.strip() for l in card.text.split("\n") if l.strip() and not l.strip().startswith("#")]
            name = lines[0] if lines else ""
            if any(b in name.lower() for b in BLACKLIST):
                print(f"⏭️ Blacklisted: {name[:50]}")
                continue
            href = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            m = re.search(r"/dp/([A-Z0-9]{10})", href or "")
            if m:
                candidates.append((m.group(1), href))
        except Exception:
            continue
    print(f"🧾 {len(candidates)} candidate products found in '{cat_name}'.")

    # PHASE 2: visit each product page independently
    category = cat_name if cat_name in HASHTAG_CATEGORIES else "Electronics"
    products = []
    for i, (asin, href) in enumerate(candidates[: max(count * 2, count)]):
        if len(products) >= count:
            break
        try:
            driver.get(href)
            product = _read_product_page(driver, asin, tag=str(i), spec_limit=7, image_limit=7)
            if product and product["images"]:
                product["category"] = category
                products.append(product)
        except Exception as e:
            print(f"⚠️ Skipping {asin}: {type(e).__name__}: {e}")
        time.sleep(random.uniform(1.5, 3.0))
    return products


def scrape_specific_product(driver, product_url):
    """Scrape one pasted product URL (short amzn.to / a.co links are followed by the browser)."""
    print(f"🎯 Manual target: {product_url}")
    driver.set_window_size(1920, 1080)
    try:
        driver.get(product_url)
        if _blocked(driver):
            print("❌ Blocked by captcha / robot check.")
            return None

        current = driver.current_url
        m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", current)
        if m:
            asin = m.group(1)
        else:
            try:
                asin = driver.find_element(By.ID, "ASIN").get_attribute("value")
            except Exception:
                asin = "MANUAL"
        print(f"🆔 Resolved ASIN: {asin}")

        product = _read_product_page(driver, asin, tag="manual", spec_limit=3, image_limit=5)
        if product:
            product["category"] = "Default"
        return product
    except Exception as e:
        print(f"❌ Manual scrape failed: {type(e).__name__}: {e}")
        return None
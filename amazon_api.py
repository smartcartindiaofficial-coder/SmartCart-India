"""
amazon_api.py - Amazon Creators API client for SmartCart India.

Replaces the Selenium scraping in scout.py. Uses plain `requests`, so there is
no SDK zip to install.

Config.env keys needed:
    CREATORS_CREDENTIAL_ID       (from Associates Central > Tools > Creators API)
    CREATORS_CREDENTIAL_SECRET   (shown only once when created)
    CREATORS_CREDENTIAL_VERSION  (e.g. 3.2 - copy the value Associates Central shows)
    Affiliate_Code               (your tracking ID, e.g. yourname-21)  <- already in use
Optional:
    DEAL_MIN_SAVING   minimum discount % to search for (default 20)
    CATEGORY_COOLDOWN_DAYS (default 4)

Public functions (both return dicts shaped like scout.py's old output, or None
when the API is unavailable so main.py can fall back to the old scraper):
    get_deal_products(count=5, exclude_asins=None) -> list[dict] | None
    get_product_by_url(url)                        -> dict | None
"""
import os
import re
import json
import time
import random
import datetime

import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "Config.env"))

API_BASE = "https://creatorsapi.amazon"
MARKETPLACE = "www.amazon.in"
TOKEN_ENDPOINTS = {  # chosen by credential version (India is in the EU group)
    "3.1": "https://api.amazon.com/auth/o2/token",
    "3.2": "https://api.amazon.co.uk/auth/o2/token",
    "3.3": "https://api.amazon.co.jp/auth/o2/token",
}
MIN_INTERVAL = 1.1  # seconds between calls; conservative start for the TPS limit

RESOURCES = [
    "images.primary.large",
    "images.variants.large",
    "itemInfo.title",
    "itemInfo.features",
    "offersV2.listings.price",
    "offersV2.listings.availability",
    "offersV2.listings.isBuyBoxWinner",
]

BLACKLIST = ["credit card", "gift card", "subscription", "recharge", "lpg", "amazon pay"]

# (display name used for hashtags in main.py, India SearchIndex, keywords to rotate)
# The API has NO "bestsellers" list, and keywords are required, so we rotate keywords.
CATEGORIES = [
    ("Computers & Accessories", "Computers", ["keyboard", "wireless mouse", "usb hub", "webcam", "laptop stand"]),
    ("Electronics", "Electronics", ["earbuds", "power bank", "smartwatch", "bluetooth speaker", "fast charger"]),
    ("Home & Kitchen", "HomeAndKitchen", ["kitchen organizer", "air fryer accessories", "water bottle", "storage container"]),
    ("Home Improvement", "ToolsAndHomeImprovement", ["tool kit", "led light", "smart plug", "cordless screwdriver"]),
    ("Car & Motorbike", "Automotive", ["car vacuum cleaner", "bike accessories", "car phone holder"]),
    ("Baby Products", "Baby", ["baby toys", "baby bottle", "baby care"]),
    ("Clothing & Accessories", "Apparel", ["men t-shirt", "women kurti", "jacket"]),
    ("Jewellery", "Jewelry", ["necklace", "earrings", "bracelet"]),
]


class CreatorsApiError(Exception):
    pass


class CreatorsApiAccessError(CreatorsApiError):
    """Missing/invalid credentials, or no API access (e.g. sales requirement not met)."""


_token = {"value": None, "expires_at": 0.0}
_last_call = 0.0


def _partner_tag():
    tag = os.getenv("Affiliate_Code")
    if not tag:
        raise CreatorsApiAccessError("Affiliate_Code (partner tag) missing in Config.env")
    return tag


def _get_token():
    """Fetch an OAuth token and cache it (it is valid for about 1 hour)."""
    if _token["value"] and time.time() < _token["expires_at"] - 60:
        return _token["value"]

    cid = os.getenv("CREATORS_CREDENTIAL_ID")
    secret = os.getenv("CREATORS_CREDENTIAL_SECRET")
    version = str(os.getenv("CREATORS_CREDENTIAL_VERSION", "3.2")).strip()
    if not cid or not secret:
        raise CreatorsApiAccessError("Creators API credentials missing in Config.env")
    endpoint = TOKEN_ENDPOINTS.get(version)
    if not endpoint:
        raise CreatorsApiAccessError(
            f"Credential version '{version}' not supported by this module (supports 3.1/3.2/3.3). "
            "For 2.x credentials use Amazon's official Python SDK."
        )

    r = requests.post(
        endpoint,
        json={"grant_type": "client_credentials", "client_id": cid,
              "client_secret": secret, "scope": "creatorsapi::default"},
        timeout=20,
    )
    if r.status_code != 200:
        raise CreatorsApiAccessError(f"Token request failed ({r.status_code}): {r.text[:200]}")
    data = r.json()
    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    return _token["value"]


def _call(path, payload, retries=3):
    """POST to the Creators API with throttling, token reuse and simple retries."""
    global _last_call
    for attempt in range(retries):
        wait = MIN_INTERVAL - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()

        r = requests.post(
            f"{API_BASE}{path}",
            headers={
                "Authorization": f"Bearer {_get_token()}",
                "Content-Type": "application/json",
                "x-marketplace": MARKETPLACE,
            },
            json=payload,
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()
        if r.status_code == 401 and attempt == 0:
            _token["value"] = None  # token may have expired early; fetch a fresh one
            continue
        if r.status_code in (401, 403):
            raise CreatorsApiAccessError(f"{r.status_code}: {r.text[:300]}")
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** (attempt + 1))
            continue
        raise CreatorsApiError(f"{r.status_code}: {r.text[:300]}")
    raise CreatorsApiError("Creators API retries exhausted")


# ---------- response parsing ----------

def _best_listing(item):
    listings = ((item.get("offersV2") or {}).get("listings")) or []
    for listing in listings:
        if listing.get("isBuyBoxWinner"):
            return listing
    return listings[0] if listings else None


def _image_urls(item, limit=7):
    images = item.get("images") or {}
    urls = []
    primary = ((images.get("primary") or {}).get("large") or {}).get("url")
    if primary:
        urls.append(primary)
    for variant in images.get("variants") or []:
        url = ((variant or {}).get("large") or {}).get("url")
        if url and url not in urls:
            urls.append(url)
    return urls[:limit]


def _download_images(urls, tag):
    """Save images as temp_<tag>_<n>.jpg in the working dir (what main.py expects)."""
    paths = []
    for idx, url in enumerate(urls):
        path = os.path.join(os.getcwd(), f"temp_{tag}_{idx}.jpg")
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(path, "wb") as f:
                    f.write(resp.content)
                paths.append(path)
        except Exception as e:
            print(f"[amazon_api] image download failed: {e}")
    return paths


def _parse_item(item, category, tag):
    """Turn an API item into the dict shape main.py already uses. None = skip it."""
    title = (((item.get("itemInfo") or {}).get("title")) or {}).get("displayValue") or ""
    if not title or any(b in title.lower() for b in BLACKLIST):
        return None

    listing = _best_listing(item)
    if not listing:
        return None  # no live offer -> nothing to buy
    availability = (listing.get("availability") or {}).get("type")
    if availability and availability != "IN_STOCK":
        return None

    price_info = listing.get("price") or {}
    offer_pct = int((price_info.get("savings") or {}).get("percentage") or 0)
    price = (price_info.get("money") or {}).get("displayAmount") or "Check Price"

    features = (((item.get("itemInfo") or {}).get("features")) or {}).get("displayValues") or []
    specs = " | ".join(f.strip()[:300] for f in features if len(f.strip()) > 10)

    image_paths = _download_images(_image_urls(item), tag)
    if not image_paths:
        return None

    return {
        "asin": item["asin"],
        "name": title,
        # detailPageURL already carries your tag; use it unmodified for attribution
        "link": item.get("detailPageURL", ""),
        "price": price,
        "specs": specs,
        "images": image_paths,
        "offer_percentage": offer_pct,
        "category": category,
    }


# ---------- category cooldown (same file/format scout.py used) ----------

def _pick_category():
    history_file = os.path.join(SCRIPT_DIR, "category_history.json")
    history = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
        except Exception:
            history = {}

    cooldown = int(os.getenv("CATEGORY_COOLDOWN_DAYS", "4"))
    now = datetime.datetime.now()
    eligible = []
    for entry in CATEGORIES:
        last = history.get(entry[0])
        if last and (now - datetime.datetime.fromisoformat(last)).days < cooldown:
            continue
        eligible.append(entry)
    if not eligible:
        eligible = list(CATEGORIES)

    choice = random.choice(eligible)
    history[choice[0]] = now.isoformat()
    try:
        with open(history_file, "w") as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        print(f"[amazon_api] could not save category history: {e}")
    return choice


# ---------- public functions ----------

def get_deal_products(count=5, exclude_asins=None):
    """Find discounted, in-stock, well-reviewed products. None = API unavailable."""
    exclude = set(exclude_asins or [])
    try:
        partner_tag = _partner_tag()
        name, search_index, keywords = _pick_category()
        min_saving = int(os.getenv("DEAL_MIN_SAVING", "20"))
        print(f"[amazon_api] category: {name}")

        products = []
        for attempt in range(3):  # try up to 3 keyword/page combos
            keyword = random.choice(keywords)
            payload = {
                "partnerTag": partner_tag,
                "marketplace": MARKETPLACE,
                "searchIndex": search_index,
                "keywords": keyword,
                "itemCount": 10,
                "itemPage": random.randint(1, 3),
                "minSavingPercent": min_saving,
                "minReviewsRating": 4,
                "sortBy": "Featured",
                "resources": RESOURCES,
            }
            # Path follows the getItems pattern; confirm against the SDK's
            # sample_search_items.py if you get a 404.
            data = _call("/catalog/v1/searchItems", payload)
            items = ((data.get("searchResult") or {}).get("items")) or []
            print(f"[amazon_api] '{keyword}': {len(items)} results")

            for i, item in enumerate(items):
                if item.get("asin") in exclude:
                    continue
                parsed = _parse_item(item, name, f"{len(products)}_{i}")
                if parsed:
                    products.append(parsed)
                if len(products) >= count:
                    return products
            if products:
                break
        return products
    except CreatorsApiAccessError as e:
        print(f"[amazon_api] API not available, falling back to scraper: {e}")
        return None
    except Exception as e:
        print(f"[amazon_api] unexpected error, falling back to scraper: {e}")
        return None


def extract_asin(url):
    """ASIN from a product URL; resolves short links (amzn.to / a.co) first."""
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    if match:
        return match.group(1)
    try:
        final = requests.head(url, allow_redirects=True, timeout=15).url
        match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", final)
        return match.group(1) if match else None
    except Exception:
        return None


def get_product_by_url(url):
    """Look up one product from a pasted URL (manual_urls.txt). None = API unavailable."""
    try:
        asin = extract_asin(url)
        if not asin:
            print(f"[amazon_api] could not find an ASIN in: {url}")
            return None
        payload = {
            "itemIds": [asin],
            "itemIdType": "ASIN",
            "marketplace": MARKETPLACE,
            "partnerTag": _partner_tag(),
            "resources": RESOURCES,
        }
        data = _call("/catalog/v1/getItems", payload)
        items = ((data.get("itemsResult") or {}).get("items")) or []
        if not items:
            return None
        return _parse_item(items[0], "Default", "manual_0")
    except CreatorsApiAccessError as e:
        print(f"[amazon_api] API not available, falling back to scraper: {e}")
        return None
    except Exception as e:
        print(f"[amazon_api] unexpected error, falling back to scraper: {e}")
        return None
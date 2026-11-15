"""
insta_uploader.py - Instagram Reels publisher (Meta Graph API + Supabase free storage).

Changes vs the old version
  * Graph API version comes from GRAPH_API_VERSION (default v23.0) instead of a
    hard-coded old v19.0. Check Meta's changelog now and then and bump it.
  * The Supabase file is ALWAYS deleted (try/finally), even if Meta fails, so
    your free 1 GB bucket doesn't fill up with orphans.
  * The returned link is the REAL permalink (the old media-id URL was broken).
  * Timeouts on every request, clearer token-expiry message.
  * `upload_to_tmpfiles` renamed to `_upload_to_supabase` (it never used tmpfiles).
  * The buy link is used exactly as given (not rewritten).
  * Supabase key can be SUPABASE_SECRET_KEY or the old `Superbase_Secret_Key`.

TIP (free): if INSTAGRAM_ACCESS_TOKEN is a PAGE access token derived from a
long-lived user token, it does not expire. User tokens expire after ~60 days.
"""
import os
import time
import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "Config.env"))

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
GRAPH = f"https://graph.facebook.com/{os.getenv('GRAPH_API_VERSION', 'v23.0')}"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("Superbase_Secret_Key")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "instagram-assets")  # create it in the Supabase dashboard (public)

HTTP_TIMEOUT = 30
POLL_INTERVAL = 10
POLL_MAX_ATTEMPTS = 45  # ~7.5 minutes


def _supabase():
    from supabase import create_client  # lazy: only needed when Instagram is enabled
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _upload_to_supabase(local_video_path):
    """Upload the MP4 to a public Supabase bucket and return its public URL (Meta needs a URL)."""
    print("☁️ Uploading video to Supabase Storage...")
    try:
        filename = os.path.basename(local_video_path)
        with open(local_video_path, "rb") as f:
            _supabase().storage.from_(BUCKET_NAME).upload(
                path=filename, file=f,
                file_options={"content-type": "video/mp4", "upsert": "true"},
            )
        url = _supabase().storage.from_(BUCKET_NAME).get_public_url(filename)
        print(f"🔗 Public URL ready: {url}")
        return url, filename
    except Exception as e:
        print(f"❌ Supabase upload failed: {e}")
        return None, None


def _delete_from_supabase(filename):
    try:
        _supabase().storage.from_(BUCKET_NAME).remove([filename])
        print(f"🗑️ Removed temporary asset from Supabase: {filename}")
    except Exception as e:
        print(f"⚠️ Could not delete {filename} from Supabase: {e}")


def _api_error(payload):
    err = payload.get("error") if isinstance(payload, dict) else None
    if not err:
        return None
    if err.get("code") == 190:
        return "Access token expired/invalid (code 190). Generate a new long-lived or Page token."
    return err.get("message", "Unknown API error")


def _wait_until_ready(container_id):
    params = {"fields": "status_code,status", "access_token": ACCESS_TOKEN}
    for attempt in range(1, POLL_MAX_ATTEMPTS + 1):
        time.sleep(POLL_INTERVAL)
        try:
            data = requests.get(f"{GRAPH}/{container_id}", params=params, timeout=HTTP_TIMEOUT).json()
        except Exception as e:
            print(f"⚠️ Network error checking status: {e}. Retrying...")
            continue

        error = _api_error(data)
        if error:
            print(f"🔄 Meta API warning: {error}. Waiting...")
            continue

        code = data.get("status_code")
        print(f"🔄 Meta processing status: {code} ({attempt}/{POLL_MAX_ATTEMPTS})")
        if code == "FINISHED":
            return True
        if code in ("EXPIRED", "ERROR"):
            print(f"❌ Meta pipeline {code}: {data.get('status', 'no details supplied')}")
            return False
    print("❌ Meta processing timed out.")
    return False


def upload_to_instagram(local_video_path, description_text, buy_link):
    """Publish a Reel. Returns the Reel's permalink, or None on failure."""
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("❌ Instagram credentials missing in Config.env.")
        return None
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase URL/secret key missing in Config.env.")
        return None

    public_url, remote_name = _upload_to_supabase(local_video_path)
    if not public_url:
        return None

    try:
        print("🎬 Creating Meta Reel container...")
        res = requests.post(
            f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media",
            data={
                "media_type": "REELS",
                "video_url": public_url,
                "caption": description_text[:2200],  # Instagram caption limit
                "access_token": ACCESS_TOKEN,
            },
            timeout=HTTP_TIMEOUT,
        ).json()
        container_id = res.get("id")
        if not container_id:
            print(f"❌ Container creation failed: {_api_error(res) or res}")
            return None
        print(f"⏳ Container {container_id} created. Waiting for Meta to process...")

        if not _wait_until_ready(container_id):
            return None

        print("⏳ Giving Meta 10s to sync before publishing...")
        time.sleep(10)

        pub = requests.post(
            f"{GRAPH}/{INSTAGRAM_ACCOUNT_ID}/media_publish",
            data={"creation_id": container_id, "access_token": ACCESS_TOKEN},
            timeout=HTTP_TIMEOUT,
        ).json()
        media_id = pub.get("id")
        if not media_id:
            print(f"❌ Publish failed: {_api_error(pub) or pub}")
            return None
        print(f"🚀 Reel is live on Instagram! Media ID: {media_id}")

        # First comment with the buy link (links in comments are not clickable on Instagram,
        # but people can copy them; the bio/website link is the clickable route).
        for attempt in (1, 2):
            try:
                c = requests.post(
                    f"{GRAPH}/{media_id}/comments",
                    data={"message": f"🛍️ Direct buy link: {buy_link}", "access_token": ACCESS_TOKEN},
                    timeout=HTTP_TIMEOUT,
                ).json()
                if c.get("id"):
                    print("✅ Instagram first comment posted.")
                    break
                print(f"⚠️ Comment attempt {attempt} failed: {_api_error(c) or c}")
            except Exception as e:
                print(f"⚠️ Comment attempt {attempt} error: {e}")
            time.sleep(5)

        # Real permalink (the media id is NOT the URL shortcode)
        permalink = f"https://www.instagram.com/{os.getenv('INSTAGRAM_USERNAME', 'smartcartindiaofficial')}/"
        try:
            info = requests.get(
                f"{GRAPH}/{media_id}",
                params={"fields": "permalink", "access_token": ACCESS_TOKEN},
                timeout=HTTP_TIMEOUT,
            ).json()
            permalink = info.get("permalink") or permalink
        except Exception:
            pass
        return permalink

    except Exception as e:
        print(f"❌ Instagram Graph API error: {e}")
        return None
    finally:
        _delete_from_supabase(remote_name)
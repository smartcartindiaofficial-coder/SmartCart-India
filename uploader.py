"""
uploader.py - YouTube Shorts uploader (YouTube Data API v3, free quota).

Changes vs the old version
  * Signature is now upload_to_youtube(video_path, title, description, tags)
    (the unused `driver` argument is gone - main.py is updated to match).
  * token.pickle / client_secrets.json are looked up next to this file, not in
    whatever folder you launched from.
  * In GitHub Actions it never tries to open a browser login (that would hang);
    it fails with a clear message instead.
  * Expired/revoked refresh tokens are handled instead of crashing.
  * Chunked, retrying upload (survives a flaky connection).
  * The garbled poll characters and the dead duplicate `except` block are gone.
  * The buy link is taken exactly as posted in the description (not rewritten).

REMINDER: if your Google Cloud OAuth consent screen is in "Testing" status,
refresh tokens expire after 7 days. Set it to "In production" (you can stay
unverified for your own account) so the login lasts.

Quota note: videos.insert costs ~1600 of your 10,000 free daily units (about
6 uploads/day); a comment costs ~50.
"""
import os
import re
import time
import pickle
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "Config.env"))

TOKEN_PATH = os.path.join(SCRIPT_DIR, "token.pickle")
SECRETS_PATH = os.path.join(SCRIPT_DIR, "client_secrets.json")
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # needed for comments
]
IN_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"

# Engagement-poll window (IST): Wed(2), Fri(4), Sat(5) after 5 PM
POLL_DAYS = (2, 4, 5)
POLL_FROM_HOUR = 17


def _load_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, "wb") as f:
                pickle.dump(creds, f)
            return creds
        except RefreshError as e:
            print(f"⚠️ YouTube refresh token rejected ({e}).")
            creds = None

    if IN_ACTIONS:
        raise RuntimeError(
            "YouTube login expired and GitHub Actions cannot open a browser. Run main.py locally once "
            "to refresh token.pickle, then update the copy your workflow uses. (Tip: put the OAuth "
            "consent screen 'In production' so tokens stop expiring every 7 days.)"
        )
    if not os.path.exists(SECRETS_PATH):
        raise FileNotFoundError(f"'client_secrets.json' missing. Download it from Google Cloud Console into: {SCRIPT_DIR}")

    flow = InstalledAppFlow.from_client_secrets_file(SECRETS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "wb") as f:
        pickle.dump(creds, f)
    return creds


def get_youtube_service():
    return build("youtube", "v3", credentials=_load_credentials())


def _short_phrase(text, max_words=4):
    clean = re.sub(r"[^a-zA-Z0-9\s\-\.]", "", text).strip()
    words = clean.split()
    return (" ".join(words[:max_words]) + "...") if len(words) > max_words else " ".join(words)


def _poll_options(description):
    """Pull 2 feature names out of the description; fall back to safe defaults."""
    options = []
    for feat in re.findall(r"\[([^\]]+)\]", description):
        phrase = _short_phrase(feat)
        if phrase and "FEATURES" not in phrase.upper():
            options.append(phrase)
    if not options:
        for line in description.split("\n"):
            line = line.strip()
            if ":" in line and line[:1] in "-*":
                phrase = _short_phrase(line.split(":")[0].strip("-* "))
                if phrase and not any(w in phrase.upper() for w in ("FEATURES", "APPLICATIONS")):
                    options.append(phrase)
    a = options[0] if len(options) > 0 else "High Performance Build"
    b = options[1] if len(options) > 1 else "Value for Money"
    return a, b


def _build_comment(description):
    match = re.search(r"Buy Link:\s*(https://\S+)", description) or re.search(r"https://\S+", description)
    buy_link = (match.group(1) if match and match.lastindex else (match.group(0) if match else "")).strip()

    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(timezone.utc).astimezone(ist)
    if now.weekday() in POLL_DAYS and now.hour >= POLL_FROM_HOUR:
        a, b = _poll_options(description)
        return (
            "📊 QUICK POLL: Which feature matters most to you?\n\n"
            f"🔹 A: {a}\n"
            f"🔸 B: {b}\n"
            "🔷 C: Premium Design & Brand Trust\n\n"
            "👇 Reply below with your choice (A, B, or C)!\n\n"
            f"🛍️ Direct Buy Link: {buy_link}\n"
            "👉 Subscribe to SmartCart India for daily smart finds!"
        )
    return f"🛍️ Direct Buy Link: {buy_link}\n\n👉 Subscribe for daily smart finds!"


def _post_comment(youtube, video_id, text):
    body = {"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": text}}}}
    for attempt in (1, 2):  # a brand-new video can reject comments for a few seconds
        try:
            youtube.commentThreads().insert(part="snippet", body=body).execute()
            print("✅ YouTube comment posted.")
            return True
        except Exception as e:
            print(f"⚠️ YouTube comment attempt {attempt} failed: {e}")
            time.sleep(8)
    return False


def _resumable_upload(request, max_retries=5):
    response = None
    retries = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"📦 Uploaded {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and retries < max_retries:
                retries += 1
                wait = (2 ** retries) + random.random()
                print(f"⚠️ YouTube server error {e.resp.status}; retry {retries}/{max_retries} in {wait:.0f}s")
                time.sleep(wait)
            else:
                raise
    return response


def upload_to_youtube(video_path, title, description, tags):
    """Upload a Short. Returns the youtube.com/shorts/<id> URL, or None on failure."""
    print(f"🚀 [YouTube] Uploading: {title[:40]}...")
    try:
        youtube = get_youtube_service()

        clean_title = title.replace("<", "").replace(">", "").strip()[:100]
        clean_desc = description.replace("<", "").replace(">", "")
        if "#shorts" not in clean_desc.lower():
            clean_desc += "\n\n#Shorts"
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        body = {
            "snippet": {"title": clean_title, "description": clean_desc, "tags": tag_list, "categoryId": "22"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        media = MediaFileUpload(os.path.abspath(video_path), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

        response = _resumable_upload(request)
        video_id = response["id"]
        print(f"🎉 [YouTube] Published. Video ID: {video_id}")

        try:
            _post_comment(youtube, video_id, _build_comment(description))
        except Exception as e:
            print(f"⚠️ Comment routine failed (video is still live): {e}")

        return f"https://youtube.com/shorts/{video_id}"
    except Exception as e:
        print(f"❌ [YouTube] Upload failed: {e}")
        return None
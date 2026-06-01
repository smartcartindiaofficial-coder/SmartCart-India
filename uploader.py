import os
import time
import pickle
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, 'Config.env')
load_dotenv(ENV_PATH)

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.force-ssl' # Gives full comment threading access
]

def clean_amazon_url(url):
    """
    Strips unnecessary tracking parameters from an Amazon link,
    leaving a clean, short URL that is easier to copy/read.
    """
    import re
    # Look for the product ID standard pattern (ASIN)
    asin_match = re.search(r'/(dp|gp/product)/([A-Z0-9]{10})', url)
    if asin_match:
        asin = asin_match.group(2)
        # Rebuild a clean short link using your store tag
        return f"https://amazon.in/dp/{asin}/?tag={os.getenv("Affiliate_Code")}"
    return url

def get_youtube_service():
    """Handles OAuth2 authentication and returns a YouTube API service object."""
    creds = None
    # token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # If there are no valid credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('client_secrets.json'):
                raise FileNotFoundError(
                    "❌ 'client_secrets.json' missing! Please download it from Google Cloud Console "
                    "and place it in your root folder: {current_working_dir}"
                )
            flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

def upload_to_youtube(driver, video_path, title, description, tags):
    """
    Uploads a video to YouTube using the official YouTube Data API v3.
    Accepts 'driver' parameter to keep signature compatibility with main.py,
    but does not use it.
    """
    print(f"🚀 [API] Initiating secure upload for: {title[:30]}...")
    
    try:
        youtube = get_youtube_service()
        
        # Format tags string into a list structure expected by the API
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        body = {
            'snippet': {
                'title': title[:100], # YouTube limit
                'description': description,
                'tags': tag_list,
                'categoryId': '22'  # 22 represents 'People & Blogs' / standard shorts category
            },
            'status': {
                'privacyStatus': 'public',
                'selfDeclaredMadeForKids': False
            }
        }

        # Setup the media file upload wrapper
        media = MediaFileUpload(
            os.path.abspath(video_path), 
            chunksize=-1, 
            resumable=True, 
            mimetype='video/mp4'
        )

        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        print("📤 Uploading video chunks directly to Google servers...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"📦 Uploaded {int(status.progress() * 100)}%")

        print(f"🎉 SUCCESS: Video Published via API! Video ID: {response['id']}")
        youtube_video_id = response['id']
        
        # ─── 🚀 AUTOMATED FIRST COMMENT YOUTUBE LAYER ───
        try:
            print("💬 Dropping pinned-style channel comment onto YouTube Short...")
            import re
            link_match = re.search(r'https://[^\s]+', description)
            buy_link = link_match.group(0) if link_match else ""
            
            comment_body = {
                "snippet": {
                    "videoId": youtube_video_id,
                    "topLevelComment": {
                        "snippet": {
                            'textOriginal': f"🛍️ Clickable Direct Buy Link: {clean_amazon_url(buy_link)}\n\n👉 Subscribe for daily smart tech finds!"
                        }
                    }
                }
            }
            # Execute the comment insert API call using the same authenticated 'youtube' service object
            youtube.commentThreads().insert(
                part="snippet",
                body=comment_body
            ).execute()
            print("✅ YouTube channel first comment dropped successfully!")
        except Exception as yt_comment_err:
            print(f"⚠️ Could not drop automated YouTube comment: {yt_comment_err}")
        # ────────────────────────────────────────────────

        # Build the clean, official YouTube Shorts watch link
        youtube_shorts_url = f"https://youtube.com/shorts/{youtube_video_id}"
        return youtube_shorts_url

    except Exception as e:
        print(f"❌ YouTube API Upload Failed: {e}")
        return None # Return None if the upload fails
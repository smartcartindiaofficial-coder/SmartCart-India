import os
import time
import requests
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__ ))
ENV_PATH = os.path.join(SCRIPT_DIR, 'Config.env')
load_dotenv(ENV_PATH)

ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

def clean_amazon_url(url):
    import re
    asin_match = re.search(r'/(dp|gp/product)/([A-Z0-9]{10})', url)
    if asin_match:
        asin = asin_match.group(2)
        return f"https://amazon.in/dp/{asin}/?tag={os.getenv('Affiliate_Code')}"
    return url

from supabase import create_client, Client

# Configuration Constants
SUPABASE_URL = "https://pdyuqhzzasveetsrotpa.supabase.co"
# Use the service_role key to bypass RLS policies during backend creation
SUPABASE_KEY = "sb_secret__1Sq_kzL_lDP9EWWwQ_6wg_S6poTJs-" 
BUCKET_NAME = "instagram-assets" # Create this bucket in your Supabase dashboard

def upload_to_tmpfiles(local_video_path):
    """
    Uploads the video asset directly to a secure Supabase storage bucket
    and generates an unrestricted public URL for Meta ingestion.
    """
    print(f"☁️ Uploading dynamic video asset to Supabase Storage...")
    try:
        # Initialize Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Dynamically extract original filename (e.g. Video_B0G64G1VMB.mp4)
        dynamic_filename = os.path.basename(local_video_path)
        
        # Open file as binary stream
        with open(local_video_path, 'rb') as f:
            # Upload to your bucket (upsert=True overrides old duplicate files)
            res = supabase.storage.from_(BUCKET_NAME).upload(
                path=dynamic_filename,
                file=f,
                file_options={"content-type": "video/mp4", "upsert": "true"}
            )
            
        # Generate the permanent public asset link
        direct_url = supabase.storage.from_(BUCKET_NAME).get_public_url(dynamic_filename)
        print(f"🔗 Public temporary URL generated: {direct_url}")
        return direct_url
        
    except Exception as e:
        print(f"❌ Temporary cloud upload failed: {e}")
        return None

def upload_to_instagram(local_video_path, description_text, buy_link):
    """
    Accepts the local file path on the runner, uploads it temporarily,
    and passes it straight to Meta Graph API.
    """
    if not ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        print("❌ Instagram Credentials missing from environment.")
        return None

    # Get a working public URL instantly
    public_video_url = upload_to_tmpfiles(local_video_path)
    if not public_video_url:
        print("❌ Aborting Instagram post: Could not generate public file asset link.")
        return None

    print(f"🎬 Initiating Meta Container Ingestion for URL: {public_video_url}")
    
    try:
        # Step 1: Initialize Container
        url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media"
        payload = {
            'media_type': 'REELS',
            'video_url': public_video_url,
            'caption': description_text,
            'access_token': ACCESS_TOKEN
        }
        
        res = requests.post(url, data=payload).json()
        container_id = res.get('id')
        
        if not container_id:
            print(f"❌ Container Ingestion Failed: {res}")
            return None
            
        print(f"⏳ Video Container Created (ID: {container_id}). Waiting for Meta processing...")
        
        # Step 2: Await Meta Processing completion
        status_url = f"https://graph.facebook.com/v19.0/{container_id}"
        # Request both status_code AND error_info to get maximum details
        status_params = {'fields': 'status_code, status', 'access_token': ACCESS_TOKEN}
        
        attempts = 0
        while attempts < 30:
            time.sleep(5)
            attempts += 1
            
            try:
                response = requests.get(status_url, params=status_params)
                status_res = response.json()
            except Exception as e:
                print(f"⚠️ Network error while checking status: {e}. Retrying...")
                continue

            if "error" in status_res:
                error_msg = status_res["error"].get("message", "Unknown API error")
                print(f"🔄 Meta API Sync Warning: {error_msg}. Server syncing, waiting...")
                continue 

            status_code = status_res.get('status_code')
            print(f"🔄 Meta Processing Status: {status_code}")

            if status_code == 'FINISHED':
                break
            elif status_code == 'EXPIRED':
                print("❌ Meta container expired.")
                return None
            elif status_code == 'ERROR':
                # The 'status' field contains Meta's explanation for the upload/pipeline failure
                failure_reason = status_res.get('status', 'No specific error context supplied by Meta.')
                print(f"❌ Meta conversion pipeline error: {status_code}")
                print(f"🔍 Root Cause Details: {failure_reason}")
                return None

        # Step 3: Publish container live
        publish_url = f"https://graph.facebook.com/v19.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {'creation_id': container_id, 'access_token': ACCESS_TOKEN}
        publish_res = requests.post(publish_url, data=publish_payload).json()
        
        published_media_id = publish_res.get('id')
        if published_media_id:
            print(f"🚀 SUCCESS: Reel is officially live on Instagram! ID: {published_media_id}")
            
            # Step 4: Drop First Comment (Affiliate Link)
            try:
                comment_url = f"https://graph.facebook.com/v19.0/{published_media_id}/comments"
                comment_payload = {
                    'message': f"🛍️ Direct buy link: {clean_amazon_url(buy_link)}",
                    'access_token': ACCESS_TOKEN
                }
                requests.post(comment_url, data=comment_payload)
                print("✅ Instagram first comment dropped successfully!")
            except Exception as comment_err:
                print(f"⚠️ Could not drop automated Instagram comment: {comment_err}")

            return f"https://www.instagram.com/p/{published_media_id}/"
        else:
            print(f"❌ Publishing Execution Failed: {publish_res}")
            return None

    except Exception as e:
        print(f"❌ Instagram Graph API Error: {e}")
        return None
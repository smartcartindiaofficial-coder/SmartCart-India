import os
import time
import requests
import http.server
import socketserver
import threading
try:
    from pyngrok import ngrok, conf
except ImportError:
    print("🌐 Running in cloud environment: 'pyngrok' module bypassed.")
    ngrok = None
    conf = None
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, 'Config.env')
load_dotenv(ENV_PATH)

# --- CONFIGURATION ---
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")       # For Instagram upload functions
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
PORT = int(os.getenv("LOCAL_SERVER_PORT", 8000))

NGROK_BINARY_PATH = os.path.join(os.getcwd(), "ngrok.exe")
conf.get_default().request_timeout = 90
conf.get_default().ngrok_path = NGROK_BINARY_PATH

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
        return f"https://amazon.in/dp/{asin}/?tag={os.getenv('Affiliate_Code')}"
    return url

def start_local_server(directory, port):
    """Starts a quiet background HTTP server serving the video folder."""
    class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress normal logging to keep terminal clean

    os.chdir(directory)
    handler = QuietHTTPRequestHandler
    httpd = socketserver.TCPServer(("", port), handler)
    return httpd

def upload_to_instagram(video_path, caption):
    """
    Creates a dynamic Ngrok tunnel to host your local MP4 file,
    submits it to Meta via the correct Business endpoint routing layer,
    monitors container creation status, and publishes it live to Instagram 
    AND Facebook Page Reels.
    """
    if not os.path.exists(video_path):
        print(f"❌ File error: {video_path} does not exist.")
        return None

    video_dir = os.path.dirname(video_path)
    print(f"video directory: {video_dir}")
    video_filename = os.path.basename(video_path)

    # 1. Initialize localized static server
    httpd = start_local_server(video_dir, PORT)
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    public_url = None
    try:
        # 2. Expose local file endpoint via Ngrok
        tunnel = ngrok.connect(PORT, "http")
        public_url = tunnel.public_url
        video_url = f"{public_url}/{video_filename}"
        print(f"🌐 Secure Proxy Tunnel initialized: {video_url}")
        
        print("🎬 Initiating Meta Reel Asset Container...")
        container_url = f"https://graph.facebook.com/v22.0/{INSTAGRAM_ACCOUNT_ID}/media"
        
        container_payload = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': ACCESS_TOKEN
        }

        # Submit Request
        response = requests.post(container_url, data=container_payload, timeout=60)
        container_res = response.json()

        if 'id' not in container_res:
            print(f"❌ Instagram Container Creation Failed: {container_res}")
            return None

        creation_id = container_res['id']
        print(f"📦 Container successfully spawned. ID: {creation_id}. Verification processing...")

        # 3. Monitor compilation status
        status_url = f"https://graph.facebook.com/v22.0/{creation_id}"
        status_payload = {
            'fields': 'status_code',
            'access_token': ACCESS_TOKEN
        }

        while True:
            time.sleep(15)
            status_res = requests.get(status_url, params=status_payload, timeout=30).json()
            status_code = status_res.get('status_code')
            
            if status_code == 'FINISHED':
                print("✅ Video encoding finished on Instagram!")
                break
            elif status_code == 'ERROR':
                print(f"❌ Meta Video Processing Error: {status_res}")
                return None
            else:
                print(f"🔄 Processing Status: {status_code}...")

        # 4. Publish live to Instagram
        print("🚀 Publishing Container to Live Instagram Feed...")
        publish_url = f"https://graph.facebook.com/v22.0/{INSTAGRAM_ACCOUNT_ID}/media_publish"
        publish_payload = {
            'creation_id': creation_id, 
            'access_token': ACCESS_TOKEN
        }
        time.sleep(10)
        publish_res = requests.post(publish_url, data=publish_payload).json()
        
        if 'id' in publish_res:
            published_media_id = publish_res['id']
            print(f"🎉 SUCCESS: Reel live on Instagram! Post ID: {published_media_id}")
            
            # ─── 🚀 AUTOMATED FIRST COMMENT EXTRACTION LAYER ───
            try:
                print("💬 Dropping automated first comment onto Instagram Reel...")
                comment_url = f"https://graph.facebook.com/v22.0/{published_media_id}/comments"
                
                import re
                link_match = re.search(r'https://[^s]+', caption)
                buy_link = link_match.group(0) if link_match else "Check our profile link!"
                
                comment_payload = {
                    'message': f"🛍️ Link to buy is pinned in our BIO profile page!\n\nOr copy this clean link: {clean_amazon_url(buy_link)}",
                    'access_token': ACCESS_TOKEN
                }
                comment_res = requests.post(comment_url, data=comment_payload).json()
                if 'id' in comment_res:
                    print("✅ Instagram first comment dropped successfully!")
                else:
                    print(f"⚠️ Comment payload warning: {comment_res}")
            except Exception as comment_err:
                print(f"⚠️ Could not drop automated Instagram comment: {comment_err}")
            # ───────────────────────────────────────────────────

            return f"https://www.instagram.com/p/{published_media_id}/"
        else:
            print(f"❌ Publishing Execution Failed: {publish_res}")
            return None

    except Exception as e:
        print(f"❌ Instagram Graph API Error: {e}")
        return None

    finally:
        print("🧹 Tearing down secure tunnel and closing local file server...")
        try:
            # Check if ngrok module was imported before calling disconnect/kill
            if ngrok and 'public_url' in locals() and public_url:
                ngrok.disconnect(public_url)
            if ngrok:
                ngrok.kill()
            
            if 'httpd' in locals() and httpd:
                httpd.shutdown()       # Stops the serve_forever loop
                httpd.server_close()   # Explicitly closes the socket connection!
            print("🔒 Clean shutdown of server complete.")
        except Exception as e:
            print(f"⚠️ Error during server teardown: {e}")
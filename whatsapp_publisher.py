import base64
import os
import requests

WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")
CHANNEL_ID = os.getenv("WHATSAPP_CHANNEL_ID")  # e.g., '120363171744447809@newsletter'
BASE_URL = "https://gate.whapi.cloud"  # Example using Whapi gateway


def post_to_whatsapp_channel(media_path: str, caption: str):
  """Sends an image/video with caption/affiliate link to a WhatsApp Channel."""
  if not WHATSAPP_API_TOKEN or not CHANNEL_ID:
    print("WhatsApp credentials missing in environment variables.")
    return False

  headers = {
      "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
      "Content-Type": "application/json",
  }

  # Determine if it's an image or video based on extension
  is_video = media_path.lower().endswith((".mp4", ".mov"))
  endpoint = f"{BASE_URL}/messages/" + ("video" if is_video else "image")

  # Read and encode local media file to base64 data URI
  try:
    with open(media_path, "rb") as f:
      encoded_file = base64.b64encode(f.read()).decode("utf-8")

    mime_type = "video/mp4" if is_video else "image/jpeg"
    media_data = f"data:{mime_type};base64,{encoded_file}"

    payload = {
        "to": CHANNEL_ID,
        "media": media_data,
        "caption": caption,  # Contains your affiliate text & link
    }

    response = requests.post(endpoint, json=payload, headers=headers)
    response.raise_for_status()

    print("Successfully broadcasted post to WhatsApp Channel!")
    return True

  except Exception as e:
    print(f"Failed to post to WhatsApp Channel: {e}")
    return False
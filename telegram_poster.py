import os
import telebot
from telebot import apihelper
from dotenv import load_dotenv

# ─── FORCE ROOT FOLDER PATH LOOKUP FOR TELEGRAM ───
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, 'Config.env')
load_dotenv(ENV_PATH)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not BOT_TOKEN:
    raise ValueError(
        f"❌ Critical Config Error: 'TELEGRAM_BOT_TOKEN' was not found in your environment!\n"
        f"The script searched explicitly inside: {ENV_PATH}\n"
        f"Please verify your file placement and ensure the key name matches exactly."
    )

apihelper.CONNECT_TIMEOUT = 120
apihelper.READ_TIMEOUT = 120

bot = telebot.TeleBot(BOT_TOKEN)

def post_to_telegram(product_name, product_link, media_path, youtube_url=None, price="Check Website"):
    """
    Sends the video/image to Telegram with a professional caption formatted in clean HTML.
    Bypasses Markdown parsing errors completely.
    """
    
    # 1. Build the caption text block using standard HTML tags
    caption = f"📦 <b>{product_name}</b>\n\n"
    
    if youtube_url:
        caption += f"🎬 <b>Watch on YouTube Shorts (Like & Subscribe!):</b>\n{youtube_url}\n\n"
        
    caption += (
        f"💰 <b>Price:</b> {price}\n"
        f"🔗 <a href='{product_link}'>Click Here to Buy on Amazon</a>\n\n"
        f"#AmazonFinds #SmartCartIndia #Deals"
    )
    
    try:
        if os.path.exists(media_path):
            # Check if it's a video or image
            if media_path.endswith(('.mp4', '.mov')):
                with open(media_path, 'rb') as video:
                    bot.send_video(
                        CHANNEL_ID, 
                        video, 
                        caption=caption, 
                        parse_mode="HTML",  # Switched to stable HTML engine
                        timeout=120
                    )
            else:
                with open(media_path, 'rb') as photo:
                    bot.send_photo(
                        CHANNEL_ID, 
                        photo, 
                        caption=caption, 
                        parse_mode="HTML"   # Switched to stable HTML engine
                    )
            print(f"🚀 Media post successful for: {product_name[:20]}")
            return True
        else:
            # Fallback to text only if media is missing
            bot.send_message(CHANNEL_ID, caption, parse_mode="HTML")
            return True

    except Exception as e:
        print(f"❌ Telegram Media Error: {e}")
        return False
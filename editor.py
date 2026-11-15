"""
editor.py - renders the vertical (1080x1920) promo video.

Changes vs the old version
  SPEED
  * Blurred backgrounds are computed ONCE per image (the old code re-blurred a
    1080x1920 frame with a 151px kernel for every single frame, twice during
    cross-fades). The blur now runs at quarter size and is scaled up.
  * Progress bar only touches its own 12px strip (no full-frame copy per frame).
  * Logo/outro canvas is built once and reused; vectorised alpha blending
    (no per-channel Python loops).
  * The random 5-15 s sleep (a leftover from TTS rate-limiting) is gone.
  * Output is written at 24 fps (what the frames were rendered at) instead of
    re-timing to 30.
  FIXES
  * Subtitle wrapping now measures with the SAME font/case that is drawn (the old
    code measured lower-case SIMPLEX but drew upper-case COMPLEX, so long lines
    ran off-screen). Non-ASCII characters (₹, emoji) are dropped because OpenCV's
    built-in fonts cannot draw them (they showed up as "???").
  * No zoom "jump" on the last image, and no missing outro time when the logo
    file is absent.
  * Assets (logos, Background_Music) are found next to this file, not in the
    launch directory.
  * Voiceover (edge-tts) is optional and OFF by default, as in your current setup:
    set ENABLE_VOICEOVER=1 to turn it on. MoviePy v1 and v2 are both supported.
  * Music volume is configurable with MUSIC_VOLUME (default 1.0).

Use only royalty-free music in Background_Music/ - otherwise YouTube/Instagram can
mute or claim your videos.
"""
import os
import re
import random
from functools import lru_cache

import cv2
import numpy as np

try:  # MoviePy v2.x
    from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
except ImportError:  # MoviePy v1.x
    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

W, H = 1080, 1920
FPS = 24
TOTAL_SECONDS = 15
OUTRO_SECONDS = 3
THUMB_SECONDS = 1.2
TRANSITION_FRAMES = 12
SUBTITLE_Y = 1600
SUBTITLE_MAX_W = 940           # keeps text inside the 1080px frame with margins
SUB_FONT = cv2.FONT_HERSHEY_COMPLEX
SUB_SCALE = 1.3
SUB_THICK = 3

ENABLE_VOICEOVER = os.getenv("ENABLE_VOICEOVER", "0") == "1"
MUSIC_VOLUME = float(os.getenv("MUSIC_VOLUME", "1.0"))


# ----------------------------------------------------------------------------
# MoviePy v1/v2 compatibility helpers
# ----------------------------------------------------------------------------
def _subclip(clip, start, end):
    return clip.subclipped(start, end) if hasattr(clip, "subclipped") else clip.subclip(start, end)


def _scale_volume(clip, factor):
    if abs(factor - 1.0) < 1e-6:
        return clip
    return clip.with_volume_scaled(factor) if hasattr(clip, "with_volume_scaled") else clip.volumex(factor)


def _with_audio(video, audio):
    return video.with_audio(audio) if hasattr(video, "with_audio") else video.set_audio(audio)


# ----------------------------------------------------------------------------
# OPTIONAL VOICEOVER (edge-tts, free). Off by default.
# ----------------------------------------------------------------------------
def generate_voiceover(text, output_audio_path):
    try:
        import asyncio
        import edge_tts
    except ImportError:
        print("⚠️ edge-tts not installed; skipping voiceover (pip install edge-tts).")
        return False

    voice = random.choice([
        "en-IN-PrabhatNeural", "en-IN-NeerjaNeural", "en-US-GuyNeural",
        "en-US-AriaNeural", "en-GB-RyanNeural", "en-GB-SoniaNeural",
    ])
    print(f"🎙️ Voiceover voice: {voice}")
    clean = text.replace('"', "").replace("'", "").replace("@", " ").replace("||", " ")

    async def render():
        await edge_tts.Communicate(clean, voice, rate="-5%").save(output_audio_path)

    try:
        try:
            asyncio.run(render())
        except RuntimeError:  # an event loop is already running (e.g. notebooks)
            import nest_asyncio
            nest_asyncio.apply()
            asyncio.get_event_loop().run_until_complete(render())
        return os.path.exists(output_audio_path)
    except Exception as e:
        print(f"❌ Voiceover generation failed: {e}")
        return False


# ----------------------------------------------------------------------------
# SUBTITLES
# ----------------------------------------------------------------------------
@lru_cache(maxsize=4096)
def _text_size(text):
    (w, h), _ = cv2.getTextSize(text, SUB_FONT, SUB_SCALE, SUB_THICK)
    return w, h


def _clean_for_hershey(text):
    """OpenCV's built-in fonts are ASCII only - drop everything else."""
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[()\[\]\"<>]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def get_wrapped_lines(text, max_w=SUBTITLE_MAX_W):
    """Break the script into lines that fit - measured exactly as they are drawn (upper-case)."""
    lines, current = [], ""
    for word in text.upper().split(" "):
        if not word:
            continue
        candidate = f"{current} {word}" if current else word
        if _text_size(candidate)[0] < max_w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_word_by_word_subtitle(frame, line_text, frame_in_line, total_frames_for_line):
    """Reveal words one by one: first word neon-highlighted, the rest white, black outline."""
    if not line_text:
        return
    words = line_text.split()
    n = len(words)
    shown = min(int(frame_in_line / max(1, total_frames_for_line) * n) + 1, n)

    first_full = words[0]
    rest_full = " ".join(words[1:])
    w1, h1 = _text_size(first_full)
    w2, h2 = _text_size(rest_full) if rest_full else (0, 0)
    space_w = _text_size(" ")[0] if rest_full else 0

    tx = W // 2 - (w1 + space_w + w2) // 2
    ty = SUBTITLE_Y + max(h1, h2) // 2

    def put(text, x, color):
        cv2.putText(frame, text, (x, ty), SUB_FONT, SUB_SCALE, (0, 0, 0), 9, cv2.LINE_AA)
        cv2.putText(frame, text, (x, ty), SUB_FONT, SUB_SCALE, color, SUB_THICK, cv2.LINE_AA)

    put(first_full, tx, (0, 230, 255))
    if shown > 1:
        put(" ".join(words[1:shown]), tx + w1 + space_w, (255, 255, 255))


# ----------------------------------------------------------------------------
# DRAWING HELPERS
# ----------------------------------------------------------------------------
def draw_progress_bar(frame, current_frame, total_frames):
    """Thin progress line at the top; only touches its own strip."""
    bar_h = 12
    roi = frame[0:bar_h, :]
    track = np.full_like(roi, (35, 30, 32))
    cv2.addWeighted(track, 0.5, roi, 0.5, 0, roi)
    fill = int(W * min(1.0, current_frame / max(1, total_frames)))
    if fill > 0:
        roi[:, :fill] = (0, 230, 255)


def make_background(img, brightness):
    """Blurred, darkened full-frame backdrop. Blur at 1/4 size, then scale up (much faster)."""
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 14)
    big = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR)
    return (big.astype(np.float32) * brightness).astype(np.uint8)


class Scene:
    """One product image with its pre-computed backdrop."""

    def __init__(self, img):
        self.img = img
        self.bg = make_background(img, 0.65)

    def render(self, frame_i, total_frames):
        h, w = self.img.shape[:2]
        zoom = 1.0 + 0.05 * (frame_i / max(1, total_frames))  # gentle Ken Burns zoom
        ratio = min(W / w, H / h)
        tw, th = max(1, int(w * ratio * zoom)), max(1, int(h * ratio * zoom))
        fg = cv2.resize(self.img, (tw, th), interpolation=cv2.INTER_LINEAR)
        x1, y1 = max(0, (tw - W) // 2), max(0, (th - H) // 2)
        fg = fg[y1:y1 + H, x1:x1 + W]
        fh, fw = fg.shape[:2]
        canvas = self.bg.copy()
        oy, ox = (H - fh) // 2, (W - fw) // 2
        canvas[oy:oy + fh, ox:ox + fw] = fg
        return canvas


def overlay_image(canvas, overlay, x, y):
    """Alpha-blend `overlay` onto `canvas` at (x, y), clipped to the frame."""
    if overlay is None:
        return
    if overlay.ndim == 2:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)
    oh, ow = overlay.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + ow), min(H, y + oh)
    if x0 >= x1 or y0 >= y1:
        return
    part = overlay[y0 - y:y1 - y, x0 - x:x1 - x]
    roi = canvas[y0:y1, x0:x1]
    if part.shape[2] == 4:
        alpha = part[:, :, 3:4].astype(np.float32) / 255.0
        roi[:] = (alpha * part[:, :, :3] + (1.0 - alpha) * roi).astype(np.uint8)
    else:
        roi[:] = part


def _load_logo(name, width):
    path = os.path.join(SCRIPT_DIR, name)
    if not os.path.exists(path):
        return None
    logo = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if logo is None:
        return None
    h, w = logo.shape[:2]
    return cv2.resize(logo, (width, max(1, int(h * width / w))))


def build_outro_canvas(last_img, logo, link_logo):
    canvas = make_background(last_img, 0.35)
    lh, lw = logo.shape[:2]
    lx, ly = (W - lw) // 2, (H - lh) // 2
    overlay_image(canvas, logo, lx, ly)

    text = "Follow & Subscribe for More Deals!"
    (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 3)
    cv2.putText(canvas, text, ((W - tw) // 2, ly + lh + 100), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 3, cv2.LINE_AA)

    if link_logo is not None:
        overlay_image(canvas, link_logo, (W - link_logo.shape[1]) // 2, 150)
    return canvas


# ----------------------------------------------------------------------------
# MAIN ENTRY POINT (signature unchanged)
# ----------------------------------------------------------------------------
def create_pro_video(image_paths, product_name, output_path, voice_text=None):
    print(f"🎬 [Editor] Rendering video for: {product_name[:25]}...")

    thumbnail_img, product_imgs = None, []
    for idx, path in enumerate(image_paths):
        if not os.path.exists(path):
            continue
        img = cv2.imread(path)
        if img is None:
            continue
        if idx == 0 and os.path.basename(path).startswith("tn_"):
            thumbnail_img = img
        else:
            product_imgs.append(img)
    if not product_imgs and thumbnail_img is not None:
        product_imgs.append(thumbnail_img)
        thumbnail_img = None
    if not product_imgs:
        print("❌ [Editor] No valid images to compile.")
        return False

    # optional voiceover decides the length
    tts_path, has_voice, total_seconds = output_path.replace(".mp4", "_voiceover.mp3"), False, TOTAL_SECONDS
    if ENABLE_VOICEOVER and voice_text and generate_voiceover(voice_text, tts_path):
        try:
            probe = AudioFileClip(tts_path)
            total_seconds = min(int(probe.duration) + OUTRO_SECONDS + 1, 58)
            probe.close()
            has_voice = True
        except Exception as e:
            print(f"⚠️ Could not read voiceover length: {e}")

    logo = _load_logo("SCIO_Logo.png", 500)
    link_logo = _load_logo("LinkInBio_Logo.png", 700)
    has_outro = logo is not None

    total_frames = total_seconds * FPS
    outro_frames = OUTRO_SECONDS * FPS if has_outro else 0
    thumb_frames = int(THUMB_SECONDS * FPS) if thumbnail_img is not None else 0
    product_frames = total_frames - outro_frames - thumb_frames
    if product_frames <= 0:
        product_frames, outro_frames, thumb_frames = total_frames, 0, 0
        has_outro = False

    # frames per image; the last image absorbs the remainder (no zoom reset)
    n = len(product_imgs)
    base = product_frames // n
    img_frames = [base] * n
    img_frames[-1] += product_frames - base * n

    script = _clean_for_hershey(voice_text or "")
    subtitle_lines = get_wrapped_lines(script) if script else []
    if not subtitle_lines:
        subtitle_lines = ["CHECK OUT THIS AMAZING DEAL!", "LINK IS AVAILABLE BELOW."]
    frames_per_line = max(1, product_frames // len(subtitle_lines))

    scenes = [Scene(img) for img in product_imgs]
    thumb_scene = Scene(thumbnail_img) if thumbnail_img is not None else None
    outro_canvas = build_outro_canvas(product_imgs[-1], logo, link_logo) if has_outro else None

    temp_video = output_path.replace(".mp4", "_temp_render.avi")
    writer = cv2.VideoWriter(temp_video, cv2.VideoWriter_fourcc(*"XVID"), FPS, (W, H))
    if not writer.isOpened():
        print("❌ [Editor] OpenCV could not open the video writer (XVID codec missing?).")
        return False

    frame_no = 0
    video_clip = final_clip = music_clip = voice_clip = base_music = None
    try:
        # A) thumbnail hook (static)
        if thumb_scene is not None:
            hook = thumb_scene.render(0, thumb_frames)
            draw_word_by_word_subtitle(hook, subtitle_lines[0], 0, thumb_frames)
            for _ in range(thumb_frames):
                f = hook.copy()
                draw_progress_bar(f, frame_no, total_frames)
                writer.write(f)
                frame_no += 1

        # B) product slideshow with zoom, cross-fades and rolling subtitles
        start = 0
        for img_idx, scene in enumerate(scenes):
            frames_here = img_frames[img_idx]
            trans = min(TRANSITION_FRAMES, frames_here)
            for i in range(frames_here):
                canvas = scene.render(i, frames_here)

                if i >= frames_here - trans:  # cross-fade into the next scene / outro
                    p = (i - (frames_here - trans)) / trans
                    if img_idx < n - 1:
                        nxt = scenes[img_idx + 1].render(i - (frames_here - trans), img_frames[img_idx + 1])
                        canvas = cv2.addWeighted(canvas, 1.0 - p, nxt, p, 0)
                    elif outro_canvas is not None:
                        canvas = cv2.addWeighted(canvas, 1.0 - p, outro_canvas, p, 0)

                g = start + i  # global index inside the product section
                line_idx = min(g // frames_per_line, len(subtitle_lines) - 1)
                draw_word_by_word_subtitle(canvas, subtitle_lines[line_idx], g % frames_per_line, frames_per_line)
                draw_progress_bar(canvas, frame_no, total_frames)
                writer.write(canvas)
                frame_no += 1
            start += frames_here

        # C) brand outro
        if outro_canvas is not None:
            for _ in range(outro_frames):
                f = outro_canvas.copy()
                draw_progress_bar(f, frame_no, total_frames)
                writer.write(f)
                frame_no += 1
    finally:
        writer.release()

    # D) final encode + audio mix
    try:
        video_clip = VideoFileClip(temp_video)
        layers = []

        if has_voice:
            voice_clip = AudioFileClip(tts_path)
            layers.append(voice_clip)

        music_dir = os.path.join(SCRIPT_DIR, "Background_Music")
        tracks = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.lower().endswith(".mp3")] \
            if os.path.isdir(music_dir) else []
        if tracks:
            track = random.choice(tracks)
            print(f"🎵 Background track: {os.path.basename(track)}")
            base_music = AudioFileClip(track)
            music_clip = _subclip(base_music, 0, min(video_clip.duration, base_music.duration))
            music_clip = _scale_volume(music_clip, 0.15 if has_voice else MUSIC_VOLUME)
            layers.append(music_clip)
        else:
            print("ℹ️ No Background_Music/*.mp3 found - video will be silent.")

        final_clip = _with_audio(video_clip, CompositeAudioClip(layers)) if layers else video_clip
        final_clip.write_videofile(
            output_path, fps=FPS, codec="libx264", audio_codec="aac",
            bitrate="5000k", audio_bitrate="128k",
            ffmpeg_params=["-movflags", "+faststart", "-pix_fmt", "yuv420p"],
            logger=None, write_logfile=False,
        )
        print(f"🎉 Video ready: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Video compilation failed: {e}")
        return False
    finally:
        for clip in (final_clip, video_clip, voice_clip, music_clip, base_music):
            try:
                if clip is not None:
                    clip.close()
            except Exception:
                pass
        for leftover in (temp_video, tts_path):
            try:
                if os.path.exists(leftover):
                    os.remove(leftover)
            except OSError:
                pass
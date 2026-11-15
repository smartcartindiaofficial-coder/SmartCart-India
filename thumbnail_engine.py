"""
thumbnail_engine.py - builds the 1080x1920 "poster" thumbnail (hook frame + cover).

Changes vs the old version
  * rembg (background removal) is imported lazily and its model is loaded ONCE
    per run. If rembg or its ~170 MB model download is unavailable, the poster is
    still built from the original photo instead of failing (main.py used to lose
    the whole thumbnail). Set REMBG_MODEL=u2netp for a much smaller/faster model.
  * Fonts: downloaded at most once per run, only the one needed; if the download
    fails it falls back to common system fonts (DejaVu/Liberation/Arial) and only
    then to Pillow's default - the old fallback was `arial.ttf`, which does not
    exist on Linux/GitHub Actions, giving tiny unreadable text. Best fix: commit
    the three .ttf files into a `fonts/` folder next to this file.
  * The offer badge is now truly centred (the old code used `text_w // 4` and a
    float divisor hack) and its font size is measured on the real 2-line text.
  * Vignette blur runs at quarter size (radius-260 blur on a full frame was the
    slowest step); text gradient is built with numpy instead of 1920 line draws.
  * Colour theme uses numpy (Image.getdata is deprecated in newer Pillow).
  * offer_percentage=None no longer crashes.
The public function generate_thumbnail_multi(...) is unchanged.
"""
import os
import io
import math
import random
from functools import lru_cache

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, "Config.env"))

CANVAS_W, CANVAS_H = 1080, 1920

# ─── RADIAL BACKGROUND SHAPE GENERATORS ───

def draw_sunburst_rays(canvas_size, num_rays=28, ray_opacity=35):
    """Generates a geometric transparent sunburst ray pattern radiating from the center."""
    width, height = canvas_size
    center_x, center_y = width // 2, height // 2
    
    ray_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ray_draw = ImageDraw.Draw(ray_layer)
    
    max_radius = int(math.hypot(width, height))
    angle_step = 360 / num_rays
    
    for i in range(0, num_rays, 2):
        start_angle = math.radians(i * angle_step)
        end_angle = math.radians((i + 1) * angle_step)
        
        p1 = (center_x, center_y)
        p2 = (center_x + max_radius * math.cos(start_angle), center_y + max_radius * math.sin(start_angle))
        p3 = (center_x + max_radius * math.cos(end_angle), center_y + max_radius * math.sin(end_angle))
        
        ray_draw.polygon([p1, p2, p3], fill=(255, 255, 255, ray_opacity))
        
    return ray_layer

def draw_radial_dot_burst(canvas_size, num_spokes=28, dots_per_spoke=14, base_opacity=35):
    """Generates a dot matrix pattern that radiates outward from the center along ray paths."""
    width, height = canvas_size
    center_x, center_y = width // 2, height // 2
    
    dot_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dot_draw = ImageDraw.Draw(dot_layer)
    
    max_radius = max(width, height) // 1.2
    angle_step = 360 / num_spokes
    
    for i in range(num_spokes):
        angle = math.radians(i * angle_step)
        
        for j in range(1, dots_per_spoke + 1):
            t = j / dots_per_spoke
            radius = max_radius * (t ** 1.3)
            
            if radius < 80:
                continue
                
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            dot_size = int(3 + (8 * t))
            opacity = int(base_opacity * (1.2 - t * 0.4))
            
            dot_draw.ellipse(
                [x - dot_size, y - dot_size, x + dot_size, y + dot_size],
                fill=(255, 255, 255, opacity)
            )
            
    return dot_layer

def draw_alternating_waves(canvas_size, num_rings=9, base_opacity=25):
    """Generates expanding concentric waves with highlighted alternating heavy/thick bands."""
    width, height = canvas_size
    center_x, center_y = width // 2, height // 2
    
    wave_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    wave_draw = ImageDraw.Draw(wave_layer)
    
    max_radius = max(width, height) // 1.3
    step = max_radius // num_rings
    
    for i in range(1, num_rings + 1):
        radius = i * step
        
        if i % 2 == 0:
            current_width = 8
            current_opacity = int(base_opacity * 1.8)
        else:
            current_width = 3
            current_opacity = base_opacity
            
        wave_draw.ellipse(
            [center_x - radius, center_y - radius, center_x + radius, center_y + radius],
            outline=(255, 255, 255, current_opacity),
            width=current_width
        )
        
    return wave_layer

def draw_alternating_squares(canvas_size, num_shapes=8, base_opacity=25):
    """Generates expanding nested squares with highlighted alternating heavy borders."""
    width, height = canvas_size
    center_x, center_y = width // 2, height // 2
    
    shape_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shape_draw = ImageDraw.Draw(shape_layer)
    
    max_radius = max(width, height) // 1.4
    step = max_radius // num_shapes
    
    for i in range(1, num_shapes + 1):
        radius = i * step
        x0, y0 = center_x - radius, center_y - radius
        x1, y1 = center_x + radius, center_y + radius
        
        current_width = 8 if i % 2 == 0 else 3
        current_opacity = int(base_opacity * 1.8) if i % 2 == 0 else base_opacity
        
        shape_draw.rectangle(
            [x0, y0, x1, y1],
            outline=(255, 255, 255, current_opacity),
            width=current_width
        )
        
    return shape_layer

def draw_alternating_ovals(canvas_size, num_shapes=9, base_opacity=25):
    """Generates expanding concentric ovals stretched proportionally to canvas limits."""
    width, height = canvas_size
    center_x, center_y = width // 2, height // 2
    
    shape_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shape_draw = ImageDraw.Draw(shape_layer)
    
    step_w = (width // 1.2) // num_shapes
    step_h = (height // 1.2) // num_shapes
    
    for i in range(1, num_shapes + 1):
        rad_w, rad_h = i * step_w, i * step_h
        x0, y0 = center_x - rad_w, center_y - rad_h
        x1, y1 = center_x + rad_w, center_y + rad_h
        
        current_width = 8 if i % 2 == 0 else 3
        current_opacity = int(base_opacity * 1.8) if i % 2 == 0 else base_opacity
        
        shape_draw.ellipse(
            [x0, y0, x1, y1],
            outline=(255, 255, 255, current_opacity),
            width=current_width
        )
        
    return shape_layer

def draw_alternating_rhombuses(canvas_size, num_shapes=8, base_opacity=25):
    """Generates expanding nested diamond/rhombus frames with highlighted alternating thick lines."""
    width, height = canvas_size
    center_x, center_y = width // 2, height // 2
    
    shape_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    shape_draw = ImageDraw.Draw(shape_layer)
    
    max_radius = max(width, height) // 1.3
    step = max_radius // num_shapes
    
    for i in range(1, num_shapes + 1):
        radius = i * step
        
        top_vertex    = (center_x, center_y - radius)
        right_vertex  = (center_x + radius, center_y)
        bottom_vertex = (center_x, center_y + radius)
        left_vertex   = (center_x - radius, center_y)
        
        current_width = 8 if i % 2 == 0 else 3
        current_opacity = int(base_opacity * 1.8) if i % 2 == 0 else base_opacity
        
        shape_draw.polygon(
            [top_vertex, right_vertex, bottom_vertex, left_vertex],
            outline=(255, 255, 255, current_opacity),
            width=current_width
        )
        
    return shape_layer

# ─── CORE THEME ENGINE ───

def extract_dominant_theme_from_image(product_layer, product_name):
    """Extracts product colour profile, builds gradient palette, randomly assigns styles."""
    arr = np.asarray(product_layer.resize((50, 50)).convert("RGBA"))
    valid = arr[arr[:, :, 3] > 220][:, :3]
    if len(valid) == 0:
        avg_r, avg_g, avg_b = 20, 24, 30
    else:
        avg_r, avg_g, avg_b = (int(v) for v in valid.mean(axis=0))

    bg_base = (max(10, avg_r // 6), max(10, avg_g // 6), max(10, avg_b // 6), 255)
    bg_glow = (min(255, int(avg_r * 0.5)), min(255, int(avg_g * 0.5)), min(255, int(avg_b * 0.5)), 255)

    max_channel = max(bg_glow[0], bg_glow[1], bg_glow[2], 1)
    scale_factor = 230 / max_channel if max_channel < 180 else 1.2
    gradient_top = tuple(min(255, int(c * scale_factor + 10)) for c in bg_glow[:3]) + (255,)
    gradient_bottom = (255, 255, 255, 255)

    return {
        "bg_base": bg_base,
        "bg_glow": bg_glow,
        "gradient_top": gradient_top,
        "gradient_bottom": gradient_bottom,
        "font_style": random.choice(["IMPACT_BEBAS", "TECH_MONTSERRAT", "CREATIVE_POPPINS"]),
        "bg_style": random.choice(["rays", "radial_dots", "alternating_waves", "squares", "ovals", "rhombuses"]),
    }


# ─── FONTS ───

FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")
FONT_URLS = {
    "Montserrat-Black.ttf": "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Black.ttf",
    "Poppins-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf",
    "BebasNeue-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/bebasneue/BebasNeue-Regular.ttf",
}
FONT_STYLE_FILES = {
    "IMPACT_BEBAS": "BebasNeue-Regular.ttf",
    "TECH_MONTSERRAT": "Montserrat-Black.ttf",
    "CREATIVE_POPPINS": "Poppins-Bold.ttf",
}
SYSTEM_FONT_FALLBACKS = [
    "arialbd.ttf", "arial.ttf",
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
_download_attempted = set()


def download_and_get_fonts(font_style):
    """Path of the font for this style, downloading it once if it is missing."""
    os.makedirs(FONT_DIR, exist_ok=True)
    filename = FONT_STYLE_FILES.get(font_style, FONT_STYLE_FILES["CREATIVE_POPPINS"])
    path = os.path.join(FONT_DIR, filename)
    if os.path.exists(path) and os.path.getsize(path) == 0:
        os.remove(path)
    if not os.path.exists(path) and filename not in _download_attempted:
        _download_attempted.add(filename)
        try:
            r = requests.get(FONT_URLS[filename], timeout=10)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(path, "wb") as f:
                    f.write(r.content)
        except Exception as e:
            print(f"⚠️ Font download failed ({filename}): {e}. Falling back to system fonts.")
    return path


@lru_cache(maxsize=64)
def safe_load_font(font_path, size):
    if font_path and os.path.exists(font_path) and os.path.getsize(font_path) > 0:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass
    for fallback in SYSTEM_FONT_FALLBACKS:
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1: scalable default font
    except TypeError:
        return ImageFont.load_default()


def wrap_text_to_lines(text, font, max_width):
    lines, current = [], []
    for word in text.split(" "):
        test = " ".join(current + [word])
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _vertical_gradient(size, y0, y1, top, bottom):
    """RGBA image whose colour blends top->bottom between rows y0..y1 (numpy, no per-row loop)."""
    w, h = size
    f = np.clip((np.arange(h, dtype=np.float32) - y0) / max(1, (y1 - y0)), 0.0, 1.0)[:, None]
    col = np.array(top, dtype=np.float32) + (np.array(bottom, dtype=np.float32) - np.array(top, dtype=np.float32)) * f
    return Image.fromarray(np.repeat(col[:, None, :], w, axis=1).astype(np.uint8), "RGBA")


def draw_gradient_text_block_with_3d_shadow(bg_canvas, text, position, font_path, max_width, top_color, bottom_color,
                                            shadow_color=(0, 0, 0, 255), offset=(12, 14)):
    """Centre-aligned title with a deep 3D shadow and a top->bottom colour gradient."""
    size = 125
    while True:
        font = safe_load_font(font_path, size)
        lines = wrap_text_to_lines(text, font, max_width)
        bbox_sample = font.getbbox("XYgq")
        line_height = (bbox_sample[3] - bbox_sample[1]) + 15
        if size * len(lines) <= 360 or size <= 50:
            break
        size -= 4

    draw = ImageDraw.Draw(bg_canvas)
    start_x, start_y = position
    off_x, off_y = offset
    mask = Image.new("L", bg_canvas.size, 0)
    mask_draw = ImageDraw.Draw(mask)

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        lx = start_x + (max_width - (bbox[2] - bbox[0])) // 2
        ly = start_y + i * line_height
        draw.text((lx + off_x, ly + off_y), line, fill=shadow_color, font=font)  # 3D shadow
        mask_draw.text((lx, ly), line, fill=255, font=font)                      # text silhouette

    gradient = _vertical_gradient(bg_canvas.size, start_y, start_y + line_height * len(lines), top_color, bottom_color)
    layer = Image.new("RGBA", bg_canvas.size, (0, 0, 0, 0))
    layer.paste(gradient, (0, 0), mask=mask)
    bg_canvas.alpha_composite(layer)


# ─── BACKGROUND REMOVAL (optional, lazy) ───

_rembg_session = None
_rembg_failed = False


def _remove_background(data):
    """Returns PNG bytes with transparent background, or None if rembg is unavailable."""
    global _rembg_session, _rembg_failed
    if _rembg_failed:
        return None
    try:
        from rembg import remove, new_session
        if _rembg_session is None:
            _rembg_session = new_session(os.getenv("REMBG_MODEL", "u2net"))
        return remove(data, session=_rembg_session)
    except Exception as e:
        _rembg_failed = True
        print(f"⚠️ Background removal unavailable ({type(e).__name__}: {e}).")
        return None


def _load_product_layer(path):
    with open(path, "rb") as f:
        data = f.read()
    cut = _remove_background(data)
    if cut:
        layer = Image.open(io.BytesIO(cut)).convert("RGBA")
        bbox = layer.getbbox()
        if bbox:
            return layer.crop(bbox)
    print("ℹ️ Using the original photo (no cut-out) for the poster.")
    return Image.open(io.BytesIO(data)).convert("RGBA")


# ─── OFFER BADGE ───

def draw_foreground_offer_badge(bg_canvas, offer_percentage, anchor_corner="bottom-right"):
    """Red starburst with centred '68% / OFF' text, drawn last so it is always on top."""
    canvas_w, canvas_h = bg_canvas.size
    draw = ImageDraw.Draw(bg_canvas)
    inner_r, outer_r, points = 210, 250, 24
    margin = 160  # keeps the whole text inside the frame (spikes may still bleed off the corner)
    cx = canvas_w - margin if "right" in anchor_corner else margin
    cy = canvas_h - margin if "bottom" in anchor_corner else margin

    star, step = [], math.pi / points
    for i in range(points * 2):
        rad = outer_r if i % 2 == 0 else inner_r
        angle = i * step - math.pi / 2
        star.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
    draw.polygon(star, fill=(192, 0, 0, 255))

    text = f"{int(offer_percentage)}%\nOFF"
    font_path = download_and_get_fonts("IMPACT_BEBAS")
    size = 180
    while True:
        font = safe_load_font(font_path, size)
        l, t, r, b = draw.multiline_textbbox((0, 0), text, font=font, align="center", spacing=0)
        if ((r - l) <= 330 and (b - t) <= 330) or size <= 70:
            break
        size -= 8
    draw.multiline_text((cx, cy), text, fill=(255, 255, 255, 255), font=font, anchor="mm", align="center", spacing=0)


# ─── MAIN ENTRY POINT (signature unchanged) ───

def _build_vignette():
    """Soft studio-light ellipse. Blurred at 1/4 size then scaled up (same look, far faster)."""
    small = Image.new("L", (CANVAS_W // 4, CANVAS_H // 4), 0)
    ImageDraw.Draw(small).ellipse([-250 // 4, 150 // 4, 1330 // 4, 1750 // 4], fill=130)
    small = small.filter(ImageFilter.GaussianBlur(65))
    return small.resize((CANVAS_W, CANVAS_H), Image.Resampling.BILINEAR)


def generate_thumbnail_multi(asin, product_name, specifications, image_paths_list, offer_percentage):
    output_path = os.path.join(SCRIPT_DIR, f"tn_{asin}.jpg")
    offer_percentage = int(offer_percentage or 0)

    valid_images = [p for p in image_paths_list if os.path.exists(p)]
    if not valid_images:
        print("❌ Thumbnail: no valid source images found.")
        return None
    print(f"🚀 [Studio Engine] ASIN {asin} ({offer_percentage}% OFF)" if offer_percentage > 0
          else f"🚀 [Studio Engine] ASIN {asin} (no offer)")

    try:
        product_layer = _load_product_layer(valid_images[0])
        theme = extract_dominant_theme_from_image(product_layer, product_name)
        title_font_path = download_and_get_fonts(theme["font_style"])

        bg = Image.new("RGBA", (CANVAS_W, CANVAS_H), theme["bg_base"])
        bg.paste(Image.new("RGBA", (CANVAS_W, CANVAS_H), theme["bg_glow"]), (0, 0), _build_vignette())

        print(f"🪄 Style variant: '{theme['bg_style']}'")
        style = theme["bg_style"]
        if style == "radial_dots":
            overlay = draw_radial_dot_burst(bg.size, num_spokes=40, dots_per_spoke=20, base_opacity=35)
        elif style == "alternating_waves":
            overlay = draw_alternating_waves(bg.size, num_rings=24, base_opacity=25)
        elif style == "squares":
            overlay = draw_alternating_squares(bg.size, num_shapes=24, base_opacity=25)
        elif style == "ovals":
            overlay = draw_alternating_ovals(bg.size, num_shapes=24, base_opacity=25)
        elif style == "rhombuses":
            overlay = draw_alternating_rhombuses(bg.size, num_shapes=24, base_opacity=25)
        else:
            overlay = draw_sunburst_rays(bg.size, num_rays=28, ray_opacity=35)
        bg.alpha_composite(overlay)

        # typography first (bottom layer)
        title = product_name.strip()
        if theme["font_style"] != "IMPACT_BEBAS" and title.isupper():
            title = title.title()
        draw_gradient_text_block_with_3d_shadow(
            bg, title, (80, 120), title_font_path, CANVAS_W - 160,
            theme["gradient_top"], theme["gradient_bottom"], offset=(11, 13),
        )

        # product on top, centred at y=1100
        pw, ph = product_layer.size
        scale = min((CANVAS_W - 60) / pw, 1100 / ph)
        tw, th = max(1, int(pw * scale * 0.92)), max(1, int(ph * scale * 0.92))
        product = product_layer.resize((tw, th), Image.Resampling.LANCZOS)
        px, py = CANVAS_W // 2 - tw // 2, 1100 - th // 2

        blur = 55
        mask = product.getchannel("A").resize((tw + blur * 2, th + blur * 2), resample=Image.Resampling.BOX)
        shadow = Image.composite(Image.new("RGBA", mask.size, (2, 2, 4, 235)), Image.new("RGBA", mask.size), mask)
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur // 2))
        bg.alpha_composite(shadow, (px - blur, py - blur))
        bg.alpha_composite(product, (px, py))

        if offer_percentage > 0:
            draw_foreground_offer_badge(bg, offer_percentage, anchor_corner="bottom-right")

        bg.convert("RGB").save(output_path, "JPEG", quality=95)
        print(f"🎉 Thumbnail saved: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Thumbnail engine failed: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    test = os.path.join(SCRIPT_DIR, "test.jpg")  # must be a clean ORIGINAL product photo
    if os.path.exists(test):
        generate_thumbnail_multi("B0FVX789CR", "Zoom In, Not Out", [], [test], 68)
    else:
        print("Put a product photo named test.jpg next to this file to try the engine.")
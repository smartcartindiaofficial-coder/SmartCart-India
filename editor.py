import os
import random
import cv2
import numpy as np
import asyncio
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip

def generate_voiceover(text, output_audio_path):
    voice_pool = [
        "en-IN-PrabhatNeural",  # Clear Indian English (Male)
        "en-IN-NeerjaNeural",   # Smooth Indian English (Female)
        "en-US-GuyNeural",      # Natural US English (Male)
        "en-US-AriaNeural",     # Natural US English (Female)
        "en-GB-RyanNeural",     # Professional UK English (Male)
        "en-GB-SoniaNeural"     # Professional UK English (Female)
    ]

    selected_voice = random.choice(voice_pool)
    print(f"🎙️ [Voiceover Engine] Selected voice asset: {selected_voice}")

    async def amain():
        communicate = edge_tts.Communicate(text, selected_voice, rate="+0%")
        await communicate.save(output_audio_path)
        
    try:
        asyncio.run(amain())
        print(f"🎙️ Voiceover successfully generated at: {output_audio_path}")
        return True
    except Exception as e:
        print(f"❌ Voiceover generation failed: {e}")
        return False

def get_wrapped_lines(text, max_w, font, font_scale, thickness):
    """
    Helper function to wrap text and return a list of lines.
    """
    words = text.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + " " + word if current_line else word
        (text_w, _), _ = cv2.getTextSize(test_line, font, font_scale, thickness)
        
        if text_w < max_w:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def draw_engagement_overlay(frame, text=">>> LINK IN BIO / COMMENTS <<<"):
    """
    Draws an ultra-premium, studio-grade call-to-action banner 
    featuring an indigo matte field, neon cyan border accents, and layered typography.
    """
    h, w, _ = frame.shape
    
    # Elegant, slim proportions (perfectly positioned above platform navigation UI overlays)
    box_y1 = int(h * 0.83)
    box_y2 = int(h * 0.885)
    margin_x = 80
    
    # Create a staging overlay matrix for professional anti-aliased alpha blending
    overlay = frame.copy()
    
    # ─── COLOR PALETTE DESIGN (BGR FORMAT) ───
    # Deep Midnight Indigo / Royal Dark Velvet field
    bg_indigo = (45, 20, 28)     
    # Vibrant Neon Cyan / Electric Aqua for the accent edge border
    border_cyan = (240, 240, 30) 
    
    # Draw the main solid field box
    cv2.rectangle(overlay, (margin_x, box_y1), (w - margin_x, box_y2), bg_indigo, -1)
    
    # Smooth blend the box into the frame with 95% opacity to allow a subtle hint of background texture
    cv2.addWeighted(overlay, 0.95, frame, 0.05, 0, frame)
    
    # Paint the high-contrast Neon Cyan modern accent frame line
    cv2.rectangle(frame, (margin_x, box_y1), (w - margin_x, box_y2), border_cyan, 3, cv2.LINE_AA)

    # ─── LAYERED TYPOGRAPHY STACK ───
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.4  # Slightly balanced for elegant tracking space margins
    thickness = 4
    
    # Precise positioning math
    (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    text_x = margin_x + ((w - (margin_x * 2)) - text_w) // 2
    text_y = box_y1 + ((box_y2 - box_y1) + text_h) // 2
    
    # Layer 1: Professional Deep Soft Shadow (Soft Offset Drop)
    cv2.putText(frame, text, (text_x + 4, text_y + 4), font, font_scale, (10, 10, 10), thickness + 2, cv2.LINE_AA)
    
    # Layer 2: Core Text Structural Sharpener
    cv2.putText(frame, text, (text_x, text_y), font, font_scale, (25, 20, 20), thickness + 1, cv2.LINE_AA)
    
    # Layer 3: Crisp, Pure White Alabaster Text Face
    cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    
    return frame


def create_pro_video(image_paths, product_name, output_path, voice_text=None):
    """
    Compiles product images into a pristine vertical Short with cinematic background blurs,
    a progressive camera zoom effect, a high-conversion voiceover asset layer,
    and a professional animated brand logo outro screen.
    """
    print(f"🎬 [Editor] Launching Premium Render Pipeline for: {product_name[:20]}...")
    
    # 1. READ ORIGINAL IMAGES
    valid_images = []
    for path in image_paths:
        if os.path.exists(path):
            img = cv2.imread(path)
            if img is not None:
                valid_images.append(img)

    if not valid_images:
        print("❌ [Editor Error] No valid product images found to compile.")
        return False

    # 🎙️ VOICE GENERATION & DURATION CALCULATION FIRST
    temp_tts_path = output_path.replace(".mp4", "_voiceover.mp3")
    has_voice = False
    total_duration = 15  # Fallback duration if voiceover generation fails

    if voice_text and generate_voiceover(voice_text, temp_tts_path):
        try:
            from moviepy.audio.io.AudioFileClip import AudioFileClip
            temp_audio = AudioFileClip(temp_tts_path)
            total_duration = min(int(temp_audio.duration) + 1, 58)
            temp_audio.close()
            has_voice = True
            print(f"⏱️ [Editor] Video duration dynamically set to match voiceover: {total_duration} seconds.")
        except Exception as audio_prep_err:
            print(f"⚠️ Could not parse audio track duration dimensions: {audio_prep_err}")

    # --- LOGIC FOR LOGO OUTRO ---
    fps = 24
    outro_duration = 5  # Add a clean 3-second branded screen at the end
    logo_filename = "SCIO_Logo.png"
    logo_path = os.path.join(os.getcwd(), logo_filename)
    logo_img = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED) if os.path.exists(logo_path) else None
    
    # Calculate frames split between product content and your logo outro
    total_frames = total_duration * fps
    outro_frames = outro_duration * fps
    product_frames = total_frames - outro_frames
    
    if product_frames <= 0:  # Fail-safe protection for ultra-short clips
        product_frames = total_frames
        outro_frames = 0

    frames_per_image = product_frames // len(valid_images)
    # -----------------------------

    # DESIGN TOP HEADER RULES & VALUES
    header_font = cv2.FONT_HERSHEY_SIMPLEX
    header_scale = 1.3
    header_thickness = 4
    header_padding = 40
    line_spacing = 20
    max_text_width = 1080 - (header_padding * 2)

    wrapped_lines = get_wrapped_lines(product_name, max_text_width, header_font, header_scale, header_thickness)
    if len(wrapped_lines) > 3:
        wrapped_lines = wrapped_lines[:3]
        wrapped_lines[-1] += "..."

    sample_text = "Test"
    (_, text_height), baseline = cv2.getTextSize(sample_text, header_font, header_scale, header_thickness)
    line_total_height = text_height + baseline + line_spacing
    banner_height = (len(wrapped_lines) * line_total_height) + (header_padding * 2)

    temp_video_path = output_path.replace(".mp4", "_temp_render.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (1080, 1920))

    # 2. RENDER STAGE 1: PRODUCT SLIDESHOW FRAME GENERATION LOOP
    current_image_idx = 0
    frame_in_current_image = 0

    for f_idx in range(product_frames):
        orig_img = valid_images[current_image_idx].copy()
        orig_h, orig_w, _ = orig_img.shape

        bg_img = cv2.resize(orig_img, (1080, 1920))
        blurred_bg = cv2.GaussianBlur(bg_img, (151, 151), 0)
        black_tint = np.zeros_like(blurred_bg)
        blurred_bg = cv2.addWeighted(blurred_bg, 0.60, black_tint, 0.40, 0)

        progress = frame_in_current_image / frames_per_image
        zoom_factor = 1.0 + (progress * 0.08) 

        scale_ratio = 1080 / orig_w
        if (orig_h * scale_ratio) > 1920:
            scale_ratio = 1920 / orig_h

        target_w = int(orig_w * scale_ratio * zoom_factor)
        target_h = int(orig_h * scale_ratio * zoom_factor)
        fg_resized = cv2.resize(orig_img, (target_w, target_h))

        crop_x1 = max(0, (target_w - 1080) // 2)
        crop_y1 = max(0, (target_h - 1920) // 2)
        fg_cropped = fg_resized[crop_y1:crop_y1+1920, crop_x1:crop_x1+1080]

        fg_h, fg_w, _ = fg_cropped.shape
        start_y = (1080 - fg_w) // 2
        start_x = (1920 - fg_h) // 2
        blurred_bg[start_x:start_x+fg_h, start_y:start_y+fg_w] = fg_cropped

        cv2.rectangle(blurred_bg, (0, 0), (1080, banner_height), (15, 15, 15), -1) 
        cv2.rectangle(blurred_bg, (0, banner_height), (1080, banner_height + 5), (0, 165, 255), -1) 

        for i, line in enumerate(wrapped_lines):
            y_pos = header_padding + text_height + (i * line_total_height)
            (w_l, _), _ = cv2.getTextSize(line, header_font, header_scale, header_thickness)
            x_pos = (1080 - w_l) // 2
            cv2.putText(blurred_bg, line, (x_pos, y_pos), header_font, header_scale, (255, 255, 255), header_thickness, cv2.LINE_AA)

        out.write(blurred_bg)

        frame_in_current_image += 1
        if frame_in_current_image >= frames_per_image and current_image_idx < len(valid_images) - 1:
            current_image_idx += 1
            frame_in_current_image = 0

    # 3. RENDER STAGE 2: HIGH-AESTHETIC BRAND LOGO OUTRO SCREEN LOOP
    if outro_frames > 0 and logo_img is not None:
        print("🎨 [Editor] Stitching premium brand logo outro sequence...")
        
        # Build a beautiful background for the logo using the last product image blur
        last_img = valid_images[-1].copy()
        bg_logo_canvas = cv2.resize(last_img, (1080, 1920))
        bg_logo_canvas = cv2.GaussianBlur(bg_logo_canvas, (151, 151), 0)
        dark_matte = np.zeros_like(bg_logo_canvas)
        bg_logo_canvas = cv2.addWeighted(bg_logo_canvas, 0.40, dark_matte, 0.60, 0) # Slightly darker for logo pop

        # Resize logo image to look clean and centered (Max width 500px)
        logo_h, logo_w = logo_img.shape[:2]
        logo_scale = 500 / logo_w
        new_logo_w = 500
        new_logo_h = int(logo_h * logo_scale)
        resized_logo = cv2.resize(logo_img, (new_logo_w, new_logo_h))

        # Center math calculation coordinates
        logo_x_start = (1080 - new_logo_w) // 2
        logo_y_start = (1920 - new_logo_h) // 2

        # Alpha Blend logic to support transparent PNG or standard solid logo overlays perfectly
        if resized_logo.shape[2] == 4:  # Transparent PNG handling
            alpha_channel = resized_logo[:, :, 3] / 255.0
            for c in range(3):
                bg_logo_canvas[logo_y_start:logo_y_start+new_logo_h, logo_x_start:logo_x_start+new_logo_w, c] = (
                    alpha_channel * resized_logo[:, :, c] +
                    (1.0 - alpha_channel) * bg_logo_canvas[logo_y_start:logo_y_start+new_logo_h, logo_x_start:logo_x_start+new_logo_w, c]
                )
        else:  # Standard RGB image handling
            bg_logo_canvas[logo_y_start:logo_y_start+new_logo_h, logo_x_start:logo_x_start+new_logo_w] = resized_logo

        # Add an ultra-premium "Thanks For Watching" or subscriber call text beneath the logo
        sub_text = "Follow & Subscribe for More Deals!"
        sub_font = cv2.FONT_HERSHEY_SIMPLEX
        sub_scale = 1.1
        sub_thick = 3
        (s_w, s_h), _ = cv2.getTextSize(sub_text, sub_font, sub_scale, sub_thick)
        sub_x = (1080 - s_w) // 2
        sub_y = logo_y_start + new_logo_h + 100
        
        cv2.putText(bg_logo_canvas, sub_text, (sub_x, sub_y), sub_font, sub_scale, (255, 255, 255), sub_thick, cv2.LINE_AA)

        # ─── ADDING LINK IN BIO IMAGE OVERLAY ASSET ───
        lib_logo_path = os.path.join(os.getcwd(), "LinkInBio_Logo.png")
        
        if os.path.exists(lib_logo_path):
            print("🖼️ [Editor] Found LinkInBio_Logo.png, overlaying asset onto outro...")
            # Load image using IMREAD_UNCHANGED to keep its alpha transparent channel if present
            lib_logo = cv2.imread(lib_logo_path, cv2.IMREAD_UNCHANGED)
            
            if lib_logo is not None:
                # 1. Scale image asset contextually (Force width to 350px, keep aspect ratio)
                target_lib_w = 700
                orig_lib_h, orig_lib_w = lib_logo.shape[:2]
                target_lib_h = int(orig_lib_h * (target_lib_w / orig_lib_w))
                resized_lib = cv2.resize(lib_logo, (target_lib_w, target_lib_h))
                
                # 2. Coordinate Math: Center horizontally, place near the bottom of canvas
                lib_x_start = (1080 - target_lib_w) // 2
                lib_y_start = 1920 - target_lib_h - 150  # 150px safety margin from very bottom
                
                # 3. Blending logic: Check if PNG contains alpha channel transparency (4 channels)
                if resized_lib.shape[2] == 4:
                    alpha_channel = resized_lib[:, :, 3] / 255.0
                    for c in range(3):
                        bg_logo_canvas[lib_y_start:lib_y_start+target_lib_h, lib_x_start:lib_x_start+target_lib_w, c] = (
                            alpha_channel * resized_lib[:, :, c] +
                            (1.0 - alpha_channel) * bg_logo_canvas[lib_y_start:lib_y_start+target_lib_h, lib_x_start:lib_x_start+target_lib_w, c]
                        )
                else:
                    # Fallback for standard 3-channel RGB images
                    bg_logo_canvas[lib_y_start:lib_y_start+target_lib_h, lib_x_start:lib_x_start+target_lib_w] = resized_lib
        else:
            print("⚠️ [Editor Warning] LinkInBio_Logo.png not found at root path. Skipping overlay.")

        # Write out the identical logo screen frame sequence for the final 3 seconds
        for _ in range(outro_frames):
            out.write(bg_logo_canvas)

    out.release()

    # 4. AUDIO TRACK CONTEXT PROCESSING
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        from moviepy.audio.AudioClip import CompositeAudioClip
        
        video_clip = VideoFileClip(temp_video_path)
        audio_layers = []

        if has_voice:
            voice_clip = AudioFileClip(temp_tts_path)
            audio_layers.append(voice_clip)

        bg_music_dir = os.path.join(os.getcwd(), "Background_Music")
        if os.path.exists(bg_music_dir):
            music_files = [os.path.join(bg_music_dir, f) for f in os.listdir(bg_music_dir) if f.lower().endswith('.mp3')]
            if music_files:
                selected_track = random.choice(music_files)
                print(f"🎵 Layering background audio track: {os.path.basename(selected_track)}")
                # Fill entire timeline (product duration + logo screen time) cleanly
                bg_music_clip = AudioFileClip(selected_track).subclip(0, total_duration).volumex(0.12)
                audio_layers.append(bg_music_clip)

        if audio_layers:
            final_audio_mix = CompositeAudioClip(audio_layers)
            final_output_clip = video_clip.set_audio(final_audio_mix)
        else:
            final_output_clip = video_clip

        print("⏳ Combining audio tracks and video frames into final .mp4...")
        final_output_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            logger=None,
            write_logfile=False
        )
        
        final_output_clip.close()
        video_clip.close()
        if has_voice: voice_clip.close()
        if os.path.exists(bg_music_dir) and music_files and 'bg_music_clip' in locals(): 
            bg_music_clip.close()
        
        if os.path.exists(temp_video_path): os.remove(temp_video_path)
        if os.path.exists(temp_tts_path): os.remove(temp_tts_path)
            
        print(f"🎉 SUCCESS: Video rendered completely with branding outro! Saved to: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Video compilation pipeline failure: {e}")
        if os.path.exists(temp_video_path):
            try: os.remove(temp_video_path)
            except: pass
        if os.path.exists(temp_tts_path):
            try: os.remove(temp_tts_path)
            except: pass
        return False
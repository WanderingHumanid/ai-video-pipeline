"""Generates YouTube thumbnails with enhanced aesthetics."""

import os
import sys
import random
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def generate_thumbnail(topic, media_assets=None, output_path=".tmp/thumbnail.jpg"):
    # Try to find a bold font
    font_paths = [
        "arialbd.ttf",  # Windows Arial Bold
        "seguiemj.ttf",
        "segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue-Bold.ttc",
        "arial.ttf"
    ]
    
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 90)
            break
        except OSError:
            continue
            
    if not font:
        font = ImageFont.load_default()

    bg_image = None
    if media_assets:
        image_assets = [a for a in media_assets if a["type"] == "image" and os.path.exists(a.get("local_path", ""))]
        video_assets = [a for a in media_assets if a["type"] == "video" and os.path.exists(a.get("local_path", ""))]
        
        # Prefer high-res images
        candidates = image_assets 
        if candidates:
            bg_path = random.choice(candidates)["local_path"]
            try:
                bg_image = Image.open(bg_path).convert("RGB")
                bg_image = bg_image.resize((1280, 720))
            except Exception:
                bg_image = None

    if not bg_image:
        # Create a moody gradient background
        bg_image = Image.new("RGB", (1280, 720), color=(20, 20, 20))
        draw = ImageDraw.Draw(bg_image)
        for y in range(720):
            r = int(10 + (y / 720) * 30)
            g = int(10 + (y / 720) * 20)
            b = int(30 + (y / 720) * 50)
            draw.line([(0, y), (1280, y)], fill=(r, g, b))

    # ENHANCEMENT: Darken and contrast the background
    enhancer = ImageEnhance.Brightness(bg_image)
    bg_image = enhancer.enhance(0.6)  # Darken by 40%
    
    enhancer = ImageEnhance.Contrast(bg_image)
    bg_image = enhancer.enhance(1.2)  # Boost contrast

    draw = ImageDraw.Draw(bg_image)
    
    # Text Processing
    words = topic.upper().split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        # Check width
        w = draw.textlength(" ".join(current_line), font=font)
        if w > 1000:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))

    # Draw text centered with shadow/outline
    total_height = len(lines) * 110
    start_y = (720 - total_height) // 2
    
    for i, line in enumerate(lines):
        w = draw.textlength(line, font=font)
        x = (1280 - w) // 2
        y = start_y + (i * 110)
        
        # Hard Drop Shadow
        draw.text((x+5, y+5), line, font=font, fill=(0, 0, 0))
        
        # Main Text
        draw.text((x, y), line, font=font, fill=(255, 230, 0)) # Yellow/Gold pop

    # Add a border
    draw.rectangle([(0,0), (1279,719)], outline=(255, 230, 0), width=10)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    bg_image.save(output_path, quality=95)
    print(f"✅ Thumbnail generated: {output_path}")
    return output_path


if __name__ == "__main__":
    import json
    topic = sys.argv[1] if len(sys.argv) > 1 else "AI Video Generation"
    
    media_assets = []
    if os.path.exists(".tmp/media_assets.json"):
        with open(".tmp/media_assets.json", "r", encoding="utf-8") as f:
            media_assets = json.load(f).get("media_assets", [])
            
    generate_thumbnail(topic, media_assets)

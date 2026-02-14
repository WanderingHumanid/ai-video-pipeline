import os
from moviepy import VideoFileClip, CompositeVideoClip, ColorClip

def _resize_to_1080p(clip):
    """Resize clip to 1920x1080, maintaining aspect ratio with black bars."""
    target_w, target_h = 1920, 1080

    # Get current dimensions
    w, h = clip.size
    print(f"Debug: Clip size {w}x{h}, duration {clip.duration}")

    # Calculate scale to fit within 1920x1080
    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    # Resize clip
    clip = clip.resized((new_w, new_h)) # MoviePy 2.x uses resized() or resize() ? I'll use resize() which typically returns copy or resized
    # Wait, MoviePy 2.0 might use "resized"? No, usually resize.
    # Let me check "resize" vs "resized".
    # In 2.0 it might be `resized`. But `resize` works in 1.x.
    # I used `resize` in compose_video.py: `clip = clip.resize((new_w, new_h))`
    # If that failed, it would have raised AttributeError.
    
    # Let's stick to what I had, but maybe try `resized` if strict. 
    # Actually, `clip.resize` is the method. 
    
    # Center on black background
    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0), duration=clip.duration)
    # bg = bg.with_fps(clip.fps if clip.fps else 30) 
    # clip.fps might be None if image... but this is video.
    
    final = CompositeVideoClip(
        [bg, clip.with_position("center")],
        size=(target_w, target_h)
    )
    final = final.with_duration(clip.duration)
    return final

if __name__ == "__main__":
    path = ".tmp/media/segment_0.mp4"
    if not os.path.exists(path):
        print(f"File not found: {path}")
        exit(1)

    print(f"Loading {path}...")
    from moviepy import concatenate_videoclips
    
    video = VideoFileClip(path)
    required_duration = 35.0 # Force looping (13s -> 35s)
    
    print(f"Processing video (duration {video.duration}s -> {required_duration}s)...")
    if video.duration >= required_duration:
        clip = video.subclipped(0, required_duration)
    else:
        num_loops = int(required_duration / video.duration) + 1
        clip = concatenate_videoclips([video] * num_loops)
        clip = clip.subclipped(0, required_duration)
        
    print("Resizing...")
    final = _resize_to_1080p(clip)
    
    output = ".tmp/test_output_processed.mp4"
    print(f"Writing to {output}...")
    final.write_videofile(
        output,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger="bar"
    )
    print("Done.")

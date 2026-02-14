"""
Video Composition Tool
Renders final .mp4 video by syncing media clips with audio narration.
Uses MoviePy and FFmpeg.
"""

import json
import os
import sys
import datetime
import subprocess

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def compose_video(audio_path, media_assets, output_dir="output", fps=30, bitrate="2500k"):
    """
    Compose final video from media clips and audio narration.

    Args:
        audio_path: Path to narration MP3 file
        media_assets: List of media asset dicts (from download_media output)
        output_dir: Directory for final video output
        fps: Frames per second
        bitrate: Video bitrate

    Returns:
        Dict with output video metadata
    """
    from moviepy import (
        VideoFileClip, ImageClip, AudioFileClip,
        concatenate_videoclips, ColorClip, CompositeVideoClip
    )

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Filter to assets that have actual files
    valid_assets = [a for a in media_assets if a.get("local_path") and os.path.exists(a["local_path"])]

    if not valid_assets:
        raise ValueError("No valid media assets found")

    print(f"🎬 Composing video: {len(valid_assets)} clips + audio")

    # Load audio
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    print(f"   Audio duration: {audio_duration:.1f}s")

    # Calculate proportional durations
    clip_durations = []
    for asset in valid_assets:
        if asset["type"] == "video":
            clip_durations.append(max(asset.get("duration", 5), 1))
        else:
            clip_durations.append(10)  # Default duration for images

    total_available = sum(clip_durations)
    scale_factor = audio_duration / total_available if total_available > 0 else 1.0
    final_durations = [d * scale_factor for d in clip_durations]

    print(f"   Scale factor: {scale_factor:.2f} ({total_available:.1f}s → {audio_duration:.1f}s)")

    # Build video clips
    video_clips = []
    for i, asset in enumerate(valid_assets):
        required_duration = final_durations[i]
        media_path = asset["local_path"]
        media_type = asset["type"]

        try:
            if media_type == "video":
                clip = _process_video_clip(media_path, required_duration)
            else:
                clip = _process_image_clip(media_path, required_duration)

            # Resize to 1920x1080 with black bars
            clip = _resize_to_1080p(clip)
            video_clips.append(clip)
            print(f"   ✅ Clip {i}: {os.path.basename(media_path)} → {required_duration:.1f}s")

        except Exception as e:
            print(f"   ⚠️  Clip {i} failed ({e}), using black fallback")
            fallback = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=required_duration)
            fallback = fallback.with_fps(fps)
            video_clips.append(fallback)

    # Concatenate all clips
    print("   Concatenating clips...")
    final_video = concatenate_videoclips(video_clips, method="compose")

    # Force exact duration to match audio
    final_video = final_video.with_duration(audio_duration)
    final_video = final_video.with_audio(audio_clip)

    # Verify sync
    duration_diff = abs(final_video.duration - audio_clip.duration)
    if duration_diff > 0.5:
        print(f"   ⚠️  Duration mismatch: {duration_diff:.2f}s (forcing correction)")
        final_video = final_video.with_duration(audio_duration)

    # Export
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = os.path.join(output_dir, f"video_{timestamp}.mp4")

    print(f"   Rendering video to: {output_path}")
    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        bitrate=bitrate,
        preset="ultrafast",
        threads=8,
        logger="bar",  # Show progress bar based on user feedback
    )

    # Close clips to free memory
    audio_clip.close()
    final_video.close()
    for clip in video_clips:
        clip.close()

    # Get output metadata
    file_size_bytes = os.path.getsize(output_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    output_meta = {
        "video_path": output_path,
        "file_size_mb": round(file_size_mb, 2),
        "duration": round(audio_duration, 2),
        "resolution": "1920x1080",
        "fps": fps,
        "codec": "libx264",
        "created_at": datetime.datetime.now().isoformat(),
    }

    with open(".tmp/output_metadata.json", "w", encoding="utf-8") as f:
        json.dump(output_meta, f, indent=2)

    print(f"\n✅ Video rendered: {output_path} ({file_size_mb:.1f} MB, {audio_duration:.1f}s)")
    return output_meta


def _process_video_clip(path, required_duration):
    """Load and adjust video clip to required duration."""
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(path)

    if clip.duration >= required_duration:
        clip = clip.subclipped(0, required_duration)
    else:
        # Loop video to fill required duration
        num_loops = int(required_duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * num_loops)
        clip = clip.subclipped(0, required_duration)

    return clip


def _process_image_clip(path, required_duration):
    """Create video clip from image with Ken Burns-like effect."""
    from moviepy import ImageClip

    clip = ImageClip(path, duration=required_duration)
    return clip


def _resize_to_1080p(clip):
    """Resize clip to 1920x1080, maintaining aspect ratio with black bars."""
    from moviepy import CompositeVideoClip, ColorClip

    target_w, target_h = 1920, 1080

    # Get current dimensions
    w, h = clip.size
    print(f"     resize: {w}x{h} -> target 1920x1080")

    # Calculate scale to fit within 1920x1080
    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    try:
        clip = clip.resized((new_w, new_h))
    except AttributeError:
        clip = clip.resize((new_w, new_h))

    # Center on black background
    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0), duration=clip.duration)
    bg = bg.with_fps(clip.fps if clip.fps else 30)

    final = CompositeVideoClip(
        [bg, clip.with_position("center")],
        size=(target_w, target_h)
    )
    final = final.with_duration(clip.duration)
    return final


if __name__ == "__main__":
    # Load metadata
    audio_meta_path = ".tmp/audio_metadata.json"
    media_assets_path = ".tmp/media_assets.json"

    if not os.path.exists(audio_meta_path):
        print("❌ No audio metadata found. Run generate_audio.py first.")
        sys.exit(1)
    if not os.path.exists(media_assets_path):
        print("❌ No media assets found. Run download_media.py first.")
        sys.exit(1)

    with open(audio_meta_path, "r", encoding="utf-8") as f:
        audio_meta = json.load(f)

    with open(media_assets_path, "r", encoding="utf-8") as f:
        media_data = json.load(f)

    result = compose_video(
        audio_path=audio_meta["local_path"],
        media_assets=media_data["media_assets"],
    )
    print(json.dumps(result, indent=2))

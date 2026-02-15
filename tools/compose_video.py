"""
Video Composition Tool
Renders final .mp4 video by syncing media clips with audio narration.
Uses MoviePy and FFmpeg. Subtitles burned via FFmpeg drawtext filter.

Optimized for speed:
  - 854x480 default resolution (fast render, good for YouTube)
  - 20fps (fewer frames, negligible quality difference)
  - ultrafast preset with sensible bitrate
  - Simplified resize (no CompositeVideoClip overhead)
"""

import json
import os
import sys
import datetime
import subprocess
import shutil

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def compose_video(audio_metadata, media_assets, output_dir="output",
                   fps=20, bitrate="1500k", resolution=(854, 480)):
    """
    Compose final video from media clips and audio narration segments.
    Subtitles are burned in via FFmpeg after initial render.

    Args:
        audio_metadata: Dict with 'segments' key (from generate_audio output)
        media_assets: List of media asset dicts (from download_media output)
        output_dir: Directory for final video output
        fps: Frames per second (20 = fast render, smooth playback)
        bitrate: Video bitrate
        resolution: Output resolution tuple (width, height)

    Returns:
        Dict with output video metadata
    """
    from moviepy import (
        VideoFileClip, ImageClip, AudioFileClip,
        concatenate_videoclips, ColorClip
    )

    target_w, target_h = resolution
    assets_map = {a["segment_index"]: a for a in media_assets}
    audio_segments = audio_metadata.get("segments", [])

    if not audio_segments:
        raise ValueError("No audio segments found")

    print(f"🎬 Composing video: {len(audio_segments)} segments @ {target_w}x{target_h}")

    video_clips = []

    for seg in audio_segments:
        idx = seg["index"]
        audio_path = seg["file_path"]
        duration = seg["duration"]

        print(f"   Segment {idx} ({duration:.1f}s)...", end=" ")

        # 1. Build visual clip
        asset = assets_map.get(idx)
        clip = None

        if asset and asset.get("local_path") and os.path.exists(asset["local_path"]):
            media_path = asset["local_path"]
            try:
                if asset["type"] == "video":
                    clip = _process_video_clip(media_path, duration, target_w, target_h, fps)
                else:
                    clip = _process_image_clip(media_path, duration, target_w, target_h, fps)
            except Exception as e:
                print(f"⚠️ visual fail ({e})", end=" ")
                clip = None

        if clip is None:
            clip = ColorClip(size=(target_w, target_h), color=(0, 0, 0),
                             duration=duration).with_fps(fps)

        # 2. Attach audio
        if os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            clip = clip.with_duration(audio_clip.duration)
            clip = clip.with_audio(audio_clip)

        video_clips.append(clip)
        print("✅")

    # 3. Concatenate
    print("   Concatenating clips...")
    final_video = concatenate_videoclips(video_clips, method="compose")

    # 4. Export raw video (NO subtitles yet)
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    raw_path = os.path.join(output_dir, f"raw_{timestamp}.mp4")
    output_path = os.path.join(output_dir, f"video_{timestamp}.mp4")

    total_duration = final_video.duration

    print(f"   Rendering raw video ({total_duration:.1f}s)...")
    final_video.write_videofile(
        raw_path,
        codec="libx264",
        audio_codec="aac",
        fps=fps,
        bitrate=bitrate,
        preset="ultrafast",
        threads=os.cpu_count() or 4,
        logger="bar",
    )

    # Cleanup MoviePy clips immediately to free memory
    final_video.close()
    for c in video_clips:
        try:
            c.close()
        except:
            pass

    # 5. Burn subtitles with FFmpeg (fast re-encode)
    print("   Burning subtitles with FFmpeg...")
    _burn_subtitles_ffmpeg(raw_path, output_path, audio_segments)

    # Remove raw file
    try:
        os.remove(raw_path)
    except:
        pass

    # Output metadata
    file_size_bytes = os.path.getsize(output_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    output_meta = {
        "video_path": output_path,
        "file_size_mb": round(file_size_mb, 2),
        "duration": round(total_duration, 2),
        "resolution": f"{target_w}x{target_h}",
        "fps": fps,
        "codec": "libx264",
        "created_at": datetime.datetime.now().isoformat(),
    }

    os.makedirs(".tmp", exist_ok=True)
    with open(".tmp/output_metadata.json", "w", encoding="utf-8") as f:
        json.dump(output_meta, f, indent=2)

    print(f"\n✅ Video rendered: {output_path} ({file_size_mb:.1f} MB, {total_duration:.1f}s)")
    return output_meta


def _burn_subtitles_ffmpeg(input_path, output_path, audio_segments):
    """Burn subtitles using FFmpeg subtitles filter — fast."""

    # Build SRT file
    srt_path = os.path.abspath(".tmp/subtitles.srt")
    _generate_srt(audio_segments, srt_path)

    # On Windows, FFmpeg subtitles filter needs forward slashes and escaped colons
    srt_ffmpeg = srt_path.replace("\\", "/")
    if len(srt_ffmpeg) >= 2 and srt_ffmpeg[1] == ':':
        srt_ffmpeg = srt_ffmpeg[0] + "\\:" + srt_ffmpeg[2:]

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"subtitles='{srt_ffmpeg}':force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=25,FontName=Arial'",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "copy",
        "-threads", str(os.cpu_count() or 4),
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

    if result.returncode != 0:
        print(f"   ⚠️ FFmpeg subtitles failed: {result.stderr[-300:] if result.stderr else 'unknown'}")
        print(f"   ⚠️ Saving video without subtitles...")
        shutil.copy2(input_path, output_path)


def _generate_srt(audio_segments, srt_path):
    """Generate SRT subtitle file from audio segment timing."""
    current_time = 0.0

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(audio_segments):
            start = current_time
            end = current_time + seg["duration"]

            f.write(f"{i + 1}\n")
            f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
            f.write(f"{seg['text']}\n\n")

            current_time = end


def _format_srt_time(seconds):
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _process_video_clip(path, required_duration, target_w, target_h, fps):
    """Load, resize, and adjust video clip to required duration."""
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(path, target_resolution=(target_h, target_w))

    if clip.duration >= required_duration:
        clip = clip.subclipped(0, required_duration)
    else:
        num_loops = int(required_duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * num_loops)
        clip = clip.subclipped(0, required_duration)

    # Ensure exact target size
    try:
        clip = clip.resized((target_w, target_h))
    except AttributeError:
        clip = clip.resize((target_w, target_h))

    return clip.with_fps(fps)


def _process_image_clip(path, required_duration, target_w, target_h, fps):
    """Create video clip from image, resized to target."""
    from moviepy import ImageClip

    clip = ImageClip(path, duration=required_duration)

    try:
        clip = clip.resized((target_w, target_h))
    except AttributeError:
        clip = clip.resize((target_w, target_h))

    return clip.with_fps(fps)


if __name__ == "__main__":
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
        audio_metadata=audio_meta,
        media_assets=media_data["media_assets"],
    )
    print(json.dumps(result, indent=2))

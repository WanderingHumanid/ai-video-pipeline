"""Renders final .mp4 by syncing media clips with audio. Subtitles burned via FFmpeg."""

import json
import os
import sys
import datetime
import subprocess
import shutil
import random

BITRATE_MAP = {480: "1000k", 720: "2500k", 1080: "4000k"}
CROSSFADE_DURATION = 0.5

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def _resolve_bitrate(resolution, bitrate_override=None):
    if bitrate_override:
        return bitrate_override
    height = resolution[1]
    for h in sorted(BITRATE_MAP.keys(), reverse=True):
        if height >= h:
            return BITRATE_MAP[h]
    return BITRATE_MAP[min(BITRATE_MAP.keys())]


def compose_video(audio_metadata, media_assets, output_dir="output",
                   fps=20, bitrate=None, resolution=(854, 480),
                   subtitles=True):
    from moviepy import (
        VideoFileClip, ImageClip, AudioFileClip,
        concatenate_videoclips, ColorClip
    )

    target_w, target_h = resolution
    bitrate = _resolve_bitrate(resolution, bitrate)
    assets_map = {a["segment_index"]: a for a in media_assets}
    audio_segments = audio_metadata.get("segments", [])

    if not audio_segments:
        raise ValueError("No audio segments found")

    print(f"🎬 Composing video: {len(audio_segments)} segments @ {target_w}x{target_h} ({bitrate})")

    video_clips = []

    for seg in audio_segments:
        idx = seg["index"]
        audio_path = seg["file_path"]
        duration = seg["duration"]

        print(f"   Segment {idx} ({duration:.1f}s)...", end=" ")

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

        if os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            clip = clip.with_duration(audio_clip.duration)
            clip = clip.with_audio(audio_clip)

        video_clips.append(clip)
        print("✅")

    # Crossfade transitions
    if len(video_clips) > 1:
        from moviepy.video.fx import CrossFadeIn
        for i in range(1, len(video_clips)):
            video_clips[i] = video_clips[i].with_effects([CrossFadeIn(CROSSFADE_DURATION)])
        final_video = concatenate_videoclips(
            video_clips, method="compose",
            padding=-CROSSFADE_DURATION
        )
    else:
        final_video = concatenate_videoclips(video_clips, method="compose")

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

    final_video.close()
    for c in video_clips:
        try:
            c.close()
        except:
            pass

    if subtitles:
        print("   Burning subtitles with FFmpeg...")
        _burn_subtitles_ffmpeg(raw_path, output_path, audio_segments)
    else:
        print("   Subtitles disabled, using raw video.")
        shutil.copy2(raw_path, output_path)

    file_size_bytes = os.path.getsize(output_path)
    file_size_mb = file_size_bytes / (1024 * 1024)

    output_meta = {
        "video_path": output_path,
        "raw_path": raw_path,
        "srt_path": os.path.abspath(".tmp/subtitles.srt") if subtitles else None,
        "file_size_mb": round(file_size_mb, 2),
        "duration": round(total_duration, 2),
        "resolution": f"{target_w}x{target_h}",
        "fps": fps,
        "codec": "libx264",
        "subtitles_enabled": subtitles,
        "created_at": datetime.datetime.now().isoformat(),
    }

    os.makedirs(".tmp", exist_ok=True)
    with open(".tmp/output_metadata.json", "w", encoding="utf-8") as f:
        json.dump(output_meta, f, indent=2)

    print(f"\n✅ Video rendered: {output_path} ({file_size_mb:.1f} MB, {total_duration:.1f}s)")
    return output_meta


def _burn_subtitles_ffmpeg(input_path, output_path, audio_segments):
    srt_path = os.path.abspath(".tmp/subtitles.srt")
    _generate_srt(audio_segments, srt_path)

    # FFmpeg needs forward slashes and escaped colons on Windows
    srt_ffmpeg = srt_path.replace("\\", "/")
    if len(srt_ffmpeg) >= 2 and srt_ffmpeg[1] == ':':
        srt_ffmpeg = srt_ffmpeg[0] + "\\:" + srt_ffmpeg[2:]

    force_style = (
        "FontSize=22,FontName=Arial,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H40000000,BackColour=&H80000000,"
        "BorderStyle=4,Outline=0,Shadow=0,Alignment=2,MarginV=30"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"subtitles='{srt_ffmpeg}':force_style='{force_style}'",
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
    """Generate SRT subtitle file with word-level timing (~4 words per entry)."""
    current_time = 0.0
    entry_num = 0

    with open(srt_path, "w", encoding="utf-8") as f:
        for seg in audio_segments:
            seg_start = current_time
            word_timings = seg.get("word_timings", [])

            if word_timings and len(word_timings) > 1:
                CHUNK_SIZE = 4
                for chunk_start_idx in range(0, len(word_timings), CHUNK_SIZE):
                    chunk = word_timings[chunk_start_idx:chunk_start_idx + CHUNK_SIZE]
                    if not chunk:
                        continue

                    chunk_text = " ".join(w["text"] for w in chunk)
                    start = seg_start + chunk[0]["offset"]
                    last_word = chunk[-1]
                    end = seg_start + last_word["offset"] + last_word["duration"]

                    if end - start < 0.3:
                        end = start + 0.3

                    entry_num += 1
                    f.write(f"{entry_num}\n")
                    f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
                    f.write(f"{chunk_text}\n\n")
            else:
                start = current_time
                end = current_time + seg["duration"]
                entry_num += 1
                f.write(f"{entry_num}\n")
                f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
                f.write(f"{seg['text']}\n\n")

            current_time += seg["duration"]


def _format_srt_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _process_video_clip(path, required_duration, target_w, target_h, fps):
    from moviepy import VideoFileClip, concatenate_videoclips

    clip = VideoFileClip(path, target_resolution=(target_h, target_w))

    if clip.duration >= required_duration:
        clip = clip.subclipped(0, required_duration)
    else:
        num_loops = int(required_duration / clip.duration) + 1
        clip = concatenate_videoclips([clip] * num_loops)
        clip = clip.subclipped(0, required_duration)

    try:
        clip = clip.resized((target_w, target_h))
    except AttributeError:
        clip = clip.resize((target_w, target_h))

    return clip.with_fps(fps)


def _process_image_clip(path, required_duration, target_w, target_h, fps):
    """Create video clip from image with Ken Burns zoom effect."""
    from moviepy import ImageClip

    clip = ImageClip(path, duration=required_duration)

    overscan_w = int(target_w * 1.2)
    overscan_h = int(target_h * 1.2)

    try:
        clip = clip.resized((overscan_w, overscan_h))
    except AttributeError:
        clip = clip.resize((overscan_w, overscan_h))

    zoom_in = random.choice([True, False])
    if zoom_in:
        start_scale, end_scale = 1.0, 1.15
    else:
        start_scale, end_scale = 1.15, 1.0

    def ken_burns(get_frame, t):
        progress = t / max(required_duration, 0.01)
        scale = start_scale + (end_scale - start_scale) * progress
        
        frame = get_frame(t)
        h, w = frame.shape[:2]
        
        new_w = int(target_w * scale)
        new_h = int(target_h * scale)
        
        x1 = max(0, (w - new_w) // 2)
        y1 = max(0, (h - new_h) // 2)
        x2 = min(w, x1 + new_w)
        y2 = min(h, y1 + new_h)
        
        cropped = frame[y1:y2, x1:x2]
        
        from PIL import Image
        import numpy as np
        img = Image.fromarray(cropped)
        img = img.resize((target_w, target_h), Image.LANCZOS)
        return np.array(img)

    clip = clip.transform(ken_burns)
    return clip.with_fps(fps)


def burn_subtitles_only(raw_path, output_path, audio_metadata):
    """Re-burn subtitles on an existing raw video (no re-render needed)."""
    audio_segments = audio_metadata.get("segments", [])
    if not audio_segments:
        raise ValueError("No audio segments for subtitle generation")

    print(f"   Re-burning subtitles on {raw_path}...")
    _burn_subtitles_ffmpeg(raw_path, output_path, audio_segments)

    if os.path.exists(output_path):
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ Subtitles burned: {output_path} ({file_size_mb:.1f} MB)")
    return output_path


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

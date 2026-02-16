"""Main pipeline orchestrator — converts a topic into a video."""

import json
import os
import sys
import time
import argparse
import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.generate_script import generate_script
from tools.extract_keywords import extract_keywords_from_segments
from tools.download_media import download_media
from tools.generate_audio import generate_audio
from tools.compose_video import compose_video
from tools.generate_thumbnail import generate_thumbnail
from tools.upload_youtube import upload_video
from tools.cleanup import cleanup


def run_pipeline(topic, voice="en-US-AriaNeural", skip_upload=False, cleanup_after=False, target_duration=60):
    print("=" * 60)
    print("🎬 AI Video Pipeline")
    print(f"📌 Topic: {topic}")
    print("=" * 60)

    start_time = time.time()
    results = {}

    print("\n" + "─" * 40)
    print("📝 Step 1/5: Generating script...")
    print("─" * 40)

    script_data = generate_script(topic, target_duration=target_duration)
    results["script"] = {
        "segments": len(script_data["segments"]),
        "duration_estimate": script_data["total_duration_estimate"],
    }

    print("\n" + "─" * 40)
    print("🔑 Step 2/5: Extracting keywords...")
    print("─" * 40)

    keywords_data = extract_keywords_from_segments(script_data)
    results["keywords"] = {
        "total_unique": len(keywords_data["all_keywords"]),
    }

    print("\n" + "─" * 40)
    print("🎤 Step 3/5: Generating audio...")
    print("─" * 40)

    audio_data = generate_audio(script_data, voice=voice)
    results["audio"] = {
        "duration": audio_data["duration"],
        "voice": audio_data["voice"],
    }

    print("\n" + "─" * 40)
    print("📥 Step 4/5: Downloading media...")
    print("─" * 40)

    media_data = download_media(keywords_data, audio_duration=audio_data["duration"])
    results["media"] = {
        "total_assets": len(media_data["media_assets"]),
        "sourced": sum(1 for a in media_data["media_assets"] if a["source"] != "none"),
    }

    print("\n" + "─" * 40)
    print("🎬 Step 5/5: Composing video...")
    print("─" * 40)

    video_data = compose_video(
        audio_metadata=audio_data,
        media_assets=media_data["media_assets"],
    )
    results["video"] = {
        "path": video_data["video_path"],
        "size_mb": video_data["file_size_mb"],
        "duration": video_data["duration"],
    }

    # --- Thumbnail ---
    print("\n" + "─" * 40)
    print("🖼️  Generating thumbnail...")
    print("─" * 40)

    try:
        thumbnail_path = generate_thumbnail(topic, media_data["media_assets"])
        results["thumbnail"] = {"path": thumbnail_path}
        print(f"   ✅ Thumbnail: {thumbnail_path}")
    except Exception as e:
        print(f"   ⚠️  Thumbnail generation failed: {e}")
        thumbnail_path = None
        results["thumbnail"] = {"status": "failed", "error": str(e)}

    if not skip_upload:
        print("\n" + "─" * 40)
        print("📤 Optional: Uploading to YouTube...")
        print("─" * 40)

        try:
            upload_data = upload_video(
                video_path=video_data["video_path"],
                topic=topic,
                media_assets=media_data["media_assets"],
                thumbnail_path=thumbnail_path,
                captions_path=video_data.get("srt_path"),
            )
            results["upload"] = {
                "url": upload_data.get("youtube_url", ""),
                "status": upload_data.get("upload_status", ""),
            }
        except Exception as e:
            print(f"⚠️  Upload failed: {e}")
            print("   Video saved locally. You can upload manually later.")
            results["upload"] = {"status": "failed", "error": str(e)}
    else:
        print("\n⏭️  Skipping YouTube upload (--skip-upload)")
        results["upload"] = {"status": "skipped"}

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print("=" * 60)
    print(f"⏱️  Total time: {minutes}m {seconds}s")
    print(f"📝 Script: {results['script']['segments']} segments")
    print(f"🎤 Audio: {results['audio']['duration']:.1f}s")
    print(f"📥 Media: {results['media']['sourced']}/{results['media']['total_assets']} sourced")
    print(f"🎬 Video: {results['video']['path']} ({results['video']['size_mb']:.1f} MB)")

    if results["upload"].get("url"):
        print(f"📤 YouTube: {results['upload']['url']}")
    elif results["upload"]["status"] == "skipped":
        print(f"📤 YouTube: Skipped")
    else:
        print(f"📤 YouTube: {results['upload']['status']}")

    os.makedirs(".tmp", exist_ok=True)
    results["pipeline"] = {
        "topic": topic,
        "elapsed_seconds": round(elapsed, 1),
        "completed_at": datetime.datetime.now().isoformat(),
    }
    with open(".tmp/pipeline_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if cleanup_after:
        print("\n🧹 Cleaning up temporary files...")
        cleanup()

    return results


def main():
    parser = argparse.ArgumentParser(description="AI Video Pipeline")
    parser.add_argument("topic", help="Video topic")
    parser.add_argument("--voice", default="en-US-AriaNeural", help="Edge-TTS voice ID")
    parser.add_argument("--skip-upload", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--cleanup", action="store_true", help="Clean up temp files after")
    parser.add_argument("--duration", type=int, default=60, choices=[30, 60, 90, 120],
                        help="Target duration in seconds (default: 60)")

    args = parser.parse_args()

    run_pipeline(
        topic=args.topic,
        voice=args.voice,
        skip_upload=args.skip_upload,
        cleanup_after=args.cleanup,
        target_duration=args.duration,
    )


if __name__ == "__main__":
    main()

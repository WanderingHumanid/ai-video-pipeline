"""
AI Video Pipeline - Main Orchestrator
Converts a topic into a production-ready YouTube video.

Usage:
    python main.py "Your Topic Here"
    python main.py "Your Topic Here" --skip-upload
    python main.py "Your Topic Here" --voice en-US-GuyNeural
"""

import json
import os
import sys
import time
import argparse
import datetime

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.generate_script import generate_script
from tools.extract_keywords import extract_keywords_from_segments
from tools.download_media import download_media
from tools.generate_audio import generate_audio
from tools.compose_video import compose_video
from tools.upload_youtube import upload_video
from tools.cleanup import cleanup


def run_pipeline(topic, voice="en-US-AriaNeural", skip_upload=False, cleanup_after=False):
    """
    Run the full video generation pipeline.

    Args:
        topic: Video topic string
        voice: Edge-TTS voice ID
        skip_upload: If True, skip YouTube upload step
        cleanup_after: If True, clean up temp files after completion
    """
    print("=" * 60)
    print("🎬 AI Video Pipeline")
    print(f"📌 Topic: {topic}")
    print("=" * 60)

    start_time = time.time()
    results = {}

    # ──────────────── STEP 1: SCRIPT GENERATION ────────────────
    print("\n" + "─" * 40)
    print("📝 Step 1/6: Generating script...")
    print("─" * 40)

    script_data = generate_script(topic)
    results["script"] = {
        "segments": len(script_data["segments"]),
        "duration_estimate": script_data["total_duration_estimate"],
    }

    # ──────────────── STEP 2: KEYWORD EXTRACTION ────────────────
    print("\n" + "─" * 40)
    print("🔑 Step 2/6: Extracting keywords...")
    print("─" * 40)

    keywords_data = extract_keywords_from_segments(script_data)
    results["keywords"] = {
        "total_unique": len(keywords_data["all_keywords"]),
    }

    # ──────────────── STEP 3: AUDIO GENERATION ────────────────
    print("\n" + "─" * 40)
    print("🎤 Step 3/6: Generating audio narration...")
    print("─" * 40)

    audio_data = generate_audio(script_data, voice=voice)
    results["audio"] = {
        "duration": audio_data["duration"],
        "voice": audio_data["voice"],
    }

    # ──────────────── STEP 4: MEDIA SOURCING ────────────────
    print("\n" + "─" * 40)
    print("📥 Step 4/6: Downloading media assets...")
    print("─" * 40)

    media_data = download_media(keywords_data, audio_duration=audio_data["duration"])
    results["media"] = {
        "total_assets": len(media_data["media_assets"]),
        "sourced": sum(1 for a in media_data["media_assets"] if a["source"] != "none"),
    }

    # ──────────────── STEP 5: VIDEO COMPOSITION ────────────────
    print("\n" + "─" * 40)
    print("🎬 Step 5/6: Composing video...")
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

    # ──────────────── STEP 6: YOUTUBE UPLOAD ────────────────
    if not skip_upload:
        print("\n" + "─" * 40)
        print("📤 Step 6/6: Uploading to YouTube...")
        print("─" * 40)

        try:
            upload_data = upload_video(
                video_path=video_data["video_path"],
                topic=topic,
                media_assets=media_data["media_assets"],
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

    # ──────────────── SUMMARY ────────────────
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

    # Save run summary
    os.makedirs(".tmp", exist_ok=True)
    results["pipeline"] = {
        "topic": topic,
        "elapsed_seconds": round(elapsed, 1),
        "completed_at": datetime.datetime.now().isoformat(),
    }
    with open(".tmp/pipeline_summary.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Cleanup
    if cleanup_after:
        print("\n🧹 Cleaning up temporary files...")
        cleanup()

    return results


def main():
    parser = argparse.ArgumentParser(description="AI Video Pipeline - Topic to YouTube")
    parser.add_argument("topic", help="Video topic (e.g., 'The Science Behind Black Holes')")
    parser.add_argument("--voice", default="en-US-AriaNeural", help="Edge-TTS voice ID")
    parser.add_argument("--skip-upload", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--cleanup", action="store_true", help="Clean up temp files after completion")

    args = parser.parse_args()

    run_pipeline(
        topic=args.topic,
        voice=args.voice,
        skip_upload=args.skip_upload,
        cleanup_after=args.cleanup,
    )


if __name__ == "__main__":
    main()

"""
Audio Generation Tool
Converts script text to MP3 audio using Edge-TTS.
"""

import asyncio
import json
import os
import sys
import datetime

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


async def _generate_tts(text, voice, output_path, rate="+0%"):
    """Generate audio using Edge-TTS."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def generate_audio(script_data, voice="en-US-AriaNeural", rate="+0%"):
    """
    Generate audio narration from script text.

    Args:
        script_data: Dict with 'full_script' key (from generate_script output)
        voice: Edge-TTS voice ID
        rate: Speaking rate adjustment (e.g., "+10%", "-5%")

    Returns:
        Dict with audio metadata including path, duration, and voice
    """
    full_script = script_data.get("full_script", "")
    segments = script_data.get("segments", [])

    if not full_script and not segments:
        raise ValueError("Script text cannot be empty")

    os.makedirs(".tmp/audio", exist_ok=True)
    full_output_path = ".tmp/audio/full_audio.mp3"
    
    audio_segments = []
    
    # Generate audio for each segment
    print(f"🎤 Generating audio for {len(segments)} segments...")
    
    for i, segment in enumerate(segments):
        text = segment["text"]
        segment_path = f".tmp/audio/segment_{i}.mp3"
        print(f"   Generating segment {i}...")
        
        asyncio.run(_generate_tts(text, voice, segment_path, rate))
        
        if os.path.exists(segment_path):
            duration = _measure_duration(segment_path, text)
            audio_segments.append({
                "index": i,
                "text": text,
                "file_path": segment_path,
                "duration": duration
            })
        else:
            raise RuntimeError(f"Failed to generate audio for segment {i}")

    # Combine all segments into full audio (optional, but good for preview)
    from pydub import AudioSegment
    full_audio = AudioSegment.empty()
    for seg in audio_segments:
        try:
            seg_audio = AudioSegment.from_mp3(seg["file_path"])
            full_audio += seg_audio
            # Add a small silence between segments if needed? 
            # For now, keeping it tight to match video concatenation
        except Exception as e:
            print(f"⚠️  Error merging segment {seg['index']}: {e}")

    full_audio.export(full_output_path, format="mp3")
    total_duration = len(full_audio) / 1000.0

    output = {
        "script": full_script,
        "local_path": full_output_path,
        "duration": round(total_duration, 2),
        "segments": audio_segments,
        "voice": voice,
        "generated_at": datetime.datetime.now().isoformat(),
    }

    with open(".tmp/audio_metadata.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Audio generated: {full_output_path} ({total_duration:.1f}s)")
    return output


def _generate_long_script(text, voice, output_path, rate):
    # Deprecated in favor of segment-based generation, but keeping for fallback
    pass 



def _measure_duration(audio_path, fallback_text=""):
    """Measure audio duration using pydub, with word-count fallback."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        print(f"⚠️  Duration measurement failed ({e}), using word-count estimate")
        word_count = len(fallback_text.split())
        return word_count / 2.5  # ~2.5 words per second


if __name__ == "__main__":
    script_path = ".tmp/script.json"
    if not os.path.exists(script_path):
        print("❌ No script found. Run generate_script.py first.")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        script_data = json.load(f)

    voice = sys.argv[1] if len(sys.argv) > 1 else "en-US-AriaNeural"
    result = generate_audio(script_data, voice=voice)
    print(f"\nDuration: {result['duration']}s")

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
    if not full_script or full_script.strip() == "":
        raise ValueError("Script text cannot be empty")

    os.makedirs(".tmp", exist_ok=True)
    output_path = ".tmp/audio.mp3"

    # Generate audio with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"🎤 Generating audio with voice: {voice} (attempt {attempt + 1})")

            # Handle long scripts by splitting
            if len(full_script) > 5000:
                _generate_long_script(full_script, voice, output_path, rate)
            else:
                asyncio.run(_generate_tts(full_script, voice, output_path, rate))

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                break
            else:
                raise RuntimeError("Audio file not created or empty")

        except Exception as e:
            print(f"⚠️  Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Audio generation failed after {max_retries} attempts: {e}")

    # Measure actual duration
    duration = _measure_duration(output_path, full_script)

    output = {
        "script": full_script,
        "local_path": output_path,
        "duration": round(duration, 2),
        "voice": voice,
        "generated_at": datetime.datetime.now().isoformat(),
    }

    with open(".tmp/audio_metadata.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Audio generated: {output_path} ({duration:.1f}s, {os.path.getsize(output_path)} bytes)")
    return output


def _generate_long_script(text, voice, output_path, rate):
    """Split long scripts into chunks, generate separately, concatenate."""
    from pydub import AudioSegment

    # Split at sentence boundaries roughly every 4000 chars
    chunks = []
    current_chunk = ""
    sentences = text.replace(". ", ".\n").split("\n")

    for sentence in sentences:
        if len(current_chunk) + len(sentence) > 4000 and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    print(f"   Split into {len(chunks)} chunks for processing")

    combined = AudioSegment.empty()
    for i, chunk in enumerate(chunks):
        chunk_path = f".tmp/audio_chunk_{i}.mp3"
        asyncio.run(_generate_tts(chunk, voice, chunk_path, rate))
        chunk_audio = AudioSegment.from_mp3(chunk_path)
        combined += chunk_audio
        os.remove(chunk_path)

    combined.export(output_path, format="mp3")


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

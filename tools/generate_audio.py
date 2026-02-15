"""Converts script text to MP3 using Edge-TTS."""

import asyncio
import json
import os
import sys
import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


async def _generate_tts(text, voice, output_path, rate="+0%"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def _synthesize_word_timings(text, duration):
    """Distribute audio duration across words proportionally by character length."""
    words = text.split()
    if not words or duration <= 0:
        return []

    char_counts = [max(len(w), 1) for w in words]
    total_chars = sum(char_counts)

    timings = []
    current_offset = 0.0
    for word, ccount in zip(words, char_counts):
        word_dur = (ccount / total_chars) * duration
        timings.append({
            "text": word,
            "offset": round(current_offset, 4),
            "duration": round(word_dur, 4),
        })
        current_offset += word_dur

    return timings


def generate_audio(script_data, voice="en-US-AriaNeural", rate="+0%"):
    full_script = script_data.get("full_script", "")
    segments = script_data.get("segments", [])

    if not full_script and not segments:
        raise ValueError("Script text cannot be empty")

    os.makedirs(".tmp/audio", exist_ok=True)
    full_output_path = ".tmp/audio/full_audio.mp3"
    
    audio_segments = []
    
    print(f"🎤 Generating audio for {len(segments)} segments...")
    
    for i, segment in enumerate(segments):
        text = segment["text"]
        segment_path = f".tmp/audio/segment_{i}.mp3"
        print(f"   Generating segment {i}...")
        
        asyncio.run(_generate_tts(text, voice, segment_path, rate))
        
        if os.path.exists(segment_path):
            duration = _measure_duration(segment_path, text)
            word_timings = _synthesize_word_timings(text, duration)
            audio_segments.append({
                "index": i,
                "text": text,
                "file_path": segment_path,
                "duration": duration,
                "word_timings": word_timings,
            })
        else:
            raise RuntimeError(f"Failed to generate audio for segment {i}")

    total_duration = sum(seg["duration"] for seg in audio_segments)

    output = {
        "script": full_script,
        "local_path": "",
        "duration": round(total_duration, 2),
        "segments": audio_segments,
        "voice": voice,
        "generated_at": datetime.datetime.now().isoformat(),
    }

    with open(".tmp/audio_metadata.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Audio generated: {full_output_path} ({total_duration:.1f}s)")
    return output


def _measure_duration(audio_path, fallback_text=""):
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(audio_path)
        return len(audio) / 1000.0
    except Exception:
        word_count = len(fallback_text.split())
        return word_count / 2.5


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

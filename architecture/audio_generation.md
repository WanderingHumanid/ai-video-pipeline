# Architecture SOP: Audio Generation

**Component:** Audio Generation (Layer 3 Tool)  
**Owner:** `tools/generate_audio.py`  
**Purpose:** Convert script text to MP3 audio using Edge-TTS

---

## 📋 Input Schema

```json
{
  "full_script": "string (complete narration text)",
  "voice": "string (optional, default: en-US-AriaNeural)"
}
```

---

## 📤 Output Schema

```json
{
  "script": "string",
  "local_path": ".tmp/audio.mp3",
  "duration": "float (seconds, measured after generation)",
  "voice": "string (TTS voice ID used)",
  "generated_at": "ISO 8601 datetime"
}
```

---

## 🎯 Behavioral Rules

### 1. Voice Selection
- **Default Voice:** `en-US-AriaNeural` (female, clear, professional)
- **Alternative:** `en-US-GuyNeural` (male voice)
- **Customization:** Allow user to specify voice in future versions

### 2. Audio Quality
- **Format:** MP3
- **Bitrate:** Use default (typically 48kbps for speech)
- **Sample Rate:** 24kHz (Edge-TTS default)

### 3. Speaking Rate
- **Default:** Normal speed (rate="+0%")
- **Optimization:** Slightly faster for engagement (rate="+10%" tested in Phase 4)
- **Constraint:** Don't exceed +20% (comprehension drops)

### 4. Duration Accuracy
- **Measurement:** Calculate actual duration using `AudioSegment` (pydub) after generation
- **Critical:** This duration is the SOURCE OF TRUTH for video composition
- **Tolerance:** ±0.5 seconds acceptable

---

## ⚙️ Tool Implementation Logic

### Step 1: Input Validation
```python
if not full_script or full_script.strip() == "":
    raise ValueError("Script cannot be empty")
```

### Step 2: Initialize Edge-TTS
```python
import edge_tts
import asyncio

async def generate_audio(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
```

### Step 3: Generate Audio
```python
import os

output_path = ".tmp/audio.mp3"
os.makedirs(".tmp", exist_ok=True)

voice = "en-US-AriaNeural"  # Default
script_text = input_script["full_script"]

# Run async generation
asyncio.run(generate_audio(script_text, voice, output_path))
```

### Step 4: Measure Duration
```python
from pydub import AudioSegment
from pydub.utils import mediainfo

audio = AudioSegment.from_mp3(output_path)
duration_seconds = len(audio) / 1000.0  # Convert ms to seconds
```

### Step 5: Output
```python
import datetime

audio_object = {
    "script": script_text,
    "local_path": output_path,
    "duration": duration_seconds,
    "voice": voice,
    "generated_at": datetime.datetime.now().isoformat()
}

# Save JSON
import json
with open(".tmp/audio_metadata.json", "w") as f:
    json.dump(audio_object, f, indent=2)

return audio_object
```

---

## 🐛 Error Handling

### Error: Edge-TTS library not installed
- **Action:** Prompt user to run `pip install edge-tts`
- **Check:** Verify at start of script with `import edge_tts`

### Error: Network failure during TTS generation
- **Action:** Retry 3 times with exponential backoff (2s, 4s, 8s)
- **Fallback:** If all retries fail, notify user and exit

### Error: Script too long for single TTS call
- **Detection:** If script > 5000 characters
- **Action:** Split into segments, generate separately, concatenate MP3s
- **Tool:** Use `pydub` for concatenation

### Error: Duration measurement fails
- **Cause:** Corrupt MP3 file
- **Action:** Regenerate audio
- **Fallback:** Manually calculate duration: `len(text.split()) / 2.5` (average 2.5 words/second)

---

## 🔧 Advanced Features (Phase 4 Optimization)

### Feature 1: Speaking Rate Adjustment
```python
# Faster for engaging content
communicate = edge_tts.Communicate(text, voice, rate="+10%")
```

### Feature 2: Pitch Adjustment
```python
# Slightly higher pitch for enthusiasm
communicate = edge_tts.Communicate(text, voice, pitch="+5Hz")
```

### Feature 3: Volume Normalization
```python
from pydub.effects import normalize

audio = AudioSegment.from_mp3(output_path)
normalized_audio = normalize(audio)
normalized_audio.export(output_path, format="mp3")
```

---

## 🧪 Test Cases

### Test 1: Basic Generation
- **Input:** Script = "Hello, world!"
- **Expected:** `.tmp/audio.mp3` created, duration ~1 second

### Test 2: Full Script (60 seconds)
- **Input:** 150-word script
- **Expected:** Duration ~60 seconds (2.5 words/second average)

### Test 3: Long Script (Split Required)
- **Input:** 6000 character script
- **Expected:** Splits into segments, concatenates, single MP3 output

### Test 4: Network Failure
- **Simulate:** Disconnect internet mid-generation
- **Expected:** Retry 3 times, then fail gracefully with error message

---

## 📊 Success Criteria

- ✅ Audio file generated at `.tmp/audio.mp3`
- ✅ Duration measured accurately (±0.5 seconds)
- ✅ Audio plays correctly (no corruption)
- ✅ Voice is clear and natural-sounding
- ✅ Metadata JSON saved to `.tmp/audio_metadata.json`

---

**Last Updated:** 2026-02-14  
**Self-Annealing Log:** None yet

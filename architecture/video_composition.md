# Architecture SOP: Video Composition

**Component:** Video Composition (Layer 3 Tool)  
**Owner:** `tools/compose_video.py`  
**Purpose:** Render final .mp4 video by syncing media clips with audio narration

---

## 📋 Input Schema

```json
{
  "audio_path": ".tmp/audio.mp3",
  "audio_duration": 62.5,
  "media_assets": [
    {
      "segment_index": 0,
      "local_path": ".tmp/media/segment_0.mp4",
      "type": "video|image",
      "duration": 15.0
    }
  ],
  "output_resolution": "1920x1080",
  "fps": 30
}
```

---

## 📤 Output Schema

```json
{
  "video_path": "output/video_20260214164945.mp4",
  "file_size_mb": 45.3,
  "duration": 62.5,
  "resolution": "1920x1080",
  "fps": 30,
  "codec": "libx264",
  "created_at": "ISO 8601 datetime"
}
```

---

## 🎯 Behavioral Rules (CRITICAL)

### 1. Visual-Audio Sync (Mandatory Logic Constraint)
**The Golden Rule:** Total video duration MUST equal audio duration exactly (±0.5s tolerance).

**Implementation:**
1. Calculate total audio duration (from audio metadata)
2. Distribute media clips proportionally to fill the entire timeline
3. No gaps, no overruns

### 2. Clip Duration Distribution Algorithm
```
total_audio_duration = 62.5 seconds
num_clips = 7
clip_durations = [15, 10, 8, 12, 10, 5, 20]  # Original durations

# Option A: Equal distribution (simple)
duration_per_clip = total_audio_duration / num_clips  # 62.5 / 7 = 8.93 seconds each

# Option B: Proportional distribution (preferred)
total_available_duration = sum(clip_durations)  # 80 seconds
scale_factor = total_audio_duration / total_available_duration  # 62.5 / 80 = 0.78

scaled_durations = [d * scale_factor for d in clip_durations]
# Result: [11.7, 7.8, 6.2, 9.4, 7.8, 3.9, 15.6] → Total = 62.5 seconds
```

**Use Option B (Proportional)** to preserve natural pacing.

### 3. Video vs. Image Handling
- **Video Clips:**
  - If clip duration > required duration: Trim to fit
  - If clip duration < required duration: Loop or speed up
- **Images:**
  - Use Ken Burns effect (slow zoom/pan) for visual interest
  - Display for exact required duration

### 4. Resolution & Quality
- **Resolution:** 1920x1080 (1080p) for YouTube
- **FPS:** 30 (standard for web video)
- **Codec:** H.264 (libx264) - best compatibility
- **Bitrate:** 8000k (8 Mbps) - high quality

---

## ⚙️ Tool Implementation Logic

### Step 1: Load Inputs
```python
from moviepy.editor import VideoFileClip, ImageClip, AudioFileClip, concatenate_videoclips
import os

audio_clip = AudioFileClip(audio_path)
audio_duration = audio_clip.duration

media_assets = load_json(".tmp/media_assets.json")
```

### Step 2: Calculate Clip Durations (Proportional Distribution)
```python
segment_durations = [asset["duration"] for asset in media_assets]
total_available = sum(segment_durations)

scale_factor = audio_duration / total_available if total_available > 0 else 1.0

final_durations = [d * scale_factor for d in segment_durations]
```

### Step 3: Load and Process Media Clips
```python
video_clips = []

for i, asset in enumerate(media_assets):
    required_duration = final_durations[i]
    media_path = asset["local_path"]
    media_type = asset["type"]
    
    if media_type == "video":
        clip = VideoFileClip(media_path)
        
        if clip.duration > required_duration:
            # Trim to fit
            clip = clip.subclip(0, required_duration)
        elif clip.duration < required_duration:
            # Loop video
            num_loops = int(required_duration / clip.duration) + 1
            clip = concatenate_videoclips([clip] * num_loops).subclip(0, required_duration)
        
    elif media_type == "image":
        # Ken Burns effect: slow zoom
        clip = ImageClip(media_path, duration=required_duration)
        clip = clip.resize(height=1080)  # Resize to 1080p
        clip = clip.set_position("center")
        
        # Optional: Add zoom effect
        # clip = clip.resize(lambda t: 1 + 0.02 * t)  # 2% zoom per second
    
    # Resize to 1920x1080 (maintain aspect ratio, add black bars if needed)
    clip = clip.resize(height=1080)
    clip = clip.on_color(size=(1920, 1080), color=(0, 0, 0), pos="center")
    
    video_clips.append(clip)
```

### Step 4: Concatenate Video Clips
```python
final_video = concatenate_videoclips(video_clips, method="compose")

# CRITICAL: Set audio duration to match video
final_video = final_video.set_duration(audio_duration)
```

### Step 5: Add Audio Track
```python
# Set audio
final_video = final_video.set_audio(audio_clip)

# Verify sync
assert abs(final_video.duration - audio_clip.duration) < 0.5, "Audio/video duration mismatch!"
```

### Step 6: Export Video
```python
import datetime

timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
output_path = f"output/video_{timestamp}.mp4"

os.makedirs("output", exist_ok=True)

final_video.write_videofile(
    output_path,
    codec="libx264",
    audio_codec="aac",
    fps=30,
    bitrate="8000k",
    preset="medium",  # Balance between speed and quality
    threads=4  # Parallel encoding
)
```

### Step 7: Get File Metadata
```python
import os

file_size_bytes = os.path.getsize(output_path)
file_size_mb = file_size_bytes / (1024 * 1024)

output_metadata = {
    "video_path": output_path,
    "file_size_mb": round(file_size_mb, 2),
    "duration": audio_duration,
    "resolution": "1920x1080",
    "fps": 30,
    "codec": "libx264",
    "created_at": datetime.datetime.now().isoformat()
}

# Save metadata
with open(".tmp/output_metadata.json", "w") as f:
    json.dump(output_metadata, f, indent=2)

return output_metadata
```

---

## 🐛 Error Handling

### Error: Audio/video duration mismatch after composition
- **Detection:** `abs(final_video.duration - audio_clip.duration) > 0.5`
- **Cause:** Clip distribution algorithm failed
- **Action:** Force-set video duration: `final_video = final_video.set_duration(audio_duration)`

### Error: Video clip codec not supported by MoviePy
- **Cause:** Some Pexels videos use uncommon codecs
- **Action:** Re-encode with FFmpeg before loading:
  ```bash
  ffmpeg -i input.mp4 -c:v libx264 -c:a aac output_reencoded.mp4
  ```

### Error: Image file corrupt or unreadable
- **Action:** Skip image, use black screen with text overlay: "Media Unavailable"

### Error: Rendering fails due to memory
- **Cause:** Too many high-res clips in memory
- **Action:** Reduce resolution during composition, then upscale final video

### Error: Export hangs or crashes
- **Action:** Reduce `threads` parameter from 4 to 2
- **Fallback:** Use `preset="ultrafast"` (lower quality, faster)

---

## 🔧 Optimization Strategies

### 1. Pre-Processing Clips
- Resize all clips to 1920x1080 BEFORE concatenation
- Reduces memory usage during composition

### 2. Hardware Acceleration
- Use `preset="veryfast"` for CPU encoding
- Consider GPU encoding (H.264_nvenc) if available

### 3. Quality vs. Speed Trade-off
- Development: `preset="ultrafast"`, `bitrate="4000k"`
- Production: `preset="medium"`, `bitrate="8000k"`

---

## 🧪 Test Cases

### Test 1: Basic Composition (5 video clips)
- **Input:** 5 clips, audio = 60 seconds
- **Expected:** Video duration = 60 seconds (±0.5s), plays without gaps

### Test 2: Mixed Media (3 videos + 2 images)
- **Input:** Mix of videos and images
- **Expected:** Images displayed with Ken Burns effect, smooth transitions

### Test 3: Looping Short Clip
- **Input:** 5-second clip, required duration = 20 seconds
- **Expected:** Clip loops 4 times seamlessly

### Test 4: High-Resolution Stress Test
- **Input:** 10 x 4K video clips
- **Expected:** Composition succeeds (may take longer), output is 1080p

---

## 📊 Success Criteria

- ✅ Final video duration = audio duration (±0.5 seconds)
- ✅ No silent portions or audio cutoffs
- ✅ Video plays smoothly without stuttering
- ✅ Resolution is 1920x1080 at 30fps
- ✅ File size reasonable (<100MB for 60-second video)
- ✅ Audio and video are perfectly synchronized

---

**Last Updated:** 2026-02-14  
**Self-Annealing Log:** None yet

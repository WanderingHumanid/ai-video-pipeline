# Architecture SOP: Media Sourcing

**Component:** Media Sourcing (Layer 3 Tool)  
**Owner:** `tools/download_media.py`  
**Purpose:** Download stock video/images from Pexels API with intelligent fallback logic

---

## 📋 Input Schema

```json
{
  "keywords_by_segment": [
    {
      "segment_index": 0,
      "keywords": ["keyword1", "keyword2"],
      "primary_keyword": "keyword1",
      "duration_estimate": 12.5
    }
  ]
}
```

---

## 📤 Output Schema

```json
{
  "media_assets": [
    {
      "segment_index": 0,
      "keyword": "ocean",
      "source": "pexels|ai-generated",
      "type": "video|image",
      "url": "https://...",
      "local_path": ".tmp/media/segment_0_ocean.mp4",
      "duration": 15.0,
      "attribution": "Jane Doe on Pexels"
    }
  ]
}
```

---

## 🎯 Behavioral Rules

### 1. Video vs. Image Priority
- **Prefer Videos:** Videos are more engaging for narration
- **Use Images:** Only if no videos found OR video duration < segment duration
- **Image Duration:** Display image for segment duration (static or Ken Burns effect)

### 2. Attribution Management
- **Store:** Photographer/videographer name from API response
- **Format:** "Video by [Name] on Pexels"
- **Placement:** In video description (not rendered in video itself)

### 3. Download Strategy
- **Orientation:** Prefer landscape (16:9) for YouTube
- **Quality:** Download highest available quality (1080p preferred)
- **File Size:** Monitor to avoid exceeding disk limits

### 4. Rate Limit Respect
- **Limit:** 200 requests/hour (Pexels API)
- **Implementation:** Add 500ms delay between requests (conservative)
- **Monitoring:** Track request count and warn if approaching limit

---

## 🔄 Fallback Logic (3-Tier System)

### Tier 1: Primary Keyword Search
```python
search_query = primary_keyword
results = pexels_api.search_videos(query=search_query, per_page=10, orientation="landscape")
if results:
    select_best_match(results)
else:
    go_to_tier_2()
```

### Tier 2: Simplified Keyword Search
```python
# Simplify keyword by removing adjectives
simplified_keyword = simplify(primary_keyword)
# Example: "black hole" → "space"
results = pexels_api.search_videos(query=simplified_keyword, per_page=10)
if results:
    select_best_match(results)
else:
    go_to_tier_3()
```

**Simplification Rules:**
- Remove adjectives (keep nouns)
- Use category generics:
  - Science → "space", "lab", "microscope"
  - Technology → "computer", "digital", "future"
  - Nature → "forest", "ocean", "mountain"
  - Urban → "city", "building", "traffic"

### Tier 3: AI-Generated Image
```python
# Generate image using Antigravity's generate_image tool
prompt = f"A realistic, cinematic photograph of {keyword}"
ai_image_path = generate_image(prompt, output_path=f".tmp/media/ai_{segment_index}.png")
return {
    "source": "ai-generated",
    "type": "image",
    "local_path": ai_image_path,
    "duration": segment_duration,
    "attribution": "AI Generated"
}
```

---

## ⚙️ Tool Implementation Logic

### Step 1: Initialize Pexels API Client
```python
from dotenv import load_dotenv
import os
import requests

load_dotenv()
API_KEY = os.getenv("PEXELS_API_KEY")
BASE_URL = "https://api.pexels.com/v1/"
HEADERS = {"Authorization": API_KEY}
```

### Step 2: For Each Segment
```python
for segment in keywords_by_segment:
    primary_keyword = segment["primary_keyword"]
    duration_needed = segment["duration_estimate"]
    
    # Try Tier 1: Primary keyword
    media = search_pexels_videos(primary_keyword, duration_needed)
    
    if not media:
        # Try Tier 2: Simplified keyword
        simplified = simplify_keyword(primary_keyword)
        media = search_pexels_videos(simplified, duration_needed)
    
    if not media:
        # Tier 3: AI-generated image
        media = generate_ai_image(primary_keyword, segment["segment_index"])
    
    # Download media to .tmp/media/
    local_path = download_media(media, segment["segment_index"])
    media["local_path"] = local_path
    
    media_assets.append(media)
```

### Step 3: Search Pexels Videos
```python
def search_pexels_videos(query, duration_needed):
    endpoint = f"{BASE_URL}videos/search"
    params = {
        "query": query,
        "per_page": 10,
        "orientation": "landscape"
    }
    
    response = requests.get(endpoint, headers=HEADERS, params=params)
    
    if response.status_code == 200:
        videos = response.json().get("videos", [])
        
        if videos:
            # Select video with duration >= segment duration
            best_match = select_best_video(videos, duration_needed)
            return best_match
    
    elif response.status_code == 429:
        # Rate limit exceeded
        log_error("Pexels rate limit exceeded. Wait before retrying.")
        time.sleep(3600)  # Wait 1 hour
    
    return None
```

### Step 4: Select Best Video
```python
def select_best_video(videos, duration_needed):
    # Filter videos by duration
    suitable = [v for v in videos if v["duration"] >= duration_needed]
    
    if not suitable:
        # Fallback: Use longest available video
        suitable = videos
    
    # Select highest quality video
    best = max(suitable, key=lambda v: v.get("width", 0))
    
    return {
        "type": "video",
        "source": "pexels",
        "url": best["video_files"][0]["link"],  # Highest quality file
        "duration": best["duration"],
        "attribution": f"{best['user']['name']} on Pexels"
    }
```

### Step 5: Download Media
```python
def download_media(media, segment_index):
    url = media["url"]
    extension = "mp4" if media["type"] == "video" else "png"
    filename = f"segment_{segment_index}.{extension}"
    local_path = f".tmp/media/{filename}"
    
    os.makedirs(".tmp/media", exist_ok=True)
    
    response = requests.get(url, stream=True)
    with open(local_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    return local_path
```

### Step 6: Output
- Save JSON to `.tmp/media_assets.json`
- Return media assets object

---

## 🐛 Error Handling

### Error: Pexels API returns 401 (Unauthorized)
- **Cause:** Invalid or missing API key
- **Action:** Verify `.env` file has `PEXELS_API_KEY`
- **Log:** "Pexels API authentication failed. Check API key."

### Error: Pexels API returns 429 (Rate Limit)
- **Action:** Wait 1 hour before retrying
- **Fallback:** Use AI-generated images for remaining segments

### Error: No videos found for keyword
- **Action:** Proceed to Tier 2 (simplified keyword)
- **Log:** "No Pexels results for '{keyword}'. Trying simplified version."

### Error: Download fails (network issue)
- **Action:** Retry download 3 times with exponential backoff
- **Fallback:** Skip to next keyword or generate AI image

### Error: Video duration < segment duration
- **Action:** Loop video or use image fallback
- **Log:** "Video too short. Using image or looping."

---

## 🧪 Test Cases

### Test 1: Successful Video Download
- **Input:** Keyword = "ocean", Duration = 10 seconds
- **Expected:** Download .mp4 from Pexels, duration >= 10s

### Test 2: Keyword Simplification
- **Input:** Keyword = "quantum computer", No results
- **Expected:** Fallback to "computer", successful download

### Test 3: AI-Generated Fallback
- **Input:** Keyword = "zxyqwert" (nonsense), No results
- **Expected:** Generate AI image, save to `.tmp/media/ai_0.png`

### Test 4: Rate Limit Handling
- **Input:** 201st request in 1 hour
- **Expected:** Wait 1 hour, then retry OR use AI images

---

## 📊 Success Criteria

- ✅ Every segment has a media asset (video or image)
- ✅ All media files downloaded to `.tmp/media/`
- ✅ Video durations >= segment durations (or loopable)
- ✅ Attribution metadata captured
- ✅ Fallback logic triggers correctly when Pexels fails
- ✅ Rate limits respected (max 200 requests/hour)

---

**Last Updated:** 2026-02-14  
**Self-Annealing Log:** None yet

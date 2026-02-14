"""
Media Sourcing Tool
Downloads stock video/images from Pexels API with 3-tier fallback logic.
"""

import json
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
BASE_URL = "https://api.pexels.com/"
HEADERS = {"Authorization": PEXELS_API_KEY} if PEXELS_API_KEY else {}
REQUEST_DELAY = 0.5  # Seconds between API requests (rate limit safety)

# Category generic fallbacks for Tier 2
CATEGORY_GENERICS = {
    "science": "space", "physics": "space", "chemistry": "laboratory",
    "biology": "nature", "astronomy": "galaxy", "math": "equations",
    "technology": "computer", "coding": "programming", "robot": "robot",
    "health": "hospital", "medicine": "doctor", "fitness": "exercise",
    "nature": "forest", "environment": "ocean", "climate": "weather",
    "history": "ancient ruins", "war": "battlefield", "culture": "city",
    "finance": "stock market", "business": "office", "economy": "money",
}


def download_media(keywords_data, audio_duration=60.0):
    """
    Download media assets for each segment based on keywords.

    Args:
        keywords_data: Dict from extract_keywords output
        audio_duration: Total audio duration for proportional segment timing

    Returns:
        Dict with media_assets list
    """
    if not PEXELS_API_KEY or PEXELS_API_KEY == "your_pexels_api_key_here":
        raise ValueError("PEXELS_API_KEY not configured in .env")

    segments = keywords_data.get("keywords_by_segment", [])
    if not segments:
        raise ValueError("No keyword segments provided")

    os.makedirs(".tmp/media", exist_ok=True)

    # Calculate duration per segment (proportional distribution)
    num_segments = len(segments)
    duration_per_segment = audio_duration / num_segments

    media_assets = []

    for segment in segments:
        idx = segment["segment_index"]
        keywords = segment["keywords"]
        primary_kw = segment["primary_keyword"]
        visual_query = segment.get("visual_search_query")

        print(f"\n📥 Segment {idx}: Processing...")

        media = None

        # Tier 0: Specific Visual Search Query (Highest Relevance)
        if visual_query:
            print(f"   🔎 Searching: '{visual_query}'")
            media = _search_pexels_video(visual_query, duration_per_segment)

        # Tier 1: Primary keyword video search
        if not media:
            print(f"   ↳ Fallback to keyword: '{primary_kw}'")
            media = _search_pexels_video(primary_kw, duration_per_segment)

        # Tier 2: Try alternative keywords + simplified versions
        if not media:
            for kw in keywords[1:]:
                media = _search_pexels_video(kw, duration_per_segment)
                if media:
                    break

        if not media:
            simplified = _simplify_keyword(primary_kw)
            if simplified != primary_kw:
                print(f"   ↳ Trying simplified: '{simplified}'")
                media = _search_pexels_video(simplified, duration_per_segment)

        # Tier 3: Try image search as final fallback
        if not media:
            print(f"   ↳ No videos found. Trying image search...")
            media = _search_pexels_image(primary_kw)

        if not media:
            for kw in keywords:
                media = _search_pexels_image(kw)
                if media:
                    break

        # Ultimate fallback: use a generic nature/abstract video
        if not media:
            print(f"   ↳ Using generic fallback...")
            media = _search_pexels_video("nature landscape", duration_per_segment)

        if not media:
            media = _search_pexels_image("abstract background")

        if media:
            # Download the file
            local_path = _download_file(media["url"], idx, media["type"])
            media["local_path"] = local_path
            media["segment_index"] = idx
            media["keyword"] = primary_kw
            print(f"   ✅ Downloaded: {os.path.basename(local_path)}")
        else:
            print(f"   ❌ No media found for segment {idx}")
            media = {
                "segment_index": idx,
                "keyword": primary_kw,
                "source": "none",
                "type": "none",
                "url": "",
                "local_path": "",
                "duration": duration_per_segment,
                "attribution": "N/A",
            }

        media_assets.append(media)
        time.sleep(REQUEST_DELAY)

    output = {"media_assets": media_assets}

    with open(".tmp/media_assets.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    successful = sum(1 for m in media_assets if m["source"] != "none")
    print(f"\n✅ Media sourcing complete: {successful}/{len(media_assets)} segments sourced")
    return output


def _search_pexels_video(query, min_duration=5):
    """Search Pexels for videos matching query."""
    try:
        endpoint = f"{BASE_URL}videos/search"
        params = {"query": query, "per_page": 10, "orientation": "landscape"}

        response = requests.get(endpoint, headers=HEADERS, params=params, timeout=10)

        if response.status_code == 429:
            print("   ⚠️  Rate limit hit. Waiting 60s...")
            time.sleep(60)
            response = requests.get(endpoint, headers=HEADERS, params=params, timeout=10)

        if response.status_code != 200:
            return None

        videos = response.json().get("videos", [])
        if not videos:
            return None

        # Select best video (prefer duration >= min_duration, highest quality)
        best = _select_best_video(videos, min_duration)
        return best

    except Exception as e:
        print(f"   ⚠️  Video search error: {e}")
        return None


def _search_pexels_image(query):
    """Search Pexels for images matching query."""
    try:
        endpoint = f"{BASE_URL}v1/search"
        params = {"query": query, "per_page": 5, "orientation": "landscape"}

        response = requests.get(endpoint, headers=HEADERS, params=params, timeout=10)

        if response.status_code != 200:
            return None

        photos = response.json().get("photos", [])
        if not photos:
            return None

        best = photos[0]
        # Prefer large or original size
        image_url = best["src"].get("large2x", best["src"].get("large", best["src"]["original"]))

        return {
            "type": "image",
            "source": "pexels",
            "url": image_url,
            "duration": 0,  # Images don't have duration
            "attribution": f"{best['photographer']} on Pexels",
        }

    except Exception as e:
        print(f"   ⚠️  Image search error: {e}")
        return None


def _select_best_video(videos, min_duration):
    """Select the best video from search results."""
    # Prefer videos with duration >= min_duration
    suitable = [v for v in videos if v.get("duration", 0) >= min_duration]
    if not suitable:
        suitable = videos  # Fallback to any video

    # Sort by width (quality) descending
    suitable.sort(key=lambda v: v.get("width", 0), reverse=True)
    best = suitable[0]

    # Find best quality video file (prefer HD, mp4)
    video_files = best.get("video_files", [])
    if not video_files:
        return None

    # Sort by width descending, prefer mp4
    video_files.sort(key=lambda f: (f.get("width", 0)), reverse=True)

    # Pick first HD file, or fallback to largest available
    chosen_file = None
    for vf in video_files:
        w = vf.get("width", 0)
        if 720 <= w <= 1920 and vf.get("file_type", "") == "video/mp4":
            chosen_file = vf
            break

    if not chosen_file:
        chosen_file = video_files[0]

    return {
        "type": "video",
        "source": "pexels",
        "url": chosen_file["link"],
        "duration": best.get("duration", 0),
        "attribution": f"{best['user']['name']} on Pexels",
    }


def _download_file(url, segment_index, media_type):
    """Download a file from URL to .tmp/media/."""
    ext = "mp4" if media_type == "video" else "jpg"
    filename = f"segment_{segment_index}.{ext}"
    local_path = f".tmp/media/{filename}"

    for attempt in range(3):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return local_path
        except Exception as e:
            print(f"   ⚠️  Download attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed to download media after 3 attempts: {url}")


def _simplify_keyword(keyword):
    """Simplify a keyword for broader search results."""
    kw_lower = keyword.lower()

    # Check category mappings
    for term, generic in CATEGORY_GENERICS.items():
        if term in kw_lower:
            return generic

    # Multi-word: try just the last word
    words = kw_lower.split()
    if len(words) > 1:
        return words[-1]

    return kw_lower


if __name__ == "__main__":
    keywords_path = ".tmp/keywords.json"
    if not os.path.exists(keywords_path):
        print("❌ No keywords found. Run extract_keywords.py first.")
        sys.exit(1)

    with open(keywords_path, "r", encoding="utf-8") as f:
        keywords_data = json.load(f)

    # Try to get audio duration if available
    audio_duration = 60.0
    audio_meta = ".tmp/audio_metadata.json"
    if os.path.exists(audio_meta):
        with open(audio_meta, "r") as f:
            audio_duration = json.load(f).get("duration", 60.0)

    result = download_media(keywords_data, audio_duration)

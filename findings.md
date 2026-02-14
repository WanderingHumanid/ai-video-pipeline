# 🔍 Findings & Research Log

**Project:** AI Video Pipeline  
**Created:** 2026-02-14  
**Purpose:** Document all research discoveries, API constraints, and technical learnings.

---

## 📚 Research Queue

### To Research:
- [ ] Pexels API - Rate limits, video formats, attribution requirements
- [ ] Edge-TTS - Voice options, language support, quality settings
- [ ] MoviePy + FFmpeg - Composition workflows, performance optimization
- [ ] YouTube Data API v3 - Upload quotas, OAuth2 flow, metadata requirements

---

## 🧩 Discoveries

### Pexels API ✅
- **Status:** Research Complete (2026-02-14)
- **Rate Limits:** 
  - Default: 200 requests/hour, 20,000 requests/month
  - Returns 429 status code when exceeded
  - Can request unlimited calls (free, requires attribution + eligibility)
- **Video Download Formats:**
  - Primary format: `.mp4` files
  - Video URLs often point to Vimeo CDN with auth tokens
  - Download endpoint: `https://www.pexels.com/video/{ID}/download`
  - Can retrieve up to 80 results per page (`per_page` parameter)
- **Attribution Requirements:**
  - Required format: "Photo/Video by [Name] on Pexels" with link
  - Minimum: "Powered by Pexels" text link
  - For unlimited API access: Must show attribution in app (requires proof)
- **Best Practices:**
  - Implement response caching (URLs are stable short-term)
  - Normalize search queries to leverage cache
  - Use pagination to retrieve more results per request

### Edge-TTS ✅
- **Status:** Research Complete (2026-02-14)
- **Quality:** Neural TTS from Microsoft Edge (high-quality, natural-sounding)
- **Key Features:**
  - No API key required (uses Microsoft's free service)
  - Works without Edge browser or Windows
  - Wide range of voices and languages
  - Customizable: rate, volume, pitch, speaking styles
- **Audio Format:**
  - Default output: MP3
  - Can generate subtitle files (SRT, VTT) alongside audio
  - Supports streaming with libraries like `pyaudio`
- **Available Voices:**
  - Use `edge-tts --list-voices` command to see all options
  - Voices have different genders, accents, and content categories
- **Limitations:**
  - Advanced SSML customization removed by Microsoft
  - Only single `<voice>` tag with single `<prosody>` tag allowed
- **Installation:** `pip install edge-tts`

### MoviePy + FFmpeg ✅
- **Status:** Research Complete (2026-02-14)
- **Critical Issue: Audio/Video Sync**
  - **Root Cause:** Duration mismatch between audio and video clips
  - **Solution:** Use `.set_duration()` on audio clip to match video duration exactly
  - **Variable Frame Rate (VFR) Warning:** Videos from mobile phones can cause desync
- **Best Practices:**
  1. Always match audio duration to total video duration
  2. Use constant frame rate (CFR) for output
  3. Verify audio file plays correctly before processing
  4. Use proper audio codec and bitrate settings
- **Workflow:**
  - MoviePy provides high-level Python API
  - FFmpeg handles low-level encoding/decoding
  - Set audio duration first, then composite video clips
- **Performance:** Rendering 1080p can be CPU-intensive (to be benchmarked)

### YouTube Data API v3 ✅
- **Status:** Research Complete (2026-02-14)
- **Quota Limits (CRITICAL):**
  - Default daily quota: 10,000 units (resets midnight PT)
  - **Video upload cost: 1,600 units** → Maximum 6 videos/day (10,000/1,600 = 6.25)
  - Video size/length/quality does NOT affect quota cost
  - Invalid requests also consume quota (minimum 1 unit)
- **Other Operation Costs:**
  - `videos.list`: 1 unit per video ID
  - `search.list`: ~100 units
  - Create/update resources: 50 units
  - Thumbnail upload: 50 units
- **OAuth2 Authentication:**
  - Required for uploading to user channels
  - Quota tied to Google Cloud project, NOT user account
  - All requests under same project share the quota pool
- **Quota Increase:**
  - Can request increase via Google Cloud Console (free)
  - Requires compliance audit with YouTube API ToS
  - Must justify increased quota needs
- **Python Integration:**
  - Use `google-api-python-client` library
  - Batching requests and caching can reduce quota usage

---

## ⚠️ Constraints

### Known Constraints:

1. **YouTube Upload Quota (CRITICAL)**
   - **Limitation:** Maximum 6 videos per day with default quota (1,600 units per upload, 10,000 daily limit)
   - **Impact:** Cannot run high-volume batch processing without quota increase
   - **Workaround:** Request quota increase from Google Cloud Console OR batch uploads across multiple days

2. **Pexels API Rate Limits**
   - **Limitation:** 200 requests/hour, 20,000/month (default free tier)
   - **Impact:** If downloading 10 videos per generation, max ~20 videos/hour
   - **Workaround:** Implement caching, normalize queries, request unlimited access (requires attribution)

3. **MoviePy Audio/Video Sync Risk**
   - **Limitation:** Duration mismatches cause silent videos or desync
   - **Impact:** Videos may export without audio if not handled correctly
   - **Mandatory Fix:** Always use `.set_duration()` to match audio to video timeline

4. **FFmpeg Dependency**
   - **Limitation:** Requires FFmpeg installed on system
   - **Impact:** Streamlit Cloud deployment needs `packages.txt` with `ffmpeg`
   - **Workaround:** Add `ffmpeg` to Streamlit apt packages or use ImageIO-FFmpeg

5. **Edge-TTS SSML Limitations**
   - **Limitation:** Advanced SSML features removed by Microsoft
   - **Impact:** Limited control over prosody/emotion beyond basic pitch/rate/volume
   - **Workaround:** Use built-in speaking styles and voice selection

---

## 💡 Optimization Ideas

*This section will track performance improvements and best practices discovered during development.*

### Ideas:
- None documented yet.

---

## 🔧 Troubleshooting Solutions

*This section will document errors encountered and their solutions (Self-Annealing Log).*

### Resolved Issues:
- None documented yet.

---

**Last Updated:** 2026-02-14T16:49:45+05:30

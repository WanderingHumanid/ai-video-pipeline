# 🧬 Project Constitution: Topic-to-YouTube Agentic System

**Project Type:** Autonomous Content Creation Pipeline  
**Last Updated:** 2026-02-14  
**Status:** Initialization Phase

---

## 📜 North Star

**Goal:** A zero-manual-effort "Topic-to-YouTube" agentic system that autonomously converts a user-provided topic into a high-retention YouTube video.

**Problem Solved:** Eliminate the bottleneck of traditional video editing by proving an autonomous agent can handle scriptwriting, asset sourcing, and technical rendering without human supervision.

---

## 🗂️ Data Schemas

### Input Schema
```json
{
  "topic": "string (user-provided topic/title)",
  "metadata": {
    "timestamp": "ISO 8601 datetime",
    "user_id": "optional string"
  }
}
```

**Example:**
```json
{
  "topic": "The Science Behind Black Holes",
  "metadata": {
    "timestamp": "2026-02-14T16:49:45+05:30",
    "user_id": null
  }
}
```

---

### Intermediate Data Structures

#### 1. Script Object
```json
{
  "topic": "string",
  "full_script": "string (complete narration)",
  "segments": [
    {
      "text": "string (sentence/paragraph)",
      "duration_estimate": "float (seconds)",
      "keywords": ["string", "string"]
    }
  ],
  "total_duration_estimate": "float (seconds)",
  "generated_at": "ISO 8601 datetime"
}
```

#### 2. Media Asset Object
```json
{
  "keyword": "string (search term)",
  "source": "pexels|ai-generated",
  "type": "video|image",
  "url": "string (download URL)",
  "local_path": "string (relative path in .tmp/media/)",
  "duration": "float (seconds, 0 for images)",
  "attribution": "string (photographer/videographer name)"
}
```

#### 3. Audio Object
```json
{
  "script": "string",
  "local_path": "string (.tmp/audio.mp3)",
  "duration": "float (seconds)",
  "voice": "string (TTS voice ID)",
  "generated_at": "ISO 8601 datetime"
}
```

#### 4. Composition Manifest
```json
{
  "audio_path": "string",
  "audio_duration": "float",
  "clips": [
    {
      "media_path": "string",
      "start_time": "float (seconds)",
      "duration": "float (seconds)",
      "type": "video|image"
    }
  ],
  "output_resolution": "1920x1080",
  "fps": 30
}
```

---

### Output Schema
```json
{
  "topic": "string",
  "video_path": "string (output/video_TIMESTAMP.mp4)",
  "file_size_mb": "float",
  "duration": "float (seconds)",
  "youtube_url": "string (optional, if uploaded)",
  "youtube_video_id": "string (optional)",
  "created_at": "ISO 8601 datetime",
  "status": "success|failed",
  "error": "string (if failed)"
}
```

**Example:**
```json
{
  "topic": "The Science Behind Black Holes",
  "video_path": "output/video_20260214164945.mp4",
  "file_size_mb": 45.3,
  "duration": 62.5,
  "youtube_url": "https://youtube.com/watch?v=ABC123XYZ",
  "youtube_video_id": "ABC123XYZ",
  "created_at": "2026-02-14T16:55:30+05:30",
  "status": "success",
  "error": null
}
```

---

## ⚖️ Behavioral Rules

### 1. Visual-Audio Sync (Logic Constraint)
- **Rule:** Visual clips MUST be timed to match the exact duration of the audio narration.
- **Implementation:** The composition engine must calculate total audio duration, then distribute media clips proportionally to fill the timeline without gaps or overruns.

### 2. Error Handling: Pexels Fallback
- **Rule:** If Pexels returns no results for a keyword:
  1. First Attempt: Simplify the keyword (remove adjectives, use root noun)
  2. Second Attempt: Use a generic fallback keyword ("nature", "abstract", "technology")
  3. Final Fallback: Generate an AI image using Antigravity's `generate_image` tool
- **Never Fail:** The system must ALWAYS produce a video, even with placeholder visuals.

### 3. Cleaning Rule (No Residue)
- **Rule:** After rendering the final `.mp4`, the system MUST delete:
  - All downloaded media in `.tmp/media/`
  - Generated audio file `.tmp/audio.mp3`
  - Any intermediate JSON manifests
- **Exception:** Keep the final `.mp4` in `output/` directory.

### 4. Security (GitHub/Streamlit Deployment)
- **Rule:** ALL API keys must be stored in `.env` and NEVER committed to version control.
- **Required Files:**
  - `.env` (ignored by git)
  - `.env.example` (template with placeholder values)
  - `.gitignore` (must exclude `.env`, `.tmp/`, `output/`)

### 5. Deterministic Behavior
- **Rule:** All business logic (keyword extraction, duration calculation, fallback logic) must be in Python scripts under `tools/`, NOT in LLM reasoning.
- **LLM Role:** Only for creative tasks (scriptwriting, keyword ideation). Never for control flow.

---

## 🏗️ Architectural Invariants

### File Structure
```
ai-video-pipeline/
├── gemini.md              # THIS FILE - Project Constitution
├── task_plan.md           # Blueprint & Phases
├── findings.md            # Research & Discoveries
├── progress.md            # Execution Log
├── .env                   # API Keys (GITIGNORED)
├── .env.example           # Public Template
├── .gitignore             # Security Exclusions
├── architecture/          # Layer 1: SOPs
│   ├── scriptwriting.md
│   ├── keyword_extraction.md
│   ├── media_sourcing.md
│   ├── audio_generation.md
│   ├── video_composition.md
│   └── youtube_upload.md
├── tools/                 # Layer 3: Python Scripts
│   ├── generate_script.py
│   ├── extract_keywords.py
│   ├── download_media.py
│   ├── generate_audio.py
│   ├── compose_video.py
│   ├── upload_youtube.py
│   └── cleanup.py
├── .tmp/                  # Ephemeral (GITIGNORED)
│   ├── media/
│   └── audio.mp3
├── output/                # Final Videos (GITIGNORED)
└── README.md              # Public Documentation
```

### Technology Stack
- **LLM:** Gemini 1.5 Flash (via Antigravity native integration)
- **TTS:** Edge-TTS (Python library)
- **Media:** Pexels API (stock video/images)
- **Rendering:** FFmpeg + MoviePy
- **Upload:** YouTube Data API v3
- **Deployment:** Streamlit + GitHub

### Dependencies (requirements.txt)
```
edge-tts
moviepy
requests
google-auth
google-auth-oauthlib
google-auth-httplib2
google-api-python-client
python-dotenv
streamlit
```

---

## 🔐 Environment Variables (.env)

```bash
# Pexels API
PEXELS_API_KEY=your_pexels_api_key_here

# YouTube Data API v3
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token

# Optional: Gemini API (if using external calls)
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## 📊 Success Criteria

1. ✅ User provides a topic string
2. ✅ System generates a complete video `.mp4` in `output/`
3. ✅ Video duration matches audio duration (±0.5 seconds tolerance)
4. ✅ All visuals are relevant to the script keywords
5. ✅ YouTube upload succeeds and returns a public URL
6. ✅ No temporary files remain after execution
7. ✅ System is deployable on GitHub without leaking API keys
8. ✅ Streamlit UI allows topic input and displays video preview

---

## 🛡️ Maintenance Log

*This section will be updated during the Self-Annealing process when errors are discovered and fixed.*

### Version History
- **v0.1.0** (2026-02-14): Initial schema definition and project setup

---

**🔒 This document is LAW. All code must conform to these schemas and rules.**

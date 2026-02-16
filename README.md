# 🎥 AI Video Pipeline

An automated pipeline that generates faceless videos from a single text prompt. It handles everything — scriptwriting, voiceover, stock footage, subtitles, thumbnail generation, and optional YouTube upload.

**🌐 Live Demo**: [ai-video-pipeline.streamlit.app](https://ai-video-pipeline.streamlit.app)

## ✨ Features

- **AI Script Generation** — Uses **Groq (Llama 3.1)** to write engaging, segment-based scripts with visual cues.
- **Natural Voiceovers** — Powered by **Edge TTS** with multiple voice options (American, British, Male, Female).
- **Stock Footage** — Automatically fetches relevant videos and images from the **Pexels API** with smart fallback logic.
- **Video Composition** — Stitches everything together with **MoviePy** and **FFmpeg**, including crossfade transitions and aspect-ratio-aware resizing.
- **Word-Level Subtitles** — Generates SRT files with precise timing. Can be burned into the video or uploaded as YouTube closed captions.
- **Thumbnail Generation** — Creates stylized thumbnails using media assets from the video.
- **YouTube Upload** — Uploads the video, captions (SRT), and thumbnail directly to your channel *(local only)*.
- **Dual Interface**:
  - **Streamlit Web App** — Full GUI with voice selection, resolution picker, script review/editing, and video preview.
  - **CLI** — Command-line interface for quick generation.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and in PATH

### Installation
```bash
git clone https://github.com/WanderingHumanid/ai-video-pipeline.git
cd ai-video-pipeline
pip install -r requirements.txt
```

### API Keys
Copy the example env file and fill in your keys:
```bash
cp .env.example .env
```

**Required keys:**
| Key | Source | Free? |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | ✅ Yes |
| `PEXELS_API_KEY` | [pexels.com/api](https://www.pexels.com/api/) | ✅ Yes |

**Optional (for YouTube upload):**
| Key | Source |
|---|---|
| `YOUTUBE_CLIENT_ID` | Google Cloud Console → OAuth 2.0 |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 |
| `YOUTUBE_REFRESH_TOKEN` | Generated via OAuth flow |

## 🖥️ Usage

### Streamlit App (Recommended)
```bash
streamlit run streamlit_app.py
```
- Enter a topic (e.g., "The Future of AI")
- Choose voice, resolution (480p / 720p / 1080p), and duration (30s–2min)
- Review and edit the AI-generated script before rendering
- Preview, download, or upload the video directly

### Command Line
```bash
python main.py "The Future of Space Travel" --duration 60 --voice en-US-AriaNeural
```
Add `--skip-upload` to generate without uploading, or `--resolution 1080` for higher quality.

## 📂 Project Structure
```
├── main.py                  # CLI pipeline orchestrator
├── streamlit_app.py         # Streamlit web interface
├── tools/
│   ├── generate_script.py   # AI script generation (Groq)
│   ├── extract_keywords.py  # Visual keyword extraction
│   ├── generate_audio.py    # Voice synthesis (Edge TTS)
│   ├── download_media.py    # Stock footage (Pexels API)
│   ├── compose_video.py     # Video rendering (MoviePy + FFmpeg)
│   ├── generate_thumbnail.py# Thumbnail creation (Pillow)
│   ├── upload_youtube.py    # YouTube upload + captions
│   └── cleanup.py           # Temp file cleanup
├── .env.example             # API key template
├── requirements.txt         # Python dependencies
└── packages.txt             # System dependencies (FFmpeg)
```

## ☁️ Deployment (Streamlit Cloud)

The app is deployed at [ai-video-pipeline.streamlit.app](https://ai-video-pipeline.streamlit.app).

> **Note**: YouTube upload does **not** work on Streamlit Cloud due to Google's OAuth restrictions requiring a local browser redirect. Use the cloud version to generate and download videos, then upload manually.

## 🛠️ Tech Stack

| Component | Tool |
|---|---|
| Script Generation | Groq (Llama 3.1) |
| Voice Synthesis | Edge TTS |
| Stock Footage | Pexels API |
| Video Composition | MoviePy + FFmpeg |
| Thumbnails | Pillow |
| Subtitles | SRT generation + FFmpeg burn-in |
| Web Interface | Streamlit |
| YouTube Upload | Google YouTube Data API v3 |

## 📄 License

MIT License. Free to use and modify.

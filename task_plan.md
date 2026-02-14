# 📋 Task Plan: Topic-to-YouTube Agentic System

**Project:** AI Video Pipeline  
**Protocol:** B.L.A.S.T. (Blueprint, Link, Architect, Stylize, Trigger)  
**Architecture:** A.N.T. (3-Layer: Architecture → Navigation → Tools)  
**Created:** 2026-02-14  

---

## 🎯 Discovery Questions (ANSWERED ✅)

### 1. North Star: What is the singular desired outcome?
**Answer:** A zero-manual-effort "Topic-to-YouTube" Agentic System that autonomously converts a topic string into a production-ready YouTube video.

### 2. Integrations: Which external services do we need?
**Answer:**
- ✅ **LLM:** Gemini 1.5 Flash (Antigravity native)
- ✅ **TTS:** Edge-TTS (Python library)
- ✅ **Media:** Pexels API (stock video/images)
- ✅ **Rendering:** FFmpeg + MoviePy
- ✅ **Upload:** YouTube Data API v3
- **Status:** All API keys are ready. Security: `.env` + `.gitignore` for GitHub/Streamlit deployment.

### 3. Source of Truth: Where does the primary data live?
**Answer:**
- **Input:** User-provided topic string
- **State:** `findings.md` and `task_plan.md` (living documents)
- **Intermediates:** `.tmp/` folder containing:
  - `script.txt` (generated script)
  - `audio.mp3` (TTS output)
  - `media/` (Pexels downloads)

### 4. Delivery Payload: How and where should the final result be delivered?
**Answer:**
- 🎯 **Primary:** Production-ready `.mp4` in `output/` directory
- 📹 **Evidence:** Antigravity Walkthrough + Browser Recording
- 🌐 **Social:** Live YouTube URL (automated upload)

### 5. Behavioral Rules: How should the system "act"?
**Answer:**
- ⏱️ **Visual-Audio Sync:** Clips must match audio duration
- 🔄 **Error Handling:** Pexels fallback → simplified keyword → AI-generated image
- 🧹 **Cleaning Rule:** Delete all `.tmp/` files after rendering
- 🔐 **Security:** No API keys in GitHub; use `.env`

---

## 📅 Phase Breakdown

### ✅ Protocol 0: Initialization (IN PROGRESS)
- [x] Ask Discovery Questions
- [/] Create `gemini.md` (Project Constitution)
- [/] Create `task_plan.md` (this file)
- [ ] Create `findings.md` (research log)
- [ ] Create `progress.md` (execution log)
- [ ] Create `.env.example` template
- [ ] Create `.gitignore`
- [ ] **HALT POINT:** User approval of Blueprint

---

### 🔵 Phase 1: B - Blueprint (Vision & Logic)
**Goal:** Define the complete system logic and research dependencies.

#### Checklist:
- [ ] Research Pexels API (rate limits, video formats, attribution requirements)
- [ ] Research Edge-TTS (available voices, language support, output quality)
- [ ] Research MoviePy + FFmpeg (composition workflows, performance)
- [ ] Research YouTube Data API v3 (upload quotas, authentication flow)
- [ ] Document findings in `findings.md`
- [ ] Create `architecture/` SOPs:
  - [ ] `scriptwriting.md` - LLM prompt engineering for scripts
  - [ ] `keyword_extraction.md` - Keyword extraction algorithm
  - [ ] `media_sourcing.md` - Pexels search + fallback logic
  - [ ] `audio_generation.md` - Edge-TTS workflow
  - [ ] `video_composition.md` - FFmpeg + MoviePy rendering
  - [ ] `youtube_upload.md` - OAuth2 + upload automation
- [ ] **Deliverable:** Complete Architecture SOPs

---

### 🟢 Phase 2: L - Link (Connectivity)
**Goal:** Verify all external services are reachable and functional.

#### Checklist:
- [ ] Install dependencies (`requirements.txt`)
- [ ] Verify Gemini 1.5 Flash (test script generation)
- [ ] Test Edge-TTS installation (generate sample audio)
- [ ] Test Pexels API (search for "ocean", download 1 video)
- [ ] Verify FFmpeg installation (`ffmpeg -version`)
- [ ] Test YouTube API authentication (OAuth2 flow)
- [ ] Create handshake scripts in `tools/`:
  - [ ] `test_gemini.py`
  - [ ] `test_edgetts.py`
  - [ ] `test_pexels.py`
  - [ ] `test_ffmpeg.py`
  - [ ] `test_youtube.py`
- [ ] **Deliverable:** All green lights on connectivity tests

---

### 🟡 Phase 3: A - Architect (The 3-Layer Build)
**Goal:** Build the deterministic automation system.

#### Layer 1: Architecture (SOPs) ✅
Already defined in Phase 1.

#### Layer 2: Navigation (Decision Layer)
- [ ] Create `main.py` orchestration script:
  1. Accept topic input
  2. Call `tools/generate_script.py`
  3. Call `tools/extract_keywords.py`
  4. Call `tools/download_media.py`
  5. Call `tools/generate_audio.py`
  6. Call `tools/compose_video.py`
  7. Call `tools/upload_youtube.py`
  8. Call `tools/cleanup.py`
  9. Return output manifest

#### Layer 3: Tools (Execution Scripts)
- [ ] `tools/generate_script.py`
  - Input: Topic string
  - Output: Script JSON (see `gemini.md` schema)
- [ ] `tools/extract_keywords.py`
  - Input: Script JSON
  - Output: Keyword list per segment
- [ ] `tools/download_media.py`
  - Input: Keyword list
  - Output: Media Asset JSON + downloaded files in `.tmp/media/`
- [ ] `tools/generate_audio.py`
  - Input: Script text
  - Output: Audio Object JSON + `.tmp/audio.mp3`
- [ ] `tools/compose_video.py`
  - Input: Composition Manifest JSON
  - Output: Final `.mp4` in `output/`
- [ ] `tools/upload_youtube.py`
  - Input: Video path + metadata
  - Output: YouTube URL + video ID
- [ ] `tools/cleanup.py`
  - Input: None
  - Output: Deletes `.tmp/` contents

- [ ] **Deliverable:** All tools functional and tested independently

---

### 🟣 Phase 4: S - Stylize (Refinement & UI)
**Goal:** Polish the system and create user interfaces.

#### Checklist:
- [ ] Test full pipeline with 3 diverse topics:
  1. Science (e.g., "Black Holes")
  2. Technology (e.g., "Quantum Computing")
  3. Lifestyle (e.g., "Morning Routines")
- [ ] Optimize video quality (resolution, bitrate, codec)
- [ ] Add progress indicators (CLI output or Streamlit progress bar)
- [ ] Create Streamlit web interface:
  - Input: Text box for topic
  - Output: Video preview + download button + YouTube link
- [ ] Add error logging to `progress.md`
- [ ] **Deliverable:** Polished, production-ready system

---

### 🔴 Phase 5: T - Trigger (Deployment)
**Goal:** Deploy to GitHub and Streamlit Cloud.

#### Checklist:
- [ ] Security audit:
  - [ ] Verify `.env` is in `.gitignore`
  - [ ] Scan for hardcoded API keys
  - [ ] Test `.env.example` template
- [ ] Create comprehensive `README.md`:
  - Project overview
  - Installation instructions
  - Configuration guide (`.env` setup)
  - Usage examples
  - Architecture diagram
- [ ] Prepare GitHub repository:
  - [ ] Initialize git
  - [ ] Create `.gitignore`
  - [ ] First commit
  - [ ] Push to GitHub
- [ ] Deploy to Streamlit Cloud:
  - [ ] Configure secrets (Streamlit Secrets Manager)
  - [ ] Test deployment
  - [ ] Share public URL
- [ ] Create Antigravity Walkthrough artifact
- [ ] Record browser demo of successful video generation/upload
- [ ] **Deliverable:** Live system accessible via public URL

---

## 🚦 Current Status

**Phase:** Protocol 0 (Initialization)  
**Next Action:** Complete initialization files, then proceed to Blueprint research.  
**Blockers:** None (API keys ready)  

---

## 📌 Notes

- **Self-Annealing Rule:** If any test fails in Phase 2 (Link), update the corresponding SOP in `architecture/` before retrying.
- **No Code in `tools/` Until:** Blueprint is approved and data schemas are finalized in `gemini.md`.
- **Deployment Priority:** Security > Functionality. Never compromise API key protection.

---

**This is the living Blueprint. Updates will be reflected in `progress.md` as work progresses.**

import streamlit as st
import os
import sys
import json
import time
import datetime
from dotenv import load_dotenv

# Add project root to path for direct imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

st.set_page_config(
    page_title="AI Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #161B22;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #30363D;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Voice configuration ─────────────────────────────────────────────────────

VOICES = {
    "en-US-AriaNeural":        ("🇺🇸 Aria — Female, American",   "static/voices/aria.mp3"),
    "en-US-ChristopherNeural": ("🇺🇸 Christopher — Male, American", "static/voices/christopher.mp3"),
    "en-GB-SoniaNeural":       ("🇬🇧 Sonia — Female, British",   "static/voices/sonia.mp3"),
    "en-GB-RyanNeural":        ("🇬🇧 Ryan — Male, British",      "static/voices/ryan.mp3"),
}

# ── Resolution presets ──────────────────────────────────────────────────────

RESOLUTIONS = {
    "480p (SD) — ~2-3 min":      (854, 480),
    "720p (HD) — ~4-6 min":      (1280, 720),
    "1080p (Full HD) — ~8-12 min": (1920, 1080),
}

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    pexels_api = os.getenv("PEXELS_API_KEY")
    groq_api = os.getenv("GROQ_API_KEY")

    if pexels_api:
        st.success("✅ Pexels API Key")
    else:
        st.error("❌ Pexels API Key missing")

    if groq_api:
        st.success("✅ Groq API Key")
    else:
        st.error("❌ Groq API Key missing")

    st.markdown("---")
    st.caption("💡 Ensure `.env` is configured before running.")

# ── Main Page ────────────────────────────────────────────────────────────────

st.title("🎬 AI Video Generator")
st.caption("Zero-Shot Text-to-Video Pipeline")
st.markdown("---")

topic = st.text_input(
    "📝 Enter a topic for your video",
    placeholder="e.g., The Future of AI, History of Rome, Quantum Physics..."
)

# ── Voice selector ───────────────────────────────────────────────────────
with st.expander("🎙️ Voice Selection"):
    voice_id = st.radio(
        "Choose a narration voice:",
        options=list(VOICES.keys()),
        format_func=lambda k: VOICES[k][0],
        horizontal=True,
        label_visibility="collapsed",
    )

    preview_path = VOICES[voice_id][1]
    if os.path.exists(preview_path):
        st.audio(preview_path, format="audio/mp3")
    st.caption(f"Selected: **{VOICES[voice_id][0]}**")

# ── Resolution selector ─────────────────────────────────────────────────
with st.expander("📐 Resolution"):
    resolution_label = st.radio(
        "Choose output resolution:",
        options=list(RESOLUTIONS.keys()),
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_resolution = RESOLUTIONS[resolution_label]
    st.caption(f"Selected: **{selected_resolution[0]}×{selected_resolution[1]}** — estimated render time shown above")

# ── Subtitle toggle ─────────────────────────────────────────────────────
enable_subtitles = st.toggle("🔤 Enable Subtitles", value=True)

# ── Generate ─────────────────────────────────────────────────────────────
can_generate = bool(topic and pexels_api and groq_api)
generate_btn = st.button("🚀 Generate Video", type="primary", disabled=not can_generate)

if generate_btn:
    progress = st.progress(0, text="Starting pipeline...")
    status = st.empty()
    start_time = time.time()

    try:
        # ── Step 1: Script Generation ────────────────────────────────────
        progress.progress(5, text="📝 Generating script...")
        status.info("📝 Generating script with Groq (Llama 3.1)...")

        from tools.generate_script import generate_script
        script_data = generate_script(topic)

        seg_count = len(script_data["segments"])
        est_dur = script_data["total_duration_estimate"]
        status.success(f"✅ Script: {seg_count} segments, ~{est_dur:.0f}s estimated")

        # ── Step 2: Keyword Extraction ───────────────────────────────────
        progress.progress(15, text="🔍 Extracting keywords...")
        status.info("🔍 Extracting visual keywords...")

        from tools.extract_keywords import extract_keywords_from_segments
        keywords_data = extract_keywords_from_segments(script_data)

        kw_count = len(keywords_data["all_keywords"])
        status.success(f"✅ Keywords: {kw_count} unique visual keywords extracted")

        # ── Step 3: Audio Generation ─────────────────────────────────────
        progress.progress(25, text="🗣️ Synthesizing voiceover...")
        status.info(f"🗣️ Generating voiceover ({VOICES[voice_id][0]})...")

        from tools.generate_audio import generate_audio
        audio_data = generate_audio(script_data, voice=voice_id)

        audio_dur = audio_data["duration"]
        status.success(f"✅ Audio: {audio_dur:.1f}s voiceover generated")

        # ── Step 4: Media Download ───────────────────────────────────────
        progress.progress(40, text="⬇️ Downloading media...")
        status.info("⬇️ Downloading stock footage from Pexels...")

        from tools.download_media import download_media
        media_data = download_media(keywords_data, audio_duration=audio_data["duration"])

        sourced = sum(1 for a in media_data["media_assets"] if a["source"] != "none")
        total = len(media_data["media_assets"])
        status.success(f"✅ Media: {sourced}/{total} segments sourced")

        # ── Step 5: Video Composition ────────────────────────────────────
        progress.progress(65, text="🎬 Rendering final video...")
        status.info("🎬 Rendering video — this may take a few minutes...")

        from tools.compose_video import compose_video
        video_data = compose_video(
            audio_metadata=audio_data,
            media_assets=media_data["media_assets"],
            resolution=selected_resolution,
            subtitles=enable_subtitles,
        )

        # ── Done! ────────────────────────────────────────────────────────
        elapsed = time.time() - start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)

        progress.progress(100, text="✅ Complete!")
        status.success(
            f"🎉 Video generated in {mins}m {secs}s! "
            f"({video_data['file_size_mb']:.1f} MB, {video_data['duration']:.1f}s)"
        )

        # Store generation data in session state for post-gen subtitle toggling
        st.session_state["last_video_data"] = video_data
        st.session_state["last_audio_data"] = audio_data

        # Show video
        video_path = video_data["video_path"]
        if os.path.exists(video_path):
            st.video(video_path)
            with open(video_path, "rb") as vf:
                st.download_button(
                    "💾 Download Video",
                    data=vf,
                    file_name=os.path.basename(video_path),
                    mime="video/mp4"
                )

    except Exception as e:
        progress.empty()
        elapsed = time.time() - start_time
        st.error(f"❌ Pipeline failed after {elapsed:.0f}s: {e}")
        # Show traceback in expander for debugging
        import traceback
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())

# ── Post-generation subtitle toggle ──────────────────────────────────────

if "last_video_data" in st.session_state and "last_audio_data" in st.session_state:
    vd = st.session_state["last_video_data"]
    raw_path = vd.get("raw_path")
    has_subs = vd.get("subtitles_enabled", True)

    if raw_path and os.path.exists(raw_path):
        st.markdown("---")
        st.markdown("#### 🔄 Post-Generation Subtitle Toggle")

        if has_subs:
            toggle_label = "🔇 Re-render **without** subtitles"
        else:
            toggle_label = "🔤 Re-render **with** subtitles"

        if st.button(toggle_label):
            with st.spinner("Re-rendering subtitles (~10s)..."):
                import shutil
                # Generate new output path
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                new_output = os.path.join(os.path.dirname(raw_path), f"video_{timestamp}.mp4")

                if has_subs:
                    # Remove subtitles: just copy the raw file
                    shutil.copy2(raw_path, new_output)
                    new_subs = False
                else:
                    # Add subtitles
                    from tools.compose_video import burn_subtitles_only
                    burn_subtitles_only(raw_path, new_output, st.session_state["last_audio_data"])
                    new_subs = True

                # Update session state
                st.session_state["last_video_data"]["video_path"] = new_output
                st.session_state["last_video_data"]["subtitles_enabled"] = new_subs
                st.session_state["last_video_data"]["file_size_mb"] = round(
                    os.path.getsize(new_output) / (1024 * 1024), 2
                )

            st.success(f"✅ Re-rendered {'with' if new_subs else 'without'} subtitles!")
            st.video(new_output)
            with open(new_output, "rb") as vf:
                st.download_button(
                    "💾 Download Re-rendered Video",
                    data=vf,
                    file_name=os.path.basename(new_output),
                    mime="video/mp4"
                )

st.markdown("---")
st.caption("Powered by Groq (Llama 3.1) · Pexels · Edge-TTS · MoviePy")

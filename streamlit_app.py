import streamlit as st
import os
import subprocess
import json
import time
from dotenv import load_dotenv

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

# ── Helper ──────────────────────────────────────────────────────────────────

TIMEOUT_PER_STEP = {
    "Script Generation": 90,
    "Keyword Extraction": 60,
    "Media Download": 120,
    "Audio Generation": 120,
    "Video Composition": 180,
}

def run_pipeline_step(command, args, step_name):
    """Run a pipeline step as a subprocess with a timeout."""
    cmd = command.split() + args
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    timeout = TIMEOUT_PER_STEP.get(step_name, 120)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        env=env
    )

    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError(
            f"{step_name} timed out after {timeout}s. "
            f"This usually means the API is rate-limited. Try again in a minute."
        )

    if process.returncode != 0:
        raise RuntimeError(f"{step_name} failed:\n{stderr}\n{stdout}")

    return stdout


# Voice configuration (labels only — previews are in the expander)
VOICES = {
    "en-US-AriaNeural":        ("🇺🇸 Aria — Female, American",   "static/voices/aria.mp3"),
    "en-US-ChristopherNeural": ("🇺🇸 Christopher — Male, American", "static/voices/christopher.mp3"),
    "en-GB-SoniaNeural":       ("🇬🇧 Sonia — Female, British",   "static/voices/sonia.mp3"),
    "en-GB-RyanNeural":        ("🇬🇧 Ryan — Male, British",      "static/voices/ryan.mp3"),
}

# ── Sidebar (minimal) ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuration")

    pexels_api = os.getenv("PEXELS_API_KEY")
    gemini_api = os.getenv("GEMINI_API_KEY")

    if pexels_api:
        st.success("✅ Pexels API Key")
    else:
        st.error("❌ Pexels API Key missing")

    if gemini_api:
        st.success("✅ Gemini API Key")
    else:
        st.error("❌ Gemini API Key missing")

    st.markdown("---")
    st.caption("💡 Ensure `.env` is configured before running.")

# ── Main Page ───────────────────────────────────────────────────────────────

st.title("🎬 AI Video Generator")
st.caption("Zero-Shot Text-to-Video Pipeline")
st.markdown("---")

col1, col2 = st.columns([3, 1])

with col1:
    topic = st.text_input(
        "📝 Enter a topic for your video",
        placeholder="e.g., The Future of AI, History of Rome, Quantum Physics..."
    )

    # ── Voice selector: simple radio + preview ──────────────────────────────
    with st.expander("🎙️ Voice Selection"):

        voice_id = st.radio(
            "Choose a narration voice:",
            options=list(VOICES.keys()),
            format_func=lambda k: VOICES[k][0],
            horizontal=True,
            label_visibility="collapsed",
        )

        # Show preview for the selected voice
        preview_path = VOICES[voice_id][1]
        if os.path.exists(preview_path):
            st.audio(preview_path, format="audio/mp3")
        st.caption(f"Selected: **{VOICES[voice_id][0]}**")

    # ── Generate ────────────────────────────────────────────────────────────
    can_generate = bool(topic and pexels_api and gemini_api)
    generate_btn = st.button("🚀 Generate Video", type="primary", disabled=not can_generate)

    if generate_btn:
        progress = st.progress(0, text="Starting pipeline...")
        status = st.empty()

        steps = [
            (10,  "📝 Generating script...",       "python tools/generate_script.py", [topic],    "Script Generation"),
            (25,  "🔍 Extracting keywords...",     "python tools/extract_keywords.py", [],        "Keyword Extraction"),
            (40,  "⬇️ Downloading media...",       "python tools/download_media.py",   [],        "Media Download"),
            (60,  "🗣️ Synthesizing voiceover...",  "python tools/generate_audio.py",   [voice_id], "Audio Generation"),
            (85,  "🎬 Rendering final video...",    "python tools/compose_video.py",    [],        "Video Composition"),
        ]

        try:
            for pct, label, cmd, args, name in steps:
                progress.progress(pct, text=label)
                status.info(label)
                run_pipeline_step(cmd, args, name)

            progress.progress(100, text="✅ Complete!")
            status.success("🎉 Video generated successfully!")

            # Find latest video
            out = "output"
            if os.path.exists(out):
                mp4s = [f for f in os.listdir(out)
                        if f.endswith(".mp4") and not f.startswith("raw_")]
                if mp4s:
                    latest = max(
                        [os.path.join(out, f) for f in mp4s],
                        key=os.path.getctime
                    )
                    st.video(latest)
                    with open(latest, "rb") as vf:
                        st.download_button(
                            "💾 Download Video",
                            data=vf,
                            file_name=os.path.basename(latest),
                            mime="video/mp4"
                        )

        except Exception as e:
            progress.empty()
            st.error(f"❌ {e}")

with col2:
    st.markdown("#### 📂 Recent Videos")
    out = "output"
    if os.path.exists(out):
        mp4s = sorted(
            [f for f in os.listdir(out) if f.endswith(".mp4") and not f.startswith("raw_")],
            key=lambda f: os.path.getctime(os.path.join(out, f)),
            reverse=True
        )[:5]
        if mp4s:
            for v in mp4s:
                sz = os.path.getsize(os.path.join(out, v)) / (1024*1024)
                st.text(f"🎞️ {v}  ({sz:.1f} MB)")
        else:
            st.caption("No videos yet.")
    else:
        st.caption("No videos yet.")

st.markdown("---")
st.caption("Powered by Gemini · Pexels · Edge-TTS · MoviePy")

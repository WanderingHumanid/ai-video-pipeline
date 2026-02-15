import streamlit as st
import os
import sys
import json
import time
import datetime
from dotenv import load_dotenv

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

VOICES = {
    "en-US-AriaNeural":        ("🇺🇸 Aria — Female, American",   "static/voices/aria.mp3"),
    "en-US-ChristopherNeural": ("🇺🇸 Christopher — Male, American", "static/voices/christopher.mp3"),
    "en-GB-SoniaNeural":       ("🇬🇧 Sonia — Female, British",   "static/voices/sonia.mp3"),
    "en-GB-RyanNeural":        ("🇬🇧 Ryan — Male, British",      "static/voices/ryan.mp3"),
}

RESOLUTIONS = {
    "480p (SD) — ~2-3 min":      (854, 480),
    "720p (HD) — ~4-6 min":      (1280, 720),
    "1080p (Full HD) — ~8-12 min": (1920, 1080),
}

DURATION_OPTIONS = {
    "30s — Quick short":    30,
    "60s — Standard":       60,
    "90s — Extended":       90,
    "2min — In-depth":      120,
}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")

    pexels_api = os.getenv("PEXELS_API_KEY")
    groq_api = os.getenv("GROQ_API_KEY")
    
    # User-uploaded secrets for custom channel upload
    st.subheader("YouTube Upload")
    uploaded_secrets = st.file_uploader(
        "Upload client_secrets.json", 
        type="json", 
        help="To upload to YOUR channel, upload your OAuth web client secrets here. Otherwise, uploads are disabled or use default env keys."
    )
    
    user_secrets_path = None
    if uploaded_secrets is not None:
        os.makedirs(".tmp", exist_ok=True)
        user_secrets_path = os.path.abspath(".tmp/user_client_secrets.json")
        with open(user_secrets_path, "wb") as f:
            f.write(uploaded_secrets.getbuffer())
        st.success("✅ Custom credentials loaded")

    # API Status Checks
    if pexels_api:
        st.success("✅ Pexels API Key")
    else:
        st.error("❌ Pexels API Key missing")

    if groq_api:
        st.success("✅ Groq API Key")
    else:
        st.error("❌ Groq API Key missing")
        
    # Check if we have ANY valid YouTube auth method
    has_youtube_env = bool(os.getenv("YOUTUBE_CLIENT_ID"))
    has_default_secrets = os.path.exists("client_secrets.json")
    can_upload = bool(user_secrets_path or has_youtube_env or has_default_secrets)
    
    if can_upload:
        st.success(f"✅ YouTube Upload Ready ({'Custom' if user_secrets_path else 'Env/Default'})")
    else:
        st.warning("⚠️ YouTube Upload disabled")

    st.markdown("---")
    st.caption("💡 Ensure `.env` is configurable if not using custom secrets.")


# --- Main Content ---
st.title("🎬 AI Video Generator")
st.markdown("---")

topic = st.text_input(
    "📝 Enter a topic for your video",
    placeholder="Give a simple prompt. The AI will generate the script for you."
)

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

with st.expander("📐 Resolution"):
    resolution_label = st.radio(
        "Choose output resolution:",
        options=list(RESOLUTIONS.keys()),
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )
    selected_resolution = RESOLUTIONS[resolution_label]
    st.caption(f"Selected: **{selected_resolution[0]}×{selected_resolution[1]}**")

with st.expander("⏱️ Video Duration"):
    duration_label = st.radio(
        "Choose target duration:",
        options=list(DURATION_OPTIONS.keys()),
        index=1,
        horizontal=True,
        label_visibility="collapsed",
    )
    target_duration = DURATION_OPTIONS[duration_label]
    st.caption(f"Selected: **{target_duration}s**")

enable_subtitles = st.toggle("🔤 Enable Subtitles (Burned in)", value=True)
review_script = st.toggle("✏️ Review & edit script before generating", value=False)

can_generate = bool(topic and pexels_api and groq_api)


# --- Pipeline Logic ---

def _run_pipeline_after_script(script_data):
    """Run the pipeline from keywords onward."""
    progress = st.session_state.get("_progress")
    status = st.session_state.get("_status")
    start_time = st.session_state.get("_start_time", time.time())

    try:
        progress.progress(15, text="🔍 Extracting keywords...")
        status.info("🔍 Extracting visual keywords...")

        from tools.extract_keywords import extract_keywords_from_segments
        keywords_data = extract_keywords_from_segments(script_data)

        kw_count = len(keywords_data["all_keywords"])
        status.success(f"✅ Keywords: {kw_count} unique visual keywords extracted")

        progress.progress(25, text="🗣️ Synthesizing voiceover...")
        status.info(f"🗣️ Generating voiceover ({VOICES[voice_id][0]})...")

        from tools.generate_audio import generate_audio
        audio_data = generate_audio(script_data, voice=voice_id)

        audio_dur = audio_data["duration"]
        status.success(f"✅ Audio: {audio_dur:.1f}s voiceover generated")

        progress.progress(40, text="⬇️ Downloading media...")
        status.info("⬇️ Downloading stock footage from Pexels...")

        from tools.download_media import download_media
        media_data = download_media(keywords_data, audio_duration=audio_data["duration"])

        sourced = sum(1 for a in media_data["media_assets"] if a["source"] != "none")
        total = len(media_data["media_assets"])
        status.success(f"✅ Media: {sourced}/{total} segments sourced")

        progress.progress(65, text="🎬 Rendering final video...")
        status.info("🎬 Rendering video — this may take a few minutes...")

        from tools.compose_video import compose_video
        video_data = compose_video(
            audio_metadata=audio_data,
            media_assets=media_data["media_assets"],
            resolution=selected_resolution,
            subtitles=enable_subtitles,
        )

        elapsed = time.time() - start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)

        progress.progress(100, text="✅ Complete!")
        status.success(
            f"🎉 Video generated in {mins}m {secs}s! "
            f"({video_data['file_size_mb']:.1f} MB, {video_data['duration']:.1f}s)"
        )

        # Update Session State
        st.session_state["last_video_data"] = video_data
        st.session_state["last_audio_data"] = audio_data
        st.session_state["last_media_assets"] = media_data["media_assets"]
        st.session_state["script_topic"] = topic

    except Exception as e:
        progress.empty()
        elapsed = time.time() - start_time
        st.error(f"❌ Pipeline failed after {elapsed:.0f}s: {e}")
        import traceback
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())


generate_btn = st.button("🚀 Generate Video", type="primary", disabled=not can_generate)

if generate_btn:
    progress = st.progress(0, text="Starting pipeline...")
    status = st.empty()
    start_time = time.time()

    st.session_state["_progress"] = progress
    st.session_state["_status"] = status
    st.session_state["_start_time"] = start_time
    # Clear previous results
    for key in ["last_video_data", "last_audio_data", "last_media_assets", "last_thumbnail"]:
        if key in st.session_state:
            del st.session_state[key]

    progress.progress(5, text="📝 Generating script...")
    status.info("📝 Generating script...")

    from tools.generate_script import generate_script
    script_data = generate_script(topic, target_duration=target_duration)

    seg_count = len(script_data["segments"])
    est_dur = script_data["total_duration_estimate"]
    status.success(f"✅ Script: {seg_count} segments, ~{est_dur:.0f}s estimated")

    if review_script:
        st.session_state["pending_script"] = script_data
        st.session_state["script_topic"] = topic
        st.rerun()
    else:
        _run_pipeline_after_script(script_data)


# --- Script Review UI ---
if "pending_script" in st.session_state:
    script_data = st.session_state["pending_script"]
    st.markdown("---")
    st.subheader("✏️ Review & Edit Script")
    
    edited_segments = []
    for i, seg in enumerate(script_data["segments"]):
        with st.expander(f"Segment {i + 1} — ~{seg.get('duration_estimate', '?')}s", expanded=True):
            text = st.text_area(f"Narration {i+1}", value=seg["text"], height=80, key=f"seg_txt_{i}")
            col1, col2 = st.columns(2)
            with col1:
                vsq = st.text_input("Visual Query", value=seg.get("visual_search_query", ""), key=f"seg_vsq_{i}")
            with col2:
                kws = st.text_input("Keywords", value=", ".join(seg.get("keywords", [])), key=f"seg_kws_{i}")
            
            edited_segments.append({
                **seg, "text": text, "visual_search_query": vsq, 
                "keywords": [k.strip() for k in kws.split(",") if k.strip()]
            })

    c1, c2 = st.columns([1, 1])
    if c1.button("✅ Continue"):
        script_data["segments"] = edited_segments
        script_data["full_script"] = " ".join(s["text"] for s in edited_segments)
        del st.session_state["pending_script"]
        
        # Setup UI for continuation
        progress = st.progress(10, text="Continuing...")
        status = st.empty()
        st.session_state["_progress"] = progress
        st.session_state["_status"] = status
        
        _run_pipeline_after_script(script_data)
        st.rerun()
        
    if c2.button("❌ Cancel"):
        del st.session_state["pending_script"]
        st.rerun()


# --- Persistent Result Display (The Fix for Disappearing Video) ---
if "last_video_data" in st.session_state:
    vd = st.session_state["last_video_data"]
    video_path = vd["video_path"]
    
    st.markdown("---")
    st.subheader("🎉 Result")
    
    if os.path.exists(video_path):
        st.video(video_path)
        
        # Download Button
        with open(video_path, "rb") as vf:
            st.download_button("💾 Download Video", data=vf, file_name=os.path.basename(video_path), mime="video/mp4")
            
        # --- Extras Section ---
        st.markdown("### 🛠️ Extras")
        
        tab1, tab2, tab3 = st.tabs(["🖼️ Thumbnail", "📤 YouTube Upload", "⚙️ Re-render"])
        
        # Tab 1: Thumbnail
        with tab1:
            if st.button("Generate Thumbnail"):
                with st.spinner("Generating..."):
                    from tools.generate_thumbnail import generate_thumbnail
                    t_topic = st.session_state.get("script_topic", "Video")
                    t_media = st.session_state.get("last_media_assets", [])
                    thumb_path = generate_thumbnail(t_topic, t_media)
                    st.session_state["last_thumbnail"] = thumb_path
            
            if st.session_state.get("last_thumbnail"):
                st.image(st.session_state["last_thumbnail"])
                with open(st.session_state["last_thumbnail"], "rb") as f:
                    st.download_button("Download Thumbnail", f, file_name="thumbnail.jpg", mime="image/jpeg")

        # Tab 2: YouTube Upload
        with tab2:
            privacy = st.selectbox("Privacy", ["unlisted", "private", "public"])
            
            if st.button("Upload to YouTube", disabled=not can_upload):
                with st.spinner("Uploading..."):
                    from tools.upload_youtube import upload_video
                    
                    # Use custom secrets if uploaded, else None (triggering default/env logic)
                    secrets_to_use = user_secrets_path if user_secrets_path else None
                    
                    # SRT path from video data
                    srt_path = vd.get("srt_path")
                    
                    res = upload_video(
                        video_path, 
                        st.session_state.get("script_topic", "Video"), 
                        st.session_state.get("last_media_assets"), 
                        privacy=privacy, 
                        captions_path=srt_path,
                        secrets_path=secrets_to_use
                    )
                    
                    if res.get("youtube_url"):
                        st.success(f"✅ Uploaded! [Watch Video]({res['youtube_url']})")
                    elif res.get("upload_status") == "auth_failed":
                        st.error(f"❌ Auth Failed: {res.get('error')}")
                    else:
                        st.error(f"❌ Failed: {res.get('error', 'Unknown')}")

        # Tab 3: Re-render
        with tab3:
            has_subs = vd.get("subtitles_enabled", True)
            btn_label = "re-render without subtitles" if has_subs else "re-render with subtitles"
            
            if st.button(f"Generate {btn_label}"):
                with st.spinner("Processing..."):
                    # Logic to swap subtitle state
                    import shutil
                    new_ts = datetime.datetime.now().strftime("%H%M%S")
                    new_out = video_path.replace(".mp4", f"_r{new_ts}.mp4")
                    
                    if has_subs:
                         shutil.copy2(vd["raw_path"], new_out)
                         new_subs_state = False
                    else:
                         from tools.compose_video import burn_subtitles_only
                         burn_subtitles_only(vd["raw_path"], new_out, st.session_state["last_audio_data"])
                         new_subs_state = True
                    
                    st.session_state["last_video_data"]["video_path"] = new_out
                    st.session_state["last_video_data"]["subtitles_enabled"] = new_subs_state
                    st.rerun()

st.markdown("---")

# 🎥 AI Video Pipeline

A powerful, automated tool that generates faceless videos from a single text topic. It leverages AI for scriptwriting, voiceovers, image selection, and subtitles, with optional automatic upload to YouTube.

## ✨ Features

-   **AI Script Generation**: Uses **Groq (Llama 3)** or **Gemini** to write engaging scripts.
-   **Realistic Voiceovers**: Powered by **Edge TTS** for high-quality, natural-sounding audio.
-   **Dynamic Visuals**: Fetches relevant stock footage and images from **Pexels API**.
-   **Word-Level Subtitles**: Generates and burns stylish subtitles with precise timing.
-   **YouTube Integration**: Uploads directly to your channel with auto-generated titles, descriptions, and tags.
    -   *Supports "Bring Your Own Key" for secure, personal uploads.*
-   **Dual Interface**:
    -   **Streamlit Web App**: User-friendly GUI with video preview and settings.
    -   **CLI**: Efficient command-line interface for batch processing.

## 🚀 Installation (Local)

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/WanderingHumanid/ai-video-pipeline.git
    cd ai-video-pipeline
    ```

2.  **Install Dependencies**:
    Requires Python 3.10+ and [FFmpeg](https://ffmpeg.org/download.html).
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Keys**:
    Create a `.env` file in the root directory:
    ```ini
    GROQ_API_KEY=your_groq_key
    PEXELS_API_KEY=your_pexels_key
    ```

## 🖥️ Usage

### Method 1: Streamlit App (Recommended)
Launch the interactive web interface:
```bash
streamlit run streamlit_app.py
```
-   Enter a topic (e.g., "The History of AI").
-   Adjust duration and voice settings to your liking.
-   Generate the video and preview it instantly.
-   **Upload to YouTube**: Open the sidebar "How to get Keys" guide to configure your credentials.

### Method 2: Command Line (CLI)
Generate a video quickly via terminal:
```bash
python main.py "The Future of Space Travel" --duration 60 --voice en-US-AriaNeural
```

## ☁️ Deployment

### Streamlit Cloud
You can deploy this app to [Streamlit Cloud](https://share.streamlit.io/) for easy video generation.
-   **Note**: The "Upload to YouTube" feature **does not work on Streamlit Cloud** due to Google's OAuth security restrictions (requires a local browser).
-   Use the Cloud version to generate videos, then download them to upload manually.

## 🛠️ Tech Stack
-   **Language**: Python
-   **UI**: Streamlit
-   **AI**: Groq (Llama 3), Gemini
-   **Media**: MoviePy, Pexels API, Pillow
-   **Audio**: Edge TTS

## 📄 License
MIT License. Free to use and modify.

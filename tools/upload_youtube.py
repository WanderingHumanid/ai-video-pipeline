"""Uploads rendered video to YouTube via Data API v3 with OAuth2."""

import json
import os
import sys
import datetime
import pickle

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def authenticate():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None

    os.makedirs(".tmp", exist_ok=True)
    token_path = ".tmp/youtube_token.pickle"

    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            secrets_path = "client_secrets.json"
            if not os.path.exists(secrets_path):
                raise FileNotFoundError(
                    "client_secrets.json not found. "
                    "Download OAuth2 credentials from Google Cloud Console "
                    "and save as client_secrets.json in the project root."
                )

            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=8080)

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    youtube = build("youtube", "v3", credentials=creds)
    return youtube


def generate_metadata(topic, media_assets=None):
    title = topic[:100]

    attributions = []
    if media_assets:
        for asset in media_assets:
            attr = asset.get("attribution", "")
            if attr and attr != "N/A" and attr not in attributions:
                attributions.append(attr)

    attribution_text = "\n".join(f"- {a}" for a in attributions) if attributions else "- Stock footage"

    description = (
        f"{topic}\n\n"
        f"---\n"
        f"Stock footage credits:\n"
        f"{attribution_text}\n\n"
        f"Powered by Pexels"
    )

    tags = [w.strip() for w in topic.split() if len(w.strip()) > 2][:15]

    return {
        "title": title,
        "description": description[:5000],
        "tags": tags,
        "category_id": "28",
        "privacy_status": "unlisted",
    }


def upload_video(video_path, topic, media_assets=None, privacy="unlisted"):
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    print(f"🎥 Preparing upload: {video_path}")

    youtube = authenticate()

    metadata = generate_metadata(topic, media_assets)
    metadata["privacy_status"] = privacy

    print(f"   Title: {metadata['title']}")
    print(f"   Privacy: {metadata['privacy_status']}")

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": metadata["category_id"],
        },
        "status": {
            "privacyStatus": metadata["privacy_status"],
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print("   Uploading...")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload progress: {int(status.progress() * 100)}%")
        except Exception as e:
            error_str = str(e)
            if "quotaExceeded" in error_str:
                print("❌ YouTube quota exceeded. Video saved locally. Try again tomorrow.")
                return {
                    "youtube_url": "",
                    "youtube_video_id": "",
                    "upload_status": "quota_exceeded",
                    "video_path": video_path,
                    "uploaded_at": datetime.datetime.now().isoformat(),
                }
            raise

    video_id = response["id"]
    youtube_url = f"https://youtube.com/watch?v={video_id}"

    result = {
        "youtube_url": youtube_url,
        "youtube_video_id": video_id,
        "upload_status": "uploaded",
        "uploaded_at": datetime.datetime.now().isoformat(),
    }

    os.makedirs(".tmp", exist_ok=True)
    with open(".tmp/youtube_upload.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n✅ Video uploaded: {youtube_url}")
    return result


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else None
    topic = sys.argv[2] if len(sys.argv) > 2 else "AI Generated Video"

    if not video_path:
        meta_path = ".tmp/output_metadata.json"
        if os.path.exists(meta_path):
            with open(meta_path, "r") as f:
                meta = json.load(f)
            video_path = meta.get("video_path", "")
        else:
            print("❌ No video path provided and no output metadata found.")
            sys.exit(1)

    media_assets = None
    assets_path = ".tmp/media_assets.json"
    if os.path.exists(assets_path):
        with open(assets_path, "r") as f:
            media_assets = json.load(f).get("media_assets", [])

    result = upload_video(video_path, topic, media_assets)
    print(json.dumps(result, indent=2))

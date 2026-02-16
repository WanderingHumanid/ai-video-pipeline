"""Uploads video to YouTube using OAuth2 credentials."""

import json
import os
import sys
import datetime
import pickle
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

load_dotenv()


def authenticate(secrets_path=None):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    creds = None
    
    # Use a separate token file for custom secrets to avoid overwriting default
    if secrets_path:
        token_path = ".tmp/youtube_token_custom.pickle"
    else:
        token_path = ".tmp/youtube_token.pickle"

    os.makedirs(".tmp", exist_ok=True)

    # 1. Try loading pickled credentials
    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    # 2. Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            # 3. IF secrets_path provided, use it (Browser Flow)
            if secrets_path:
                print(f"   🔑 Authenticating with provided secrets: {secrets_path}")
                flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # 4. ELSE try .env credentials
            else:
                client_id = os.getenv("YOUTUBE_CLIENT_ID")
                client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
                refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

                if client_id and client_secret and refresh_token:
                    print("   🔑 Using YouTube credentials from .env")
                    creds = Credentials(
                        None,  # access_token (will be refreshed)
                        refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=SCOPES
                    )
                    creds.refresh(Request())
                else:
                    # 5. Fallback to default client_secrets.json
                    default_secrets = "client_secrets.json"
                    if not os.path.exists(default_secrets):
                        raise FileNotFoundError(
                            "YouTube credentials not found. "
                            "Upload client_secrets.json or configure .env."
                        )
                    
                    print("   🔑 Starting browser authentication (default)...")
                    flow = InstalledAppFlow.from_client_secrets_file(default_secrets, SCOPES)
                    creds = flow.run_local_server(port=0)

        # Save valid credentials
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


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
        "category_id": "28",  # Science & Technology
        "privacy_status": "unlisted",
    }


def upload_video(video_path, topic, media_assets=None, privacy="unlisted", captions_path=None, thumbnail_path=None, secrets_path=None):
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    print(f"🎥 Preparing upload: {video_path}")

    try:
        youtube = authenticate(secrets_path)
    except Exception as e:
        return {
            "upload_status": "auth_failed",
            "error": str(e)
        }

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

    print("   Uploading video...")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload progress: {int(status.progress() * 100)}%")
        except Exception as e:
            error_str = str(e)
            if "quotaExceeded" in error_str:
                print("❌ YouTube quota exceeded. Video saved locally.")
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
    print(f"✅ Video uploaded: {youtube_url}")

    # --- Upload Captions ---
    if captions_path and os.path.exists(captions_path):
        print(f"   Uploading captions: {captions_path}")
        try:
            caption_body = {
                "snippet": {
                    "videoId": video_id,
                    "language": "en",
                    "name": "English (Auto-generated)",
                    "isDraft": False
                }
            }
            caption_media = MediaFileUpload(captions_path, mimetype="application/x-subrip")
            youtube.captions().insert(
                part="snippet",
                body=caption_body,
                media_body=caption_media
            ).execute()
            print("   ✅ Captions uploaded")
        except Exception as e:
            print(f"   ⚠️ Caption upload failed: {e}")

    # --- Upload Thumbnail ---
    if thumbnail_path and os.path.exists(thumbnail_path):
        print(f"   Uploading thumbnail: {thumbnail_path}")
        try:
            thumbnail_media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=thumbnail_media
            ).execute()
            print("   ✅ Thumbnail uploaded")
        except Exception as e:
            print(f"   ⚠️ Thumbnail upload failed: {e}")

    result = {
        "youtube_url": youtube_url,
        "youtube_video_id": video_id,
        "upload_status": "uploaded",
        "uploaded_at": datetime.datetime.now().isoformat(),
    }

    os.makedirs(".tmp", exist_ok=True)
    with open(".tmp/youtube_upload.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

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

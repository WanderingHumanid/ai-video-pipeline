# Architecture SOP: YouTube Upload

**Component:** YouTube Upload (Layer 3 Tool)  
**Owner:** `tools/upload_youtube.py`  
**Purpose:** Automatically upload rendered video to YouTube via Data API v3

---

## 📋 Input Schema

```json
{
  "video_path": "output/video_20260214164945.mp4",
  "title": "string (video title, defaults to topic)",
  "description": "string (video description + attributions)",
  "tags": ["tag1", "tag2"],
  "category_id": "28",
  "privacy_status": "public|unlisted|private"
}
```

---

## 📤 Output Schema

```json
{
  "youtube_url": "https://youtube.com/watch?v=ABC123XYZ",
  "youtube_video_id": "ABC123XYZ",
  "upload_status": "processed|uploaded|failed",
  "uploaded_at": "ISO 8601 datetime"
}
```

---

## 🎯 Behavioral Rules

### 1. Metadata Generation
- **Title:** Use topic as title (max 100 characters)
- **Description:**
  ```
  {Script snippet or topic description}
  
  ---
  Stock footage credits:
  - Video by [Name] on Pexels
  - Video by [Name] on Pexels
  
  Powered by Pexels
  Generated with AI automation
  ```
- **Tags:** Extract from keywords (max 500 characters total)
- **Category:** Science & Technology (ID: 28) OR Education (ID: 27)

### 2. Privacy Settings
- **Default:** `unlisted` (safe for testing)
- **Production:** `public` (only after user approval)

### 3. Quota Management (CRITICAL)
- **Cost per Upload:** 1,600 units
- **Daily Limit:** 6 videos with default quota (10,000 units)
- **Check Quota:** Before upload, verify quota availability
- **Fallback:** If quota exceeded, save video locally and notify user

---

## ⚙️ Tool Implementation Logic

### Step 1: Install Dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Step 2: OAuth2 Authentication Setup
```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import pickle

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def authenticate():
    creds = None
    
    # Load saved credentials
    if os.path.exists('.tmp/youtube_token.pickle'):
        with open('.tmp/youtube_token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # First-time setup: user must authorize
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        
        # Save credentials
        with open('.tmp/youtube_token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    youtube = build('youtube', 'v3', credentials=creds)
    return youtube
```

### Step 3: Build client_secrets.json (One-Time Setup)
User must provide OAuth2 credentials from Google Cloud Console:
```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["http://localhost:8080/"]
  }
}
```

### Step 4: Generate Video Metadata
```python
def generate_metadata(topic, media_assets):
    # Title
    title = topic[:100]  # YouTube limit
    
    # Description with attributions
    attributions = "\n".join([
        f"- {asset['attribution']}" 
        for asset in media_assets 
        if asset['source'] == 'pexels'
    ])
    
    description = f"""
{topic}

---
Stock footage credits:
{attributions}

Powered by Pexels
Generated with AI automation
    """.strip()
    
    # Tags (from keywords)
    all_keywords = list(set([
        kw for asset in media_assets 
        for kw in asset.get('keywords', [])
    ]))
    tags = all_keywords[:50]  # YouTube limit: 500 chars total
    
    return {
        "title": title,
        "description": description,
        "tags": tags,
        "category_id": "28",  # Science & Technology
        "privacy_status": "unlisted"  # Safe default
    }
```

### Step 5: Upload Video
```python
def upload_video(youtube, video_path, metadata):
    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": metadata["category_id"]
        },
        "status": {
            "privacyStatus": metadata["privacy_status"],
            "selfDeclaredMadeForKids": False
        }
    }
    
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
    
    video_id = response['id']
    youtube_url = f"https://youtube.com/watch?v={video_id}"
    
    return {
        "youtube_url": youtube_url,
        "youtube_video_id": video_id,
        "upload_status": "uploaded",
        "uploaded_at": datetime.datetime.now().isoformat()
    }
```

### Step 6: Main Upload Function
```python
import datetime
import json

def upload_to_youtube(video_path, topic, media_assets):
    # Authenticate
    youtube = authenticate()
    
    # Generate metadata
    metadata = generate_metadata(topic, media_assets)
    
    # Upload
    result = upload_video(youtube, video_path, metadata)
    
    # Save result
    with open(".tmp/youtube_upload.json", "w") as f:
        json.dump(result, f, indent=2)
    
    return result
```

---

## 🐛 Error Handling

### Error: OAuth2 authentication fails
- **Cause:** Invalid or missing `client_secrets.json`
- **Action:** Prompt user to create OAuth2 credentials in Google Cloud Console
- **Guide:** Provide step-by-step instructions in README

### Error: Quota exceeded (403 error)
- **Detection:** API returns `quotaExceeded` error
- **Action:** 
  1. Log error to `progress.md`
  2. Save video locally in `output/`
  3. Notify user: "YouTube quota exceeded. Video saved locally. Upload manually or try tomorrow."
- **No Retry:** Quota resets at midnight PT

### Error: Video file too large
- **Limit:** YouTube max = 256 GB (not a concern for 60-second videos)
- **Action:** If somehow exceeded, compress video with higher compression

### Error: Upload interrupted (network failure)
- **Action:** Resumable upload handles this automatically
- **Retry:** YouTube API will resume from last successful chunk

### Error: Video processing fails on YouTube
- **Cause:** Unsupported codec or corrupt file
- **Action:** Re-encode video with FFmpeg using YouTube-recommended settings:
  ```bash
  ffmpeg -i input.mp4 -c:v libx264 -preset slow -crf 22 -c:a aac -b:a 128k -movflags +faststart output.mp4
  ```

---

## 🔐 Security Best Practices

### 1. Credential Storage
- **Never commit:** `client_secrets.json` or `.tmp/youtube_token.pickle`
- **Gitignore:** Ensure both are excluded
- **Streamlit Secrets:** Use `st.secrets` for cloud deployment

### 2. Scope Limitation
- **Use Minimal Scope:** Only `youtube.upload` (not `youtube` full access)
- **Revoke Access:** Provide instructions for users to revoke OAuth2 tokens

### 3. Token Refresh
- **Automatic:** Library handles refresh token rotation
- **Expiry:** Access tokens expire after 1 hour (refresh token is long-lived)

---

## 🧪 Test Cases

### Test 1: First-Time OAuth2 Setup
- **Input:** No existing token
- **Expected:** Browser opens, user authorizes, token saved to `.tmp/youtube_token.pickle`

### Test 2: Successful Upload
- **Input:** Valid video, authenticated user
- **Expected:** Video uploaded, returns YouTube URL

### Test 3: Quota Exceeded
- **Input:** 7th upload in a day (exceeds 10,000 units)
- **Expected:** Error logged, video saved locally, user notified

### Test 4: Network Interruption
- **Simulate:** Disconnect internet mid-upload
- **Expected:** Upload resumes from last chunk when reconnected

---

## 📊 Success Criteria

- ✅ OAuth2 authentication succeeds
- ✅ Video uploads to YouTube without errors
- ✅ Returns valid YouTube URL
- ✅ Video is playable on YouTube within 5 minutes (processing time)
- ✅ Attributions appear in video description
- ✅ Quota monitoring prevents failures

---

## 📝 User Setup Instructions (For README)

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable YouTube Data API v3

### 2. Create OAuth2 Credentials
1. Go to APIs & Services > Credentials
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. Application type: "Desktop app"
4. Download JSON file, save as `client_secrets.json` in project root

### 3. First-Time Authorization
1. Run upload script
2. Browser will open for authorization
3. Grant access to your YouTube channel
4. Token saved automatically for future use

---

**Last Updated:** 2026-02-14  
**Self-Annealing Log:** None yet

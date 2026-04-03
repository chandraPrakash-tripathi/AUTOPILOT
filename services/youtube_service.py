import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from config.settings import YOUTUBE_CLIENT_SECRETS_FILE

logger = logging.getLogger(__name__)

# YouTube upload scope — this is the only permission we need
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

# Where we save the token after first login (so you don't re-login every time)
TOKEN_FILE = "youtube_token.json"


def get_youtube_service():
    """
    Authenticates with YouTube using OAuth2.
    
    First run:  Opens browser → you log in → saves token to youtube_token.json
    Later runs: Loads token from file → auto-refreshes if expired
    
    Returns an authenticated YouTube API client.
    """
    creds = None

    # Load saved token if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid token, do the browser login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token expired but we have a refresh token — silently refresh
            print("🔄 Refreshing YouTube token...")
            creds.refresh(Request())
        else:
            # First time — open browser for login
            print("🌐 Opening browser for YouTube authorization...")
            print("   Log in with the Google account that owns your YouTube channel.")
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the token for next time
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"✅ Token saved to {TOKEN_FILE}")

    return build("youtube", "v3", credentials=creds)


def upload_short(video_path, title, description="", tags=None):
    """
    Uploads a video to YouTube as a Short.
    
    A YouTube Short is just a regular upload under 60 seconds
    with #Shorts in the title or description — YouTube auto-detects it.
    
    Returns the YouTube video ID (str) on success, None on failure.
    """
    print(f"\n▶️  Starting YouTube Short upload: {os.path.basename(video_path)}")

    tags = tags or ["Shorts", "viral", "trending", "reels"]

    # Make sure #Shorts is in the description for YouTube to classify it
    if "#Shorts" not in description and "#shorts" not in description:
        description = description + "\n\n#Shorts"

    youtube = get_youtube_service()

    # Metadata about the video
    body = {
        "snippet": {
            "title": title[:100],          # YouTube title max is 100 chars
            "description": description,
            "tags": tags,
            "categoryId": "22",            # 22 = People & Blogs (good for Reels)
        },
        "status": {
            "privacyStatus": "public",     # "public" | "private" | "unlisted"
            "selfDeclaredMadeForKids": False,
        }
    }

    # MediaFileUpload handles large files with resumable chunked upload
    # resumable=True means if upload fails midway, it can resume
    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5   # upload in 5MB chunks
    )

    try:
        print("📤 Uploading to YouTube...")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        # Execute upload with progress tracking
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                percent = int(status.progress() * 100)
                print(f"   Upload progress: {percent}%")

        video_id = response.get("id")
        video_url = f"https://youtube.com/shorts/{video_id}"
        print(f"✅ YouTube Short uploaded!")
        print(f"   Video ID : {video_id}")
        print(f"   URL      : {video_url}")
        return video_id

    except HttpError as e:
        logger.error(f"YouTube upload error: {e}")
        print(f"❌ YouTube upload failed: {e}")
        return None


def check_channel_info():
    """
    Quick check — shows your YouTube channel name and ID.
    Run this to verify your OAuth setup is working.
    """
    try:
        youtube = get_youtube_service()
        response = youtube.channels().list(
            part="snippet",
            mine=True
        ).execute()

        items = response.get("items", [])
        if not items:
            print("❌ No YouTube channel found for this account.")
            return False

        channel = items[0]["snippet"]
        print(f"✅ YouTube connected!")
        print(f"   Channel : {channel['title']}")
        print(f"   ID      : {items[0]['id']}")
        return True

    except Exception as e:
        print(f"❌ YouTube connection error: {e}")
        return False


if __name__ == "__main__":
    print("=== Testing YouTube API connection ===\n")
    check_channel_info()

    # Uncomment to test a real upload:
    # video_id = upload_short(
    #     video_path="downloads/test.mp4",
    #     title="Test Short #Shorts",
    #     description="Testing upload"
    # )
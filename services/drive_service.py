import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

from config.settings import GOOGLE_DRIVE_FOLDER_ID

# Path to your service account key file
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "..", "service_account.json")

# We only need read access to Drive
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    """
    Authenticates using the service account JSON key
    and returns a Google Drive API client.
    """
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)
    return service


def list_videos_in_folder(folder_id=None):
    """
    Lists ALL video files inside your Google Drive folder.
    Handles pagination automatically — no 100-item limit.
    Returns a list of dicts: [{id, name, mimeType, createdTime}, ...]
    """
    folder_id = folder_id or GOOGLE_DRIVE_FOLDER_ID
    service = get_drive_service()

    # Query: only video files inside the target folder, not in trash
    query = (
        f"'{folder_id}' in parents"
        f" and mimeType contains 'video/'"
        f" and trashed = false"
    )

    all_files = []
    page_token = None

    while True:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, createdTime)",
            orderBy="createdTime",
            pageSize=1000,          # max allowed per request
            pageToken=page_token    # None on first call, then carries forward
        ).execute()

        batch = results.get("files", [])
        all_files.extend(batch)
        print(f"📄 Fetched {len(batch)} videos (total so far: {len(all_files)})")

        # nextPageToken exists only if there are more pages
        page_token = results.get("nextPageToken")
        if not page_token:
            break   # no more pages — we're done

    print(f"📂 Found {len(all_files)} video(s) in Drive folder.")
    return all_files


def download_video(file_id, destination_folder="downloads"):
    """
    Downloads a video file from Drive by its file ID.
    Saves it locally to destination_folder/filename.
    Returns the local file path.
    """
    service = get_drive_service()

    # First get the filename
    file_metadata = service.files().get(fileId=file_id, fields="name").execute()
    filename = file_metadata["name"]

    # Make sure the downloads folder exists
    os.makedirs(destination_folder, exist_ok=True)
    local_path = os.path.join(destination_folder, filename)

    # Stream download — handles large files without loading into RAM
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, "wb")
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        percent = int(status.progress() * 100)
        print(f"⬇️  Downloading {filename}: {percent}%")

    print(f"✅ Downloaded to: {local_path}")
    return local_path


def sync_drive_to_db():
    """
    Fetches ALL videos from Drive and adds any new ones to the database
    with status 'pending'. Already-known videos are skipped (INSERT OR IGNORE).
    This is what the scheduler calls at the start of each cycle.
    """
    from database.db import add_video  # imported here to avoid circular imports

    videos = list_videos_in_folder()

    new_count = 0
    for video in videos:
        add_video(drive_file_id=video["id"], filename=video["name"])
        new_count += 1

    print(f"🔄 Synced {new_count} video(s) from Drive to local DB.")
    return videos


if __name__ == "__main__":
    print("Testing Drive connection...")
    videos = list_videos_in_folder()
    if videos:
        for v in videos:
            print(f"  🎬 {v['name']}  (id: {v['id']})")
    else:
        print("No videos found. Check your folder ID and sharing settings.")
import os
import logging

from database.db import get_connection, mark_uploaded
from services.drive_service import download_video
from services.instagram_service import upload_reel
from services.youtube_service import upload_short

logger = logging.getLogger(__name__)
DOWNLOAD_FOLDER = "downloads"


def get_approved_videos():
    """Fetch all videos with status = 'approved' from the DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE status = 'approved'")
    rows = cursor.fetchall()
    conn.close()
    return rows


def upload_approved_videos():
    """
    Main orchestrator — called by the scheduler and dashboard.
    Loops through all approved videos and processes each one.
    """
    approved = get_approved_videos()

    if not approved:
        print("📭 No approved videos waiting for upload.")
        return

    print(f"\n🚀 Found {len(approved)} approved video(s) to upload.")

    for video in approved:
        _process_one_video(dict(video))


def _process_one_video(video):
    """
    Full upload cycle for one video:
    1. Download from Drive locally (needed for both Instagram + YouTube)
    2. Upload to selected platform(s)
    3. Update DB status to 'uploaded'
    4. Clean up local temp file

    WHY always download first?
    Both Instagram (file upload) and YouTube (MediaFileUpload) need
    a local file. Drive URLs are not publicly accessible to external APIs.
    """
    drive_file_id = video["drive_file_id"]
    filename      = video["filename"]
    caption       = video["caption"] or ""
    platform      = video["platform"] or "both"

    print(f"\n{'='*50}")
    print(f"📹 Processing : {filename}")
    print(f"🎯 Platform   : {platform}")
    print(f"📝 Caption    : {caption[:60]}{'...' if len(caption) > 60 else ''}")
    print(f"{'='*50}")

    local_path = None

    try:
        # ── 1. Download from Drive ────────────────────────────
        # Always download — both platforms need local file
        print("\n⬇️  Downloading from Google Drive...")
        local_path = download_video(drive_file_id, DOWNLOAD_FOLDER)

        if not local_path or not os.path.exists(local_path):
            print("❌ Download failed — skipping this video.")
            return

        file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
        print(f"✅ Downloaded: {filename} ({file_size_mb:.1f} MB)")

        # ── 2. Upload to platform(s) ──────────────────────────
        ig_post_id  = None
        yt_video_id = None

        if platform in ("instagram", "both"):
            # Pass local file path — NOT a URL
            ig_post_id = upload_reel(local_path, caption)
            if ig_post_id:
                print(f"📸 Instagram post ID : {ig_post_id}")
            else:
                print("⚠️  Instagram upload failed — continuing to YouTube...")

        if platform in ("youtube", "both"):
            # Use first line of caption as YouTube title
            title = caption.split("\n")[0][:100] or filename
            yt_video_id = upload_short(local_path, title, caption)
            if yt_video_id:
                print(f"▶️  YouTube video ID  : {yt_video_id}")
            else:
                print("⚠️  YouTube upload failed.")

        # ── 3. Update DB ──────────────────────────────────────
        if ig_post_id or yt_video_id:
            combined_post_id = (
                f"ig:{ig_post_id or 'failed'}"
                f"|yt:{yt_video_id or 'failed'}"
            )
            mark_uploaded(drive_file_id, platform, combined_post_id)
            print(f"\n✅ DB updated — marked as uploaded.")
            print(f"   Post IDs: {combined_post_id}")
        else:
            print(f"\n❌ All uploads failed — keeping status 'approved' to retry next cycle.")

    except Exception as e:
        logger.error(f"Error processing {filename}: {e}", exc_info=True)
        print(f"❌ Unexpected error: {e}")

    finally:
        # ── 4. Always clean up local file ─────────────────────
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
            print(f"🗑️  Cleaned up temp file: {local_path}")


if __name__ == "__main__":
    print("=== Running upload cycle manually ===\n")
    upload_approved_videos()
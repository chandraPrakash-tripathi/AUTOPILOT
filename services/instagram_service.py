import os
import time
import requests
import logging
import subprocess

import cloudinary
import cloudinary.uploader

from config.settings import (
    INSTAGRAM_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN,
    CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
)

logger = logging.getLogger(__name__)
BASE_URL = "https://graph.facebook.com/v19.0"

# Configure Cloudinary once at import time
cloudinary.config(
    cloud_name = CLOUDINARY_CLOUD_NAME,
    api_key    = CLOUDINARY_API_KEY,
    api_secret = CLOUDINARY_API_SECRET,
    secure     = True
)


# ── API Helpers ───────────────────────────────────────────────────

def _api_get(endpoint, params=None):
    params = params or {}
    params["access_token"] = INSTAGRAM_ACCESS_TOKEN
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    return response.json()


def _api_post(endpoint, data=None):
    data = data or {}
    data["access_token"] = INSTAGRAM_ACCESS_TOKEN
    response = requests.post(f"{BASE_URL}/{endpoint}", data=data)
    return response.json()


def check_token_valid():
    result = _api_get("me", {"fields": "id,name"})
    if "error" in result:
        print(f"❌ Token error: {result['error']['message']}")
        return False
    print(f"✅ Token valid! Logged in as: {result.get('name')} (id: {result.get('id')})")
    return True


# ── Video Re-encoding ─────────────────────────────────────────────

def reencode_for_instagram(input_path):
    """
    Re-encodes to H.264 + AAC with a clean sanitized filename.
    Even if the source is already H.264, re-encoding ensures
    faststart flag and correct profile for Instagram.
    """
    folder  = os.path.dirname(os.path.abspath(input_path))
    name, _ = os.path.splitext(os.path.basename(input_path))

    safe_name   = name.replace(" ", "_") \
                      .replace("(", "").replace(")", "") \
                      .replace("[", "").replace("]", "") \
                      .lower()
    output_path = os.path.join(folder, f"{safe_name}_ig.mp4")

    print(f"🔄 Re-encoding for Instagram...")
    print(f"   Input : {os.path.basename(input_path)}")
    print(f"   Output: {os.path.basename(output_path)}")

    command = [
        "ffmpeg", "-i", input_path,
        "-c:v", "libx264",
        "-profile:v", "high",      # High profile — widely supported
        "-level", "4.0",           # Level 4.0 — supports 1080p
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-profile:a", "aac_low",   # LC-AAC (most compatible, NOT HE-AAC)
        "-b:a", "128k",
        "-ar", "44100",            # 44.1kHz sample rate
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-vf", "scale='min(1080,iw)':-2",
        "-y", output_path
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print(f"❌ ffmpeg failed! Using original.")
        print(result.stderr.decode("utf-8", errors="replace"))
        return input_path

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"✅ Re-encoded: {os.path.basename(output_path)} ({size_mb:.1f} MB)")
    return output_path


# ── Cloudinary Upload ─────────────────────────────────────────────

def upload_to_cloudinary(video_path):
    """
    Uploads video to Cloudinary and returns a public URL.
    
    WHY Cloudinary instead of ngrok?
    Instagram's servers block/distrust free ngrok tunnels.
    Cloudinary is a trusted CDN — Instagram can always fetch from it.
    Free tier: 25GB storage, 25GB bandwidth/month — plenty for testing.
    
    Returns (public_url, public_id) or (None, None) on failure.
    """
    filename  = os.path.basename(video_path)
    public_id = os.path.splitext(filename)[0]  # use filename as ID in Cloudinary

    print(f"☁️  Uploading to Cloudinary: {filename}")

    try:
        result = cloudinary.uploader.upload(
            video_path,
            resource_type = "video",
            public_id     = public_id,
            overwrite     = True,
            folder        = "autopilot"   # organizes under autopilot/ in your account
        )

        url = result.get("secure_url")
        pid = result.get("public_id")
        print(f"✅ Cloudinary upload done!")
        print(f"   URL: {url}")
        return url, pid

    except Exception as e:
        print(f"❌ Cloudinary upload failed: {e}")
        return None, None


def delete_from_cloudinary(public_id):
    """Deletes a video from Cloudinary after Instagram has processed it."""
    try:
        cloudinary.uploader.destroy(public_id, resource_type="video")
        print(f"🗑️  Deleted from Cloudinary: {public_id}")
    except Exception as e:
        logger.warning(f"Could not delete from Cloudinary: {e}")


# ── Step 1: Create Container ──────────────────────────────────────

def create_reel_container(video_url, caption):
    """
    STEP 1 of 3: POST the Cloudinary URL to Instagram to create container.
    Returns container_id or None.
    """
    print(f"\n📤 Step 1/3: Creating Reel container...")
    print(f"   URL: {video_url}")

    response = requests.post(
        f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media",
        data={
            "media_type":    "REELS",
            "video_url":     video_url,
            "caption":       caption,
            "share_to_feed": "true",
            "access_token":  INSTAGRAM_ACCESS_TOKEN,
        },
        timeout=60
    )

    result = response.json()
    print(f"   API response: {result}")

    if "error" in result:
        print(f"❌ Failed: {result['error']['message']} (code {result['error'].get('code')})")
        return None

    container_id = result.get("id")
    print(f"✅ Step 1/3 done. Container ID: {container_id}")
    return container_id


# ── Step 2: Wait for Processing ───────────────────────────────────

def wait_for_container_ready(container_id, max_wait=180):
    """
    STEP 2 of 3: Poll until Instagram finishes processing.
    Returns True if FINISHED, False if ERROR/timeout.
    """
    print(f"\n⏳ Step 2/3: Waiting for Instagram to process...")

    waited = 0
    while waited < max_wait:
        result = _api_get(container_id, {"fields": "status_code,status"})
        status = result.get("status_code", "UNKNOWN")
        detail = result.get("status", "")
        print(f"   [{waited:>3}s] {status} — {detail}")

        if status == "FINISHED":
            print(f"✅ Step 2/3 done. Video ready!")
            return True

        elif status in ("ERROR", "EXPIRED"):
            print(f"❌ Processing failed: {detail}")
            return False

        time.sleep(5)
        waited += 5

    print(f"❌ Timed out after {max_wait}s")
    return False


# ── Step 3: Publish ───────────────────────────────────────────────

def publish_reel(container_id):
    """STEP 3 of 3: Publish the container as a live Reel."""
    print(f"\n🚀 Step 3/3: Publishing Reel...")

    result = _api_post(
        f"{INSTAGRAM_ACCOUNT_ID}/media_publish",
        {"creation_id": container_id}
    )

    if "error" in result:
        print(f"❌ Publish failed: {result['error']['message']}")
        return None

    post_id = result.get("id")
    print(f"✅ Reel published! Post ID: {post_id}")
    print(f"   View: https://www.instagram.com/p/{post_id}/")
    return post_id


# ── Master Upload Function ────────────────────────────────────────

def upload_reel(video_path, caption):
    """
    Full pipeline:
    1. Re-encode to H.264/AAC LC
    2. Upload re-encoded file to Cloudinary (trusted public URL)
    3. POST URL to Instagram → get container_id
    4. Poll until processed
    5. Publish
    6. Delete from Cloudinary + clean up local files
    
    Returns post_id on success, None on failure.
    """
    print(f"\n📸 Instagram upload: {os.path.basename(video_path)}")

    if not os.path.exists(video_path):
        print(f"❌ File not found: {video_path}")
        return None

    encoded_path = None
    cloudinary_id = None

    try:
        # 1. Re-encode
        encoded_path = reencode_for_instagram(video_path)

        # 2. Upload to Cloudinary
        public_url, cloudinary_id = upload_to_cloudinary(encoded_path)
        if not public_url:
            return None

        # 3. Create Instagram container
        container_id = create_reel_container(public_url, caption)
        if not container_id:
            return None

        # 4. Wait for processing
        ready = wait_for_container_ready(container_id)
        if not ready:
            return None

        # 5. Publish
        return publish_reel(container_id)

    finally:
        # 6. Cleanup
        if cloudinary_id:
            delete_from_cloudinary(cloudinary_id)
        if encoded_path and encoded_path != video_path:
            if os.path.exists(encoded_path):
                os.remove(encoded_path)
                print(f"🗑️  Cleaned up re-encoded file.")


# ── Test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Testing Instagram API connection ===\n")
    check_token_valid()
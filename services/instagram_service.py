import os
import time
import requests
import logging

from config.settings import INSTAGRAM_ACCOUNT_ID, INSTAGRAM_ACCESS_TOKEN

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.facebook.com/v19.0"


def _api_get(endpoint, params=None):
    """Helper: GET request to Graph API with auth token."""
    params = params or {}
    params["access_token"] = INSTAGRAM_ACCESS_TOKEN
    response = requests.get(f"{BASE_URL}/{endpoint}", params=params)
    return response.json()


def _api_post(endpoint, data=None):
    """Helper: POST request to Graph API with auth token."""
    data = data or {}
    data["access_token"] = INSTAGRAM_ACCESS_TOKEN
    response = requests.post(f"{BASE_URL}/{endpoint}", data=data)
    return response.json()


def check_token_valid():
    """
    Quick check — verifies your access token works.
    Run this first to confirm your setup is correct.
    """
    result = _api_get("me", {"fields": "id,name"})
    if "error" in result:
        print(f"❌ Token error: {result['error']['message']}")
        return False
    print(f"✅ Token valid! Logged in as: {result.get('name')} (id: {result.get('id')})")
    return True


def create_reel_container(video_path, caption):
    """
    STEP 1 of 3: Tell Instagram we want to upload a Reel.
    
    We upload the video file directly as multipart form data.
    Instagram processes it and gives us a container_id.
    
    Returns container_id (str) or None on failure.
    """
    print(f"📤 Step 1/3: Creating Instagram Reel container...")

    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"

    with open(video_path, "rb") as video_file:
        response = requests.post(
            url,
            data={
                "media_type": "REELS",
                "caption": caption,
                "share_to_feed": "true",   # also shows on main feed
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            files={
                "video_file": (os.path.basename(video_path), video_file, "video/mp4")
            }
        )

    result = response.json()

    if "error" in result:
        logger.error(f"Instagram container error: {result['error']}")
        print(f"❌ Container creation failed: {result['error']['message']}")
        return None

    container_id = result.get("id")
    print(f"✅ Step 1/3 done. Container ID: {container_id}")
    return container_id


def wait_for_container_ready(container_id, max_wait=120):
    """
    STEP 2 of 3: Wait for Instagram to finish processing the video.
    
    Instagram processes the video asynchronously — we poll every 5 seconds
    until status = FINISHED (ready to publish) or it times out.
    
    Returns True if ready, False if failed/timed out.
    """
    print(f"⏳ Step 2/3: Waiting for Instagram to process video...")

    waited = 0
    while waited < max_wait:
        result = _api_get(
            container_id,
            {"fields": "status_code,status"}
        )

        status = result.get("status_code", "UNKNOWN")
        print(f"   Status: {status} ({waited}s elapsed)")

        if status == "FINISHED":
            print(f"✅ Step 2/3 done. Video processed and ready!")
            return True
        elif status in ("ERROR", "EXPIRED"):
            print(f"❌ Container failed with status: {status}")
            return False

        time.sleep(5)
        waited += 5

    print(f"❌ Timed out waiting for container after {max_wait}s")
    return False


def publish_reel(container_id):
    """
    STEP 3 of 3: Publish the processed container as a Reel.
    
    Returns the Instagram post ID (str) or None on failure.
    """
    print(f"🚀 Step 3/3: Publishing Reel...")

    result = _api_post(
        f"{INSTAGRAM_ACCOUNT_ID}/media_publish",
        {"creation_id": container_id}
    )

    if "error" in result:
        logger.error(f"Instagram publish error: {result['error']}")
        print(f"❌ Publish failed: {result['error']['message']}")
        return None

    post_id = result.get("id")
    print(f"✅ Step 3/3 done. Reel published! Post ID: {post_id}")
    return post_id


def upload_reel(video_path, caption):
    """
    Master function — runs all 3 steps to upload a Reel.
    This is what the rest of the app calls.
    
    Returns post_id (str) on success, None on failure.
    """
    print(f"\n📸 Starting Instagram Reel upload: {os.path.basename(video_path)}")

    # Step 1: Create container
    container_id = create_reel_container(video_path, caption)
    if not container_id:
        return None

    # Step 2: Wait for processing
    ready = wait_for_container_ready(container_id)
    if not ready:
        return None

    # Step 3: Publish
    post_id = publish_reel(container_id)
    return post_id


if __name__ == "__main__":
    # Test 1: Check if your token works
    print("=== Testing Instagram API connection ===\n")
    check_token_valid()

    # Test 2: Optionally test a real upload
    # Uncomment below and point to a real .mp4 file to test upload
    # post_id = upload_reel(
    #     video_path="downloads/test.mp4",
    #     caption="Test reel #testing"
    # )
    # if post_id:
    #     print(f"\n🎉 Success! View at: https://www.instagram.com/p/{post_id}/")
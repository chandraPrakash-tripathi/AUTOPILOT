import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import streamlit.components.v1 as components
from database.db import get_all_videos, update_status
from services.drive_service import sync_drive_to_db
from services.uploader import upload_approved_videos

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Autopilot Dashboard",
    page_icon="🎬",
    layout="wide"
)

# ── Helpers ───────────────────────────────────────────────────────

def get_drive_preview_url(file_id):
    return f"https://drive.google.com/file/d/{file_id}/preview"

def get_drive_link(file_id):
    return f"https://drive.google.com/file/d/{file_id}/view"

def count_by_status(videos):
    counts = {"pending": 0, "approved": 0, "uploaded": 0, "skipped": 0}
    for v in videos:
        s = v["status"]
        if s in counts:
            counts[s] += 1
    return counts

def status_badge(status):
    return {
        "pending":  "⏳ Pending",
        "approved": "✅ Approved",
        "uploaded": "🚀 Uploaded",
        "skipped":  "⏭️ Skipped",
    }.get(status, status)

def platform_badge(platform):
    return {
        "instagram": "📸 Instagram",
        "youtube":   "▶️ YouTube",
        "both":      "🚀 Both",
    }.get(platform, "—") if platform else "—"

# ── Session state defaults ────────────────────────────────────────
# These persist across Streamlit reruns within the same session

if "review_video"   not in st.session_state:
    st.session_state.review_video = None
if "library_page"   not in st.session_state:
    st.session_state.library_page = 0          # current page index (0-based)
if "status_filter"  not in st.session_state:
    st.session_state.status_filter = "all"

VIDEOS_PER_PAGE = 12   # 4 rows × 3 columns — fast to render

# ── Load data ONCE per render ─────────────────────────────────────
# We load all videos but only RENDER the current page slice
# This keeps DB calls minimal while making the UI fast

all_videos = get_all_videos()
counts     = count_by_status(all_videos)

# ── Sidebar ───────────────────────────────────────────────────────

with st.sidebar:
    st.title("🎬 Autopilot")
    st.caption("Automated Reel Publisher")
    st.divider()

    if st.button("🔄 Sync Google Drive", use_container_width=True):
        with st.spinner("Syncing from Google Drive..."):
            sync_drive_to_db()
        st.success("Drive synced!")
        st.rerun()

    if st.button("🚀 Upload Approved Videos", use_container_width=True):
        with st.spinner("Uploading approved videos..."):
            upload_approved_videos()
        st.success("Upload cycle complete!")
        st.rerun()

    st.divider()
    st.subheader("🔍 Filter")

    new_filter = st.selectbox(
        "Show videos with status:",
        ["all", "pending", "approved", "uploaded", "skipped"],
        index=["all", "pending", "approved", "uploaded", "skipped"].index(
            st.session_state.status_filter
        )
    )

    # Reset to page 0 whenever filter changes
    if new_filter != st.session_state.status_filter:
        st.session_state.status_filter = new_filter
        st.session_state.library_page  = 0
        st.rerun()

    st.divider()
    st.caption("Run `python main.py` to start the full system.")

# ── Header metrics ────────────────────────────────────────────────

st.title("🎬 Autopilot Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("⏳ Pending",  counts["pending"])
c2.metric("✅ Approved", counts["approved"])
c3.metric("🚀 Uploaded", counts["uploaded"])
c4.metric("⏭️ Skipped",  counts["skipped"])

st.divider()

# ── Review Panel ──────────────────────────────────────────────────

pending_videos = [v for v in all_videos if v["status"] == "pending"]

if pending_videos:
    st.subheader("🎯 Review Next Video")

    # Pick initial video if none selected
    if st.session_state.review_video is None:
        st.session_state.review_video = dict(random.choice(pending_videos))

    current = st.session_state.review_video

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown(f"**📁 {current['filename']}**")
        components.iframe(get_drive_preview_url(current["drive_file_id"]), height=360)
        st.caption(f"[Open in Drive ↗]({get_drive_link(current['drive_file_id'])})")

    with right:
        st.markdown("#### Actions")

        if st.button("🔀 Shuffle — pick different video", use_container_width=True):
            others = [v for v in pending_videos
                      if v["drive_file_id"] != current["drive_file_id"]]
            if others:
                st.session_state.review_video = dict(random.choice(others))
                st.rerun()
            else:
                st.warning("No other pending videos!")

        st.divider()
        st.markdown("#### ✅ Approve this video")

        caption_input = st.text_area(
            "Caption & Hashtags",
            placeholder="#health #reels #viral",
            height=100,
            key="caption_input"
        )
        platform_input = st.radio(
            "Post to:",
            ["both", "instagram", "youtube"],
            format_func=platform_badge,
            horizontal=True,
            key="platform_input"
        )

        if st.button("✅ Approve & Queue", use_container_width=True, type="primary"):
            if not caption_input.strip():
                st.warning("Please enter a caption first!")
            else:
                update_status(
                    drive_file_id=current["drive_file_id"],
                    status="approved",
                    caption=caption_input,
                    platform=platform_input
                )
                st.success(f"✅ Queued: {current['filename']}")
                st.session_state.review_video = None
                st.rerun()

        st.divider()

        if st.button("⏭️ Skip this video", use_container_width=True):
            update_status(current["drive_file_id"], "skipped")
            st.session_state.review_video = None
            st.rerun()

    st.divider()

# ── Video Library with Pagination ────────────────────────────────

# Apply status filter
if st.session_state.status_filter == "all":
    filtered = all_videos
else:
    filtered = [v for v in all_videos if v["status"] == st.session_state.status_filter]

total_videos = len(filtered)
total_pages  = max(1, (total_videos + VIDEOS_PER_PAGE - 1) // VIDEOS_PER_PAGE)

# Clamp page index in case filter changed and page is now out of range
if st.session_state.library_page >= total_pages:
    st.session_state.library_page = 0

current_page = st.session_state.library_page
start_idx    = current_page * VIDEOS_PER_PAGE
end_idx      = start_idx + VIDEOS_PER_PAGE
page_videos  = filtered[start_idx:end_idx]   # ← only 12 videos rendered

# Library header + pagination controls (top)
st.subheader(f"📚 Video Library — {total_videos} videos")

top_left, top_mid, top_right = st.columns([1, 2, 1])

with top_left:
    if st.button("◀ Prev", disabled=(current_page == 0), use_container_width=True):
        st.session_state.library_page -= 1
        st.rerun()

with top_mid:
    st.markdown(
        f"<p style='text-align:center; padding-top:6px;'>"
        f"Page <b>{current_page + 1}</b> of <b>{total_pages}</b> "
        f"&nbsp;|&nbsp; showing {start_idx + 1}–{min(end_idx, total_videos)} of {total_videos}"
        f"</p>",
        unsafe_allow_html=True
    )

with top_right:
    if st.button("Next ▶", disabled=(current_page >= total_pages - 1), use_container_width=True):
        st.session_state.library_page += 1
        st.rerun()

# Jump to page input
with st.expander("Jump to page"):
    jump = st.number_input(
        "Page number",
        min_value=1,
        max_value=total_pages,
        value=current_page + 1,
        step=1,
        key="jump_input"
    )
    if st.button("Go", key="jump_go"):
        st.session_state.library_page = int(jump) - 1
        st.rerun()

st.divider()

# ── Render only current page's 12 videos ─────────────────────────

if not page_videos:
    st.info("No videos match the current filter.")
else:
    cols_per_row = 3
    for i in range(0, len(page_videos), cols_per_row):
        row_videos = page_videos[i:i + cols_per_row]
        cols = st.columns(cols_per_row)

        for col, video in zip(cols, row_videos):
            video = dict(video)
            with col:
                with st.container(border=True):
                    st.markdown(f"**{status_badge(video['status'])}**")
                    st.caption(video["filename"])
                    st.markdown(f"[▶ Preview]({get_drive_link(video['drive_file_id'])})")

                    if video.get("caption"):
                        st.caption(f"📝 {video['caption'][:50]}...")
                    if video.get("platform"):
                        st.caption(platform_badge(video["platform"]))
                    if video.get("uploaded_at"):
                        st.caption(f"🕐 {video['uploaded_at']}")

                    if video["status"] == "pending":
                        if st.button(
                            "Review",
                            key=f"rev_{video['drive_file_id']}",
                            use_container_width=True
                        ):
                            st.session_state.review_video = video
                            st.session_state.library_page = 0
                            st.rerun()

                    elif video["status"] == "skipped":
                        if st.button(
                            "↩️ Restore",
                            key=f"rst_{video['drive_file_id']}",
                            use_container_width=True
                        ):
                            update_status(video["drive_file_id"], "pending")
                            st.rerun()

# ── Bottom pagination controls (mirror of top) ───────────────────

st.divider()
bot_left, bot_mid, bot_right = st.columns([1, 2, 1])

with bot_left:
    if st.button("◀ Prev ", disabled=(current_page == 0), use_container_width=True):
        st.session_state.library_page -= 1
        st.rerun()

with bot_mid:
    st.markdown(
        f"<p style='text-align:center; padding-top:6px;'>"
        f"Page <b>{current_page + 1}</b> of <b>{total_pages}</b>"
        f"</p>",
        unsafe_allow_html=True
    )

with bot_right:
    if st.button("Next ▶ ", disabled=(current_page >= total_pages - 1), use_container_width=True):
        st.session_state.library_page += 1
        st.rerun()
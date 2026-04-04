# 🎬 AUTOPILOT — Complete Project Documentation
### The Soul & Source of Truth for the Automated Reel Publishing System

> **GitHub:** https://github.com/chandraPrakash-tripathi/AUTOPILOT.git  
> **Built by:** Chandra Prakash Tripathi  
> **Stack:** Python 3.11 · Google Drive API · Instagram Graph API · YouTube Data API v3 · Telegram Bot API · Cloudinary · APScheduler · Streamlit · SQLite

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [How the Full Flow Works](#4-how-the-full-flow-works)
5. [Step 1 — Project Skeleton & Database](#5-step-1--project-skeleton--database)
6. [Step 2 — Google Drive API](#6-step-2--google-drive-api)
7. [Step 3 — Telegram Bot](#7-step-3--telegram-bot)
8. [Step 4 — Instagram Graph API](#8-step-4--instagram-graph-api)
9. [Step 5 — YouTube Data API v3](#9-step-5--youtube-data-api-v3)
10. [Step 6 — Upload Orchestrator & Scheduler](#10-step-6--upload-orchestrator--scheduler)
11. [Step 7 — Streamlit Dashboard](#11-step-7--streamlit-dashboard)
12. [Step 8 — Wiring Everything in main.py](#12-step-8--wiring-everything-in-mainpy)
13. [API Setup Guides](#13-api-setup-guides)
14. [Environment Variables Reference](#14-environment-variables-reference)
15. [Common Errors & Fixes](#15-common-errors--fixes)
16. [Daily Usage Guide](#16-daily-usage-guide)

---

## 1. What This System Does

Autopilot is a **fully automated content publishing system** that:

- Pulls videos from your **Google Drive** folder
- Sends them to you via **Telegram** for review (with preview + buttons)
- Lets you **Approve / Shuffle / Skip** each video
- Asks for a **caption and platform selection** (Instagram / YouTube / Both)
- **Uploads approved videos** automatically to the selected platforms
- Tracks every video's state (`pending → approved → uploaded / skipped`) in a **SQLite database**
- Runs **3 times per day** on a schedule (10 AM, 3 PM, 8 PM)
- Provides a **Streamlit web dashboard** for desktop review and history

---

## 2. Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Language | Python 3.11+ | Everything |
| Video source | Google Drive API v3 | Fetch and download videos |
| Approval interface | Telegram Bot API (python-telegram-bot v21) | Send previews, handle buttons |
| Instagram upload | Instagram Graph API v19 | Publish Reels |
| YouTube upload | YouTube Data API v3 | Publish Shorts |
| Video hosting (temp) | Cloudinary | Public URL for Instagram API |
| Video re-encoding | ffmpeg | Convert to H.264/AAC for Instagram |
| Scheduler | APScheduler 3.x | 3x daily automated triggers |
| Dashboard | Streamlit | Web UI for review and history |
| Database | SQLite (built-in Python) | State tracking for all videos |
| Config | python-dotenv | Manage API keys via .env file |

---

## 3. Project Structure

```
autopilot/
│
├── .env                        # All secrets — NEVER commit this
├── .gitignore
├── requirements.txt
├── main.py                     # Entry point — starts scheduler + Telegram bot
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Loads .env into Python variables
│
├── database/
│   ├── __init__.py
│   ├── db.py                   # SQLite setup, all DB operations
│   └── autopilot.db            # Auto-created SQLite database file
│
├── services/
│   ├── __init__.py
│   ├── drive_service.py        # Google Drive API — list, download, sync
│   ├── telegram_service.py     # Telegram Bot — send previews, handle buttons
│   ├── instagram_service.py    # Instagram Graph API — re-encode, upload Reels
│   ├── youtube_service.py      # YouTube Data API — upload Shorts
│   └── uploader.py             # Orchestrator — routes approved videos to platforms
│
├── scheduler/
│   ├── __init__.py
│   └── job.py                  # APScheduler — 3x daily cron jobs
│
├── dashboard/
│   └── app.py                  # Streamlit web dashboard
│
├── downloads/                  # Temp folder — videos downloaded here, deleted after upload
├── service_account.json        # Google Drive service account key — NEVER commit
├── client_secrets.json         # YouTube OAuth client secrets — NEVER commit
└── youtube_token.json          # YouTube OAuth token (auto-created) — NEVER commit
```

---

## 4. How the Full Flow Works

```
┌─────────────────────────────────────────────────────────────┐
│                    DAILY AUTOMATED CYCLE                     │
│                  (Runs at 10AM, 3PM, 8PM)                   │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
  1. Scheduler fires
          │
          ▼
  2. sync_drive_to_db()
     → Lists all .mp4 files in your Drive folder
     → Adds any new ones to SQLite as status='pending'
     → Already-known videos are ignored (INSERT OR IGNORE)
          │
          ▼
  3. Telegram bot sends you a video review message
     → Downloads video from Drive
     → Sends it as a Telegram video (or Drive link if too large)
     → Shows: ✅ Approve  🔀 Shuffle  ⏭️ Skip buttons
          │
     ┌────┴────┐
     │         │
  Shuffle    Approve
     │         │
  New video  Bot asks: "Type your caption"
             │
             ▼
          You type caption + hashtags
             │
             ▼
          Bot asks: 📸 Instagram / ▶️ YouTube / 🚀 Both
             │
             ▼
          DB updated: status='approved', caption, platform saved
          │
          ▼
  4. Next scheduler cycle (or manual trigger):
     upload_approved_videos()
     → Downloads video from Drive locally
     → Re-encodes with ffmpeg (H.264 + AAC LC)
     → Uploads re-encoded file to Cloudinary (trusted public CDN)
     → POSTs Cloudinary URL to Instagram Graph API
     → Polls until Instagram processes it (IN_PROGRESS → FINISHED)
     → Publishes the Reel
     → Uploads to YouTube using resumable chunked upload
     → Updates DB: status='uploaded', post_id saved
     → Deletes from Cloudinary, cleans up local temp files
```

---

## 5. Step 1 — Project Skeleton & Database

### What we built
- Full folder structure with proper Python packages (`__init__.py` in every folder)
- `.env` file for all secrets
- `config/settings.py` to load `.env` into Python
- `database/db.py` with SQLite setup and all CRUD operations

### Key concept: Why SQLite?
SQLite is a file-based database — no server needed. It lives as a single file (`autopilot.db`) in your project. Perfect for a solo automation tool that runs on one machine.

### The `videos` table schema

```sql
CREATE TABLE IF NOT EXISTS videos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    drive_file_id TEXT UNIQUE NOT NULL,   -- Google Drive file ID (the hash in the URL)
    filename      TEXT NOT NULL,
    status        TEXT DEFAULT 'pending', -- pending | approved | uploaded | skipped
    caption       TEXT,                   -- caption typed by user
    platform      TEXT,                   -- instagram | youtube | both
    post_id       TEXT,                   -- returned post ID after successful upload
    uploaded_at   TIMESTAMP,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### State machine for every video
```
pending → (you approve) → approved → (uploader runs) → uploaded
pending → (you skip)    → skipped  → (you restore)   → pending
```

### `database/db.py` — key functions

| Function | What it does |
|---|---|
| `init_db()` | Creates the table if it doesn't exist |
| `add_video(file_id, filename)` | Inserts a video as pending — ignores duplicates |
| `get_pending_videos()` | Returns all videos with status=pending |
| `get_all_videos()` | Returns all videos, newest first |
| `update_status(file_id, status, caption, platform)` | Updates video state |
| `mark_uploaded(file_id, platform, post_id)` | Marks as uploaded with post ID |

### How to initialize
```bash
python -m database.db
# Output: ✅ Database initialized.
```

---

## 6. Step 2 — Google Drive API

### What we built
- Service account authentication (no browser login needed)
- List all video files in a Drive folder
- Download individual videos locally
- Sync function that adds new Drive videos to DB

### Key concept: Service Account vs OAuth
- **Service Account** = a robot Google account. You share your Drive folder with it. It can access that folder without any human login. Used for Drive (read-only access to your folder).
- **OAuth Client** = requires a human to log in via browser. Used for YouTube (you must personally authorize your channel).

### Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project `autopilot-reels`
3. Enable **Google Drive API**
4. Create **Service Account** → download JSON key → rename to `service_account.json`
5. Copy the `client_email` from the JSON
6. Share your Drive folder with that email (Viewer access)
7. Copy your folder ID from the Drive URL → paste into `.env`

### How folder ID works
```
https://drive.google.com/drive/folders/1X7eYflWAz7W_bZBiPBP2u1UUhEst1Nm7
                                        ↑ THIS IS YOUR FOLDER ID
```
Do not include `?usp=sharing` — that's just a sharing suffix, not part of the ID.

### `drive_service.py` — key functions

| Function | What it does |
|---|---|
| `get_drive_service()` | Authenticates with service account, returns API client |
| `list_videos_in_folder()` | Queries Drive for video files in your folder |
| `download_video(file_id, folder)` | Streams video to local disk (handles large files) |
| `sync_drive_to_db()` | Adds any new Drive videos to DB as pending |

### Why streaming download?
```python
downloader = MediaIoBaseDownload(fh, request)
done = False
while not done:
    status, done = downloader.next_chunk()
```
Instead of loading the entire file into RAM, `MediaIoBaseDownload` downloads in chunks. Essential for large video files that would crash your RAM if loaded all at once.

### Test
```bash
python -m services.drive_service
# Output: 📂 Found 534 video(s) in Drive folder.
```

---

## 7. Step 3 — Telegram Bot

### What we built
- A Telegram bot with a full multi-step conversation flow
- Video preview (downloads from Drive → sends to Telegram → deletes local file)
- Inline keyboard buttons: Approve / Shuffle / Skip
- Caption input and platform selection
- `/status` command showing video counts by state

### Key concept: ConversationHandler states
The bot uses a state machine — at each point it only listens for specific inputs:

```
SHOW_VIDEO state    → listens for Approve / Shuffle / Skip button clicks
WAIT_CAPTION state  → listens for text messages (the caption)
WAIT_PLATFORM state → listens for platform button clicks
```

This is why the caption wasn't working initially — it was registered in the wrong state.

### Key concept: Polling vs Webhooks
- **Polling** (what we use): Bot keeps asking Telegram "any new messages?" every second. Simple, works locally, no public URL needed.
- **Webhooks**: Telegram pushes messages to your server. Requires a public HTTPS URL. Better for production servers.

### Bot Setup
1. Open Telegram → search **@BotFather** → `/newbot`
2. Name: `Autopilot Reels Bot`, username: `autopilot_reels_bot`
3. Copy the token → paste as `TELEGRAM_BOT_TOKEN` in `.env`
4. Search **@userinfobot** → `/start` → copy your numeric ID → paste as `TELEGRAM_CHAT_ID`

### Conversation flow
```
/start
  ↓
sync Drive → pick random pending video
  ↓
Download video → send as Telegram video (or Drive link if too large)
  ↓ buttons appear ↓
[✅ Approve] [🔀 Shuffle] [⏭️ Skip]
  ↓ Approve clicked
"Type your caption..."
  ↓ user types caption
[📸 Instagram] [▶️ YouTube] [🚀 Both]
  ↓ platform selected
DB updated: status=approved, caption, platform saved
"🚀 Queued for upload!"
```

### Why video preview sometimes falls back to Drive link
Telegram has a 20MB upload limit via bots for video files. If the video is larger, the `send_video` call times out. The fallback sends the Drive URL instead — you can still preview it by tapping the link.

### Commands
| Command | What it does |
|---|---|
| `/start` | Syncs Drive, picks a video, starts review flow |
| `/status` | Shows count of pending/approved/uploaded/skipped |
| `/cancel` | Exits current conversation flow |
| `/default` | Uses a default caption instead of typing one |

---

## 8. Step 4 — Instagram Graph API

### What we built
- Video re-encoding with ffmpeg (H.264 + AAC LC)
- Cloudinary integration for trusted public video hosting
- 3-step Instagram Reel upload: Create Container → Wait → Publish

### Key concept: Why Instagram upload is complex
Instagram does NOT let you upload a video file directly via API. The process is:
1. Give Instagram a **public URL** to download the video from
2. Instagram downloads and processes it asynchronously
3. You poll until it's done
4. You publish the processed container

### Why we needed Cloudinary
We tried two approaches before Cloudinary:
- **Google Drive URL** → Instagram can't access it (requires auth)
- **ngrok tunnel** → Instagram's servers block/distrust free ngrok domains

Cloudinary is a trusted CDN. Instagram always accepts URLs from it. Free tier gives 25GB storage + 25GB bandwidth/month.

### Why re-encoding is needed
Even though our videos were already H.264 + AAC, Instagram requires:
- Audio profile: **LC-AAC** (Low Complexity) — NOT HE-AAC
- Pixel format: `yuv420p`
- Container: MP4 with `faststart` flag (metadata at the start)
- ffmpeg re-encoding ensures all these are correct

### Error 2207076 explained
This is Instagram's generic "video format rejected" error. It's caused by:
- Wrong audio codec profile (HE-AAC instead of LC-AAC)
- Missing `faststart` flag
- URL with spaces or special characters
- Untrusted hosting domain (like ngrok free tier)

All four of these were fixed in our final implementation.

### Instagram API Setup
1. Go to [Facebook Developers](https://developers.facebook.com/apps) → Create App → Business
2. Add **Instagram Graph API** product
3. Switch Instagram account to **Creator or Business** (not Personal)
4. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer)
5. Generate token with permissions: `instagram_basic`, `instagram_content_publish`, `pages_read_engagement`
6. Exchange for a **Long-Lived Token** (60 days):
```
GET https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id=YOUR_APP_ID
  &client_secret=YOUR_APP_SECRET
  &fb_exchange_token=YOUR_SHORT_TOKEN
```
7. Get Instagram Account ID:
```
GET https://graph.facebook.com/v19.0/me/accounts?access_token=TOKEN
→ get page_id
GET https://graph.facebook.com/v19.0/PAGE_ID?fields=instagram_business_account&access_token=TOKEN
→ get instagram_business_account.id
```

### Cloudinary Setup
1. Sign up free at [cloudinary.com](https://cloudinary.com)
2. Dashboard → copy Cloud Name, API Key, API Secret
3. Paste all three into `.env`

### The 3-step Instagram upload pipeline
```python
# Step 1: Create container (give Instagram the video URL)
POST /{ig_account_id}/media
  media_type = REELS
  video_url  = https://res.cloudinary.com/...
  caption    = "#health #reels"

# Step 2: Poll until processed
GET /{container_id}?fields=status_code,status
→ IN_PROGRESS → IN_PROGRESS → FINISHED

# Step 3: Publish
POST /{ig_account_id}/media_publish
  creation_id = {container_id}
→ returns post_id
```

### ffmpeg re-encoding command explained
```bash
ffmpeg
  -i input.mp4          # input file
  -c:v libx264          # H.264 video codec
  -profile:v high       # High profile (wide device support)
  -level 4.0            # Supports up to 1080p
  -preset fast          # Encoding speed vs compression balance
  -crf 23               # Quality (18=best, 28=worst)
  -c:a aac              # AAC audio codec
  -profile:a aac_low    # LC-AAC profile (NOT HE-AAC — Instagram requires this)
  -b:a 128k             # Audio bitrate
  -ar 44100             # 44.1kHz sample rate
  -pix_fmt yuv420p      # Pixel format required by Instagram
  -movflags +faststart  # Move metadata to start of file (required for streaming)
  -vf scale='min(1080,iw)':-2  # Max 1080px wide, keep aspect ratio
  -y output.mp4         # Overwrite output if exists
```

---

## 9. Step 5 — YouTube Data API v3

### What we built
- OAuth2 browser-based login (first time only)
- Token saved to `youtube_token.json` for automatic refresh
- Resumable chunked video upload (handles large files)
- Auto-adds `#Shorts` to description

### Key concept: YouTube Shorts
A YouTube Short is just a regular video upload with:
- Duration under 60 seconds
- `#Shorts` in title or description

YouTube auto-classifies it as a Short. No special API endpoint needed.

### Key concept: Resumable upload
```python
media = MediaFileUpload(video_path, resumable=True, chunksize=5*1024*1024)
```
Instead of uploading the whole file in one request (which fails on large files or slow connections), `resumable=True` uploads in 5MB chunks. If it fails mid-upload, it can resume from where it left off.

### YouTube API Setup
1. In your existing Google Cloud project → Enable **YouTube Data API v3**
2. Create **OAuth 2.0 Client ID** → Desktop app type
3. Configure consent screen:
   - User Type: External
   - Add scope: `https://www.googleapis.com/auth/youtube.upload`
   - Add your Google email as a test user
4. Download JSON → rename to `client_secrets.json`

### First-time auth flow
```bash
python -m services.youtube_service
# Browser opens → log in → click Allow
# youtube_token.json is created automatically
# Every subsequent run loads the token silently
```

### Token refresh
```python
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())  # silent refresh, no browser needed
```
Tokens expire but refresh automatically as long as `youtube_token.json` exists.

---

## 10. Step 6 — Upload Orchestrator & Scheduler

### What we built
- `uploader.py` — routes approved videos to the right platform(s)
- `scheduler/job.py` — APScheduler with 3x daily cron triggers
- Full cleanup pipeline (local files, Cloudinary assets)

### `uploader.py` logic
```
get_approved_videos() from DB
  ↓ for each approved video:
download_video() from Drive → local file
  ↓
if platform in (instagram, both):
    upload_reel(local_path, caption)
if platform in (youtube, both):
    upload_short(local_path, title, caption)
  ↓
if any upload succeeded:
    mark_uploaded() in DB
else:
    keep as 'approved' → will retry next cycle
  ↓
os.remove(local_path)  # always clean up
```

### `scheduler/job.py` — how APScheduler works
```python
scheduler = BackgroundScheduler()
# BackgroundScheduler runs in a separate thread
# so it doesn't block the Telegram bot's polling loop

scheduler.add_job(
    scheduled_cycle,
    trigger=CronTrigger(hour=10, minute=0),  # fires at 10:00 AM daily
)
scheduler.start()
# Now runs in background while main thread runs Telegram bot
```

### What `scheduled_cycle()` does each trigger
1. Calls `upload_approved_videos()` — uploads anything already approved
2. Calls `sync_drive_to_db()` — picks up any new videos added to Drive
3. (Telegram bot handles sending review — triggered by `/start` or separately)

### Schedule configuration
Times are set in `.env` as a comma-separated string:
```env
SCHEDULE_TIMES=10:00,15:00,20:00
```
`settings.py` parses this into a list: `["10:00", "15:00", "20:00"]`
`job.py` splits each into `(hour, minute)` and creates one cron job per time.

---

## 11. Step 7 — Streamlit Dashboard

### What we built
- Live metrics (pending/approved/uploaded/skipped counts)
- Video review panel with embedded Drive preview + action buttons
- Full video library grid with status badges
- Sidebar controls for manual sync and upload trigger
- Filter by status

### Key concept: Streamlit's execution model
Streamlit re-runs the entire `app.py` script from top to bottom every time you click a button or interact with any widget. This is why we use `st.session_state` — it persists values across re-runs.

```python
# Without session_state: review_video resets on every button click
# With session_state: value persists until explicitly changed
if "review_video" not in st.session_state:
    st.session_state.review_video = dict(random.choice(pending_videos))
```

### How the Drive preview works
```python
components.iframe(
    f"https://drive.google.com/file/d/{file_id}/preview",
    height=360
)
```
Google Drive has a built-in video player accessible at `/preview`. We embed it in an iframe — you can watch the video directly in the dashboard without downloading it.

### Running the dashboard
```bash
# In a separate terminal from main.py
streamlit run dashboard/app.py
# Opens at http://localhost:8501
```

---

## 12. Step 8 — Wiring Everything in main.py

### What `main.py` does
```python
def main():
    # 1. Initialize DB (creates table if not exists)
    init_db()

    # 2. Start scheduler in background thread
    scheduler = create_scheduler()
    scheduler.start()

    # 3. Start Telegram bot (blocks — runs forever)
    run_bot()
```

The `BackgroundScheduler` runs in its own thread while the Telegram bot's polling loop runs in the main thread. Both run simultaneously.

### Running the full system
```bash
# Terminal 1: Full system (scheduler + Telegram bot)
python main.py

# Terminal 2: Dashboard (optional, independent)
streamlit run dashboard/app.py
```

---

## 13. API Setup Guides

### Google Drive API
| Step | Action |
|---|---|
| 1 | [Google Cloud Console](https://console.cloud.google.com) → New Project → `autopilot-reels` |
| 2 | APIs & Services → Enable **Google Drive API** |
| 3 | Credentials → Create Service Account → `autopilot-drive` |
| 4 | Service Account → Keys → Add Key → JSON → download → rename `service_account.json` |
| 5 | Copy `client_email` from JSON |
| 6 | Google Drive → share your reels folder with that email (Viewer) |
| 7 | Copy folder ID from URL → `.env` as `GOOGLE_DRIVE_FOLDER_ID` |

### Telegram Bot API
| Step | Action |
|---|---|
| 1 | Telegram → @BotFather → `/newbot` |
| 2 | Name: `Autopilot Reels Bot`, username: `autopilot_reels_bot` |
| 3 | Copy token → `.env` as `TELEGRAM_BOT_TOKEN` |
| 4 | Telegram → @userinfobot → `/start` → copy ID → `.env` as `TELEGRAM_CHAT_ID` |

### Instagram Graph API
| Step | Action |
|---|---|
| 1 | [developers.facebook.com](https://developers.facebook.com/apps) → Create App → Business |
| 2 | Add Product → **Instagram Graph API** |
| 3 | Instagram → Settings → Account → Switch to Professional (Creator/Business) |
| 4 | [Graph API Explorer](https://developers.facebook.com/tools/explorer) → select your app |
| 5 | Generate token with: `instagram_basic`, `instagram_content_publish`, `pages_read_engagement` |
| 6 | Exchange for long-lived token (see URL in Section 8) |
| 7 | Get Instagram Account ID (see URLs in Section 8) |
| 8 | Paste both into `.env` |

### YouTube Data API v3
| Step | Action |
|---|---|
| 1 | Same Google Cloud project → Enable **YouTube Data API v3** |
| 2 | Credentials → Create OAuth Client ID → Desktop app |
| 3 | Configure consent screen → External → add scope `youtube.upload` → add your email as test user |
| 4 | Download JSON → rename `client_secrets.json` |
| 5 | Run `python -m services.youtube_service` → browser opens → log in → done |

### Cloudinary
| Step | Action |
|---|---|
| 1 | Sign up free at [cloudinary.com](https://cloudinary.com) |
| 2 | Dashboard → copy Cloud Name, API Key, API Secret |
| 3 | Paste all three into `.env` |
| 4 | `pip install cloudinary` |

### ffmpeg (Windows)
| Step | Action |
|---|---|
| 1 | [ffmpeg.org/download](https://ffmpeg.org/download.html) → Windows → gyan.dev builds |
| 2 | Download the full build zip → extract |
| 3 | Copy path to `bin` folder (e.g. `C:\ffmpeg\bin`) |
| 4 | Windows search → "Environment Variables" → System Variables → Path → New → paste path |
| 5 | Open new terminal → `ffmpeg -version` to verify |

---

## 14. Environment Variables Reference

```env
# ── Google Drive ──────────────────────────────────────
GOOGLE_DRIVE_FOLDER_ID=1X7eYflWAz7W_bZBiPBP2u1UUhEst1Nm7
# The folder ID from your Google Drive reels folder URL
# Just the ID — do NOT include ?usp=sharing

# ── Telegram ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN=7123456789:AAF...
# From @BotFather after creating your bot

TELEGRAM_CHAT_ID=912345678
# Your personal Telegram user ID from @userinfobot

# ── Instagram ─────────────────────────────────────────
INSTAGRAM_ACCOUNT_ID=17841400000000000
# Your Instagram Business/Creator account ID (numeric)

INSTAGRAM_ACCESS_TOKEN=EAABsbCS...
# Long-lived token (valid 60 days, needs manual refresh after)

# ── YouTube ───────────────────────────────────────────
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json
# Path to the OAuth client secrets JSON file

# ── Cloudinary ────────────────────────────────────────
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=abcdefghijklmnopqrstuvwxyz

# ── Scheduler ─────────────────────────────────────────
SCHEDULE_TIMES=10:00,15:00,20:00
# Comma-separated 24-hour times for daily upload cycles
```

### `.gitignore` — never commit these
```
.env
service_account.json
client_secrets.json
youtube_token.json
*.db
downloads/
__pycache__/
*.pyc
venv/
```

---

## 15. Common Errors & Fixes

### `ModuleNotFoundError: No module named 'config'`
**Cause:** Running a file directly instead of as a module from the project root.  
**Fix:** Always run from the `autopilot/` root using `-m`:
```bash
# Wrong
python services/drive_service.py

# Correct
python -m services.drive_service
```

### `HttpError 400 Invalid Value on orderBy`
**Cause:** Drive API `orderBy` doesn't accept `"createdTime ascending"` as a string.  
**Fix:** Use just `orderBy="createdTime"` with no direction suffix.

### `FOLDER_ID?usp=sharing` in .env
**Cause:** Copying the full sharing URL instead of just the ID.  
**Fix:** Strip everything after and including the `?`.

### Instagram Error `(#100) video_url is required`
**Cause:** Trying to upload the video file directly instead of a URL.  
**Fix:** Use Cloudinary to host the video and pass the Cloudinary URL.

### Instagram Error `2207076`
**Cause:** Video codec incompatibility — usually HE-AAC audio profile or missing faststart flag.  
**Fix:** Re-encode with ffmpeg using `-profile:a aac_low` and `-movflags +faststart`.

### Instagram `UNKNOWN` status when polling
**Cause:** Querying `error_message` field which doesn't exist for media containers.  
**Fix:** Use only `{"fields": "status_code,status"}` when polling.

### Telegram caption not responding
**Cause:** Text message handler was registered in `WAIT_PLATFORM` state instead of `WAIT_CAPTION`.  
**Fix:** Register `MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption)` in `WAIT_CAPTION` state.

### Telegram video preview `Timed out`
**Cause:** Video file is too large for Telegram's bot upload limit (~20MB).  
**Fix:** Handled gracefully — falls back to sending a Drive link instead.

### `PTBUserWarning: per_message=False`
**Cause:** APScheduler warning about ConversationHandler tracking.  
**Harmless:** Add `per_chat=True` to the ConversationHandler to suppress it.

### YouTube browser doesn't open on re-run
**Expected behaviour:** `youtube_token.json` exists from first run. Token loads silently. No browser needed again until token fully expires (usually several months).

### `streamlit.components has no attribute v1`
**Cause:** `st.components.v1` accessed without importing the module.  
**Fix:** Add `import streamlit.components.v1 as components` and use `components.iframe()`.

---

## 16. Daily Usage Guide

### Starting the system
```bash
# Activate virtual environment
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

# Terminal 1: Main system
python main.py

# Terminal 2: Dashboard (optional)
streamlit run dashboard/app.py
```

### Your daily workflow
1. At 10 AM, 3 PM, 8 PM — bot sends you a video on Telegram
2. Watch the preview (tap the Drive link if preview unavailable)
3. Tap **✅ Approve** → type your caption + hashtags → choose platform
4. At the next scheduled cycle, the video uploads automatically
5. Check the dashboard at `http://localhost:8501` for history

### Manual operations
```bash
# Manually sync Drive (pick up new videos)
python -m services.drive_service

# Manually trigger the upload cycle (upload all approved videos now)
python -m services.uploader

# Check DB status
python -c "from database.db import get_all_videos; [print(dict(v)['status'], dict(v)['filename']) for v in get_all_videos()]"

# Test Instagram connection
python -m services.instagram_service

# Test YouTube connection
python -m services.youtube_service
```

### Refreshing your Instagram token (every 60 days)
Instagram long-lived tokens expire after 60 days. Refresh them:
```
GET https://graph.facebook.com/v19.0/oauth/access_token
  ?grant_type=ig_refresh_token
  &access_token=YOUR_CURRENT_TOKEN
```
Paste the new token into `.env` as `INSTAGRAM_ACCESS_TOKEN`.

### Adding more videos
Just drop new `.mp4` files into your Google Drive folder. The next scheduler cycle (or a manual `/start` in Telegram) will pick them up automatically.

---

## Requirements

```txt
python-dotenv==1.0.1
google-api-python-client==2.131.0
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
python-telegram-bot==21.3
APScheduler==3.10.4
streamlit==1.35.0
requests==2.32.3
pyngrok==7.2.0
cloudinary==1.40.0
ffmpeg-python==0.2.0
```

---

*Built step by step, debugged line by line. Every error was a lesson.*  
*— Chandra Prakash Tripathi, April 2026*
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "autopilot.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets you access columns by name like a dict
    return conn

##initialize database for sqlite3
def init_db():
    """Creates the videos table if it doesn't exist yet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive_file_id TEXT UNIQUE NOT NULL,   -- Google Drive file ID
            filename TEXT NOT NULL,
            status TEXT DEFAULT 'pending',         -- pending | approved | uploaded | skipped
            caption TEXT,
            platform TEXT,                         -- instagram | youtube | both
            uploaded_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized.")

def add_video(drive_file_id, filename):
    """Adds a new video record with status 'pending'. Ignores if already exists."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO videos (drive_file_id, filename) VALUES (?, ?)",
            (drive_file_id, filename)
        )
        conn.commit()
    finally:
        conn.close()

def get_pending_videos():
    """Returns all videos with status = 'pending'."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE status = 'pending' ORDER BY created_at ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_status(drive_file_id, status, caption=None, platform=None):
    """Updates the status (and optionally caption/platform) of a video."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE videos
        SET status = ?,
            caption = COALESCE(?, caption),
            platform = COALESCE(?, platform),
            uploaded_at = CASE WHEN ? = 'uploaded' THEN CURRENT_TIMESTAMP ELSE uploaded_at END
        WHERE drive_file_id = ?
    """, (status, caption, platform, status, drive_file_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
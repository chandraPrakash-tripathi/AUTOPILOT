import os
from dotenv import load_dotenv

load_dotenv()  # This reads your .env file and loads everything into os.environ

# Google Drive
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Instagram
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# YouTube
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")

# Schedule times — split "10:00,15:00,20:00" into a list
SCHEDULE_TIMES = os.getenv("SCHEDULE_TIMES", "10:00,15:00,20:00").split(",")
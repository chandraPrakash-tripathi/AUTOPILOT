import logging
from scheduler.job import create_scheduler
from services.telegram_service import run_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    print("🚀 Starting Autopilot...\n")

    # 1. Initialize the database
    from database.db import init_db
    init_db()

    # 2. Start the scheduler in background
    # BackgroundScheduler runs in a separate thread
    # so it doesn't block the Telegram bot
    scheduler = create_scheduler()
    scheduler.start()
    print("✅ Scheduler started.\n")

    # 3. Start Telegram bot (this runs forever, blocking)
    # The scheduler keeps running in the background while bot polls
    print("✅ Starting Telegram bot...\n")
    run_bot()   # blocks here until Ctrl+C


if __name__ == "__main__":
    main()
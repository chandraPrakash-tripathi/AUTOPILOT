import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import SCHEDULE_TIMES
from services.drive_service import sync_drive_to_db
from services.uploader import upload_approved_videos

logger = logging.getLogger(__name__)


def scheduled_cycle():
    """
    This runs 3x per day at your configured times.
    
    Two jobs in one:
    1. Upload any videos already approved since last cycle
    2. Sync Drive so new videos appear as pending
       (Telegram bot handles sending the review — triggered separately)
    """
    print("\n⏰ Scheduler triggered — starting cycle...")

    # Job 1: Upload anything already approved
    print("\n📤 Checking for approved videos to upload...")
    upload_approved_videos()

    # Job 2: Sync Drive for new videos
    print("\n🔄 Syncing Drive for new videos...")
    sync_drive_to_db()

    print("\n✅ Cycle complete.\n")


def parse_schedule_times(times_list):
    """
    Converts ["10:00", "15:00", "20:00"] into
    cron hour/minute pairs: [(10,0), (15,0), (20,0)]
    """
    parsed = []
    for t in times_list:
        h, m = t.strip().split(":")
        parsed.append((int(h), int(m)))
    return parsed


def create_scheduler():
    """
    Creates and configures the APScheduler.
    Adds one cron job per schedule time from your .env.
    Returns the scheduler (not yet started).
    """
    scheduler = BackgroundScheduler()

    times = parse_schedule_times(SCHEDULE_TIMES)
    print(f"📅 Scheduling {len(times)} daily trigger(s):")

    for hour, minute in times:
        scheduler.add_job(
            scheduled_cycle,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=f"cycle_{hour:02d}{minute:02d}",
            name=f"Daily cycle at {hour:02d}:{minute:02d}",
            replace_existing=True
        )
        print(f"   ⏰ {hour:02d}:{minute:02d} every day")

    return scheduler


if __name__ == "__main__":
    # Test: run the cycle RIGHT NOW manually (don't wait for schedule)
    print("=== Running scheduled cycle manually ===\n")
    scheduled_cycle()
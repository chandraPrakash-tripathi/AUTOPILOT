import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)

from config.settings import TELEGRAM_BOT_TOKEN
from database.db import get_pending_videos, update_status, get_all_videos
from services.drive_service import sync_drive_to_db, download_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Conversation states ───────────────────────────────────────────
# Think of these as "what is the bot waiting for next?"
SHOW_VIDEO     = 1   # Bot just sent a video — waiting for Approve/Shuffle/Skip
WAIT_CAPTION   = 2   # User clicked Approve — waiting for them to type caption
WAIT_PLATFORM  = 3   # Caption received — waiting for platform button click


def pick_random_pending(exclude_id=None):
    """Pick a random pending video, optionally excluding one (for Shuffle)."""
    pending = get_pending_videos()
    choices = [v for v in pending if v["drive_file_id"] != exclude_id]
    return random.choice(choices) if choices else None


def review_keyboard():
    """The Approve / Shuffle / Skip inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data="approve"),
            InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle"),
        ],
        [InlineKeyboardButton("⏭️ Skip this video", callback_data="skip")]
    ])


def platform_keyboard():
    """The platform selection keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 Instagram", callback_data="plat_instagram"),
            InlineKeyboardButton("▶️ YouTube",   callback_data="plat_youtube"),
        ],
        [InlineKeyboardButton("🚀 Both Platforms", callback_data="plat_both")]
    ])


async def send_video_for_review(context, chat_id, video):
    """
    Downloads the video from Drive, sends it to Telegram as a video message,
    then deletes the local temp file. Returns the sent message.
    
    WHY download first? Telegram needs a real file or public URL.
    Drive links require auth, so we download → send → cleanup.
    """
    file_id   = video["drive_file_id"]
    filename  = video["filename"]
    drive_url = f"https://drive.google.com/file/d/{file_id}/view"

    # Tell user we're fetching it
    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏳ Fetching *{filename}* from Drive for preview...",
        parse_mode="Markdown"
    )

    local_path = None
    try:
        # Download video to local /downloads folder
        local_path = download_video(file_id, destination_folder="downloads")

        caption_text = (
            f"🎬 *{filename}*\n"
            f"🔗 [Open in Drive]({drive_url})\n\n"
            f"_Review this video and choose an action below:_"
        )

        # Send the actual video file to Telegram
        with open(local_path, "rb") as video_file:
            sent = await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=caption_text,
                parse_mode="Markdown",
                reply_markup=review_keyboard(),
                supports_streaming=True
            )

        # Delete the status message (no longer needed)
        await status_msg.delete()
        return sent

    except Exception as e:
        logger.error(f"Failed to send video preview: {e}")
        # Fallback: send just the Drive link if download/send fails
        await status_msg.edit_text(
            f"🎬 *{filename}*\n"
            f"_(Preview unavailable — file may be too large)_\n"
            f"🔗 [Open in Drive]({drive_url})\n\n"
            f"Choose an action:",
            parse_mode="Markdown",
            reply_markup=review_keyboard()
        )
        return None

    finally:
        # Always clean up the downloaded file
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
            logger.info(f"🗑️ Cleaned up temp file: {local_path}")


# ── /start ────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start — sync Drive, pick a random pending video, send for review."""
    chat_id = update.effective_chat.id

    await update.message.reply_text("🔄 Syncing videos from Google Drive...")
    sync_drive_to_db()

    video = pick_random_pending()
    if not video:
        await update.message.reply_text(
            "✅ No pending videos! All caught up.\n"
            "Add more videos to your Drive folder and send /start again."
        )
        return ConversationHandler.END

    context.user_data["current_video"] = dict(video)
    await send_video_for_review(context, chat_id, video)
    return SHOW_VIDEO   # ← Now we wait for Approve/Shuffle/Skip button


# ── Button: Shuffle ───────────────────────────────────────────────

async def handle_shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("🔀 Picking a different video...")

    current = context.user_data.get("current_video", {})
    video = pick_random_pending(exclude_id=current.get("drive_file_id"))

    if not video:
        await query.edit_message_caption("🔀 No other pending videos to shuffle to!")
        return SHOW_VIDEO

    context.user_data["current_video"] = dict(video)
    chat_id = update.effective_chat.id

    # Delete old video message, send new one
    await query.message.delete()
    await send_video_for_review(context, chat_id, video)
    return SHOW_VIDEO


# ── Button: Skip ──────────────────────────────────────────────────

async def handle_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏭️ Skipped!")

    current = context.user_data.get("current_video", {})
    if current:
        update_status(current["drive_file_id"], "skipped")

    video = pick_random_pending()
    if not video:
        await query.message.delete()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="✅ No more pending videos! Send /start to refresh."
        )
        return ConversationHandler.END

    context.user_data["current_video"] = dict(video)
    await query.message.delete()
    await send_video_for_review(context, update.effective_chat.id, video)
    return SHOW_VIDEO


# ── Button: Approve ───────────────────────────────────────────────

async def handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User approved — now ask for caption."""
    query = update.callback_query
    await query.answer("✅ Approved! Now add a caption.")

    current = context.user_data.get("current_video", {})

    await query.message.delete()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"✅ *Approved:* `{current.get('filename', 'video')}`\n\n"
            f"✏️ *Type your caption and hashtags now.*\n"
            f"Or send /default for a generic caption."
        ),
        parse_mode="Markdown"
    )
    return WAIT_CAPTION   # ← Now we wait for TEXT input


# ── Text: Caption input ───────────────────────────────────────────

async def handle_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed a caption — save it, ask for platform."""
    text = update.message.text.strip()

    if text.lower() == "/default":
        text = "🎬 Watch this! #reels #viral #trending #shorts"

    context.user_data["caption"] = text

    await update.message.reply_text(
        f"📝 *Caption saved!*\n\n_{text}_\n\n"
        f"Now choose where to post:",
        parse_mode="Markdown",
        reply_markup=platform_keyboard()
    )
    return WAIT_PLATFORM   # ← Now we wait for platform button


# ── Button: Platform selection ────────────────────────────────────

async def handle_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User picked a platform — save everything to DB as 'approved'."""
    query = update.callback_query
    await query.answer()

    platform_map = {
        "plat_instagram": "instagram",
        "plat_youtube":   "youtube",
        "plat_both":      "both"
    }
    platform = platform_map.get(query.data, "both")
    emoji    = {"instagram": "📸", "youtube": "▶️", "both": "🚀"}

    current = context.user_data.get("current_video", {})
    caption = context.user_data.get("caption", "")

    update_status(
        drive_file_id=current["drive_file_id"],
        status="approved",
        caption=caption,
        platform=platform
    )

    await query.edit_message_text(
        f"{emoji[platform]} *Queued for upload!*\n\n"
        f"📁 `{current['filename']}`\n"
        f"📝 {caption}\n"
        f"🎯 Platform: *{platform.capitalize()}*\n\n"
        f"_Send /start to review another video._",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ── /status command ───────────────────────────────────────────────

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_videos = get_all_videos()
    counts = {"pending": 0, "approved": 0, "uploaded": 0, "skipped": 0}
    for v in all_videos:
        if v["status"] in counts:
            counts[v["status"]] += 1

    await update.message.reply_text(
        f"📊 *Video Status*\n\n"
        f"⏳ Pending:  {counts['pending']}\n"
        f"✅ Approved: {counts['approved']}\n"
        f"🚀 Uploaded: {counts['uploaded']}\n"
        f"⏭️ Skipped:  {counts['skipped']}\n"
        f"📦 Total:    {len(all_videos)}",
        parse_mode="Markdown"
    )


# ── /cancel ───────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Send /start to begin again.")
    return ConversationHandler.END


# ── Bot startup ───────────────────────────────────────────────────

def run_bot():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SHOW_VIDEO: [
                # In this state, we ONLY listen for button clicks
                CallbackQueryHandler(handle_approve, pattern="^approve$"),
                CallbackQueryHandler(handle_shuffle, pattern="^shuffle$"),
                CallbackQueryHandler(handle_skip,    pattern="^skip$"),
            ],
            WAIT_CAPTION: [
                # In this state, we ONLY listen for text messages
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_caption),
                CommandHandler("default", handle_caption),
            ],
            WAIT_PLATFORM: [
                # In this state, we ONLY listen for platform button clicks
                CallbackQueryHandler(handle_platform, pattern="^plat_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False,
        per_chat=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("status", status_command))

    print("🤖 Telegram bot is running... Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
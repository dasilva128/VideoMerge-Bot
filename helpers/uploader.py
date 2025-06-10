# (c) @Savior_128

import asyncio
import time
from configs import Config
from helpers.database.access_db import db
from helpers.display_progress import progress_for_pyrogram, humanbytes
from humanfriendly import format_timespan
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified


async def UploadVideo(bot: Client, cb: CallbackQuery, merged_vid_path: str, width: int, height: int, duration: int, video_thumbnail: str | None, file_size: int) -> None:
    """
    Upload a merged video to Telegram as a video or document based on user settings.

    Args:
        bot (Client): Pyrogram Client instance.
        cb (CallbackQuery): The callback query triggering the upload.
        merged_vid_path (str): Path to the merged video file.
        width (int): Video width.
        height (int): Video height.
        duration (int): Video duration in seconds.
        video_thumbnail (str | None): Path to the thumbnail file, or None if not available.
        file_size (int): Size of the video file in bytes.
    """
    try:
        sent_ = None
        caption = Config.CAPTION.format((await bot.get_me()).username) + f"\n\n**File Name:** `{merged_vid_path.rsplit('/', 1)[-1]}`\n**Duration:** `{format_timespan(duration)}`\n**File Size:** `{humanbytes(file_size)}`"
        upload_as_doc = await db.get_upload_as_doc(cb.from_user.id)
        
        c_time = time.time()
        if not upload_as_doc:
            sent_ = await bot.send_video(
                chat_id=cb.message.chat.id,
                video=merged_vid_path,
                width=width,
                height=height,
                duration=duration,
                thumb=video_thumbnail,
                caption=caption,
                progress=progress_for_pyrogram,
                progress_args=(
                    "Uploading Video ...",
                    cb.message,
                    c_time
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Developer - @Savior_128", url="https://t.me/Savior_128")],
                        [InlineKeyboardButton("Support Group", url="https://t.me/Savior_128"),
                         InlineKeyboardButton("Bots Channel", url="https://t.me/Savior_128")]
                    ]
                ),
                parse_mode="markdown"
            )
        else:
            sent_ = await bot.send_document(
                chat_id=cb.message.chat.id,
                document=merged_vid_path,
                caption=caption,
                thumb=video_thumbnail,
                progress=progress_for_pyrogram,
                progress_args=(
                    "Uploading Video ...",
                    cb.message,
                    c_time
                ),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Developer - @Savior_128", url="https://t.me/Savior_128")],
                        [InlineKeyboardButton("Support Group", url="https://t.me/Savior_128"),
                         InlineKeyboardButton("Bots Channel", url="https://t.me/Savior_128")]
                    ]
                ),
                parse_mode="markdown"
            )
        
        await asyncio.sleep(Config.TIME_GAP)
        if Config.LOG_CHANNEL:
            forward_ = await sent_.forward(chat_id=Config.LOG_CHANNEL)
            username = cb.from_user.username or "None"
            await forward_.reply_text(
                text=f"**User:** [{cb.from_user.first_name}](tg://user?id={cb.from_user.id})\n**Username:** `{username}`\n**UserID:** `{cb.from_user.id}`",
                disable_web_page_preview=True,
                quote=True,
                parse_mode="markdown"
            )
    except MessageNotModified:
        pass  # Silently ignore if progress update fails
    except Exception as err:
        print(f"Failed to Upload Video: {err}")
        try:
            await cb.message.edit_text(f"Failed to Upload Video!\n**Error:**\n`{err}`", parse_mode="markdown")
        except MessageNotModified:
            pass
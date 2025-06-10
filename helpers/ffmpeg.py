# (c) Shrimadhav U K & @Savior_99
# FFmpeg helper functions for media processing
# Rewritten and optimized for use with Pyrogram 2.0.106 on June 10, 2025

import asyncio
import os
import time
import logging
from typing import List, Optional
from configs import Config
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified

# Configure logging
logger = logging.getLogger(__name__)

async def MergeVideo(
    input_file: str,
    user_id: str,
    message: Message,
    format_: str = "mkv"
) -> Optional[str]:
    """
    Merge multiple video files into one using FFmpeg.

    Args:
        input_file: Path to the input text file listing video files.
        user_id: User identifier for directory structure.
        message: Pyrogram Message object to update progress.
        format_: Output file extension (default: 'mkv').

    Returns:
        Path to the merged video file or None if failed.
    """
    output_file = f"{Config.DOWN_PATH}/{user_id}/[@Savior_99]_Merged.{format_.lower()}"
    file_generator_command = [
        "ffmpeg",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        input_file,
        "-c:v",
        "libx264",  # Re-encode video to avoid codec issues
        "-c:a",
        "aac",      # Re-encode audio to standard AAC
        "-y",       # Overwrite output file
        output_file
    ]

    try:
        await message.edit_text(
            "در حال ادغام ویدیوها...\n",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"Executing FFmpeg command: {' '.join(file_generator_command)}")

        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode().strip()
        stderr_str = stderr.decode().strip()
        logger.debug(f"FFmpeg stdout: {stdout_str}")
        logger.debug(f"FFmpeg stderr: {stderr_str}")

        if process.returncode != 0:
            logger.error(f"FFmpeg failed with error: {stderr_str}")
            await message.edit_text(
                f"خطا در اجرای FFmpeg: `{stderr_str}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return None

        if os.path.exists(output_file):
            logger.info(f"Merged video created: {output_file}, Size: {os.path.getsize(output_file)} bytes")
            return output_file

        logger.error("Failed to create merged video file")
        await message.edit_text(
            "خطا در ایجاد فایل ویدیویی ادغام‌شده!",
            parse_mode=ParseMode.MARKDOWN
        )
        return None

    except NotImplementedError:
        logger.error("FFmpeg not supported on this platform")
        await message.edit_text(
            "اجرای دستور FFmpeg ممکن نیست! خطای `NotImplementedError` رخ داد.\n"
            "لطفاً بات را در محیط لینوکس/یونیکس اجرا کنید.",
            parse_mode=ParseMode.MARKDOWN
        )
        return None

    except FileNotFoundError:
        logger.error("FFmpeg executable not found")
        await message.edit_text(
            "اجرای FFmpeg یافت نشد! لطفاً مطمئن شوید که FFmpeg نصب شده است.",
            parse_mode=ParseMode.MARKDOWN
        )
        return None

    except MessageNotModified:
        logger.debug("Message edit skipped due to MessageNotModified")
        pass

    except Exception as e:
        logger.error(f"MergeVideo failed: {e}")
        await message.edit_text(
            f"خطا در ادغام ویدیو: `{e}`",
            parse_mode=ParseMode.MARKDOWN
        )
        return None

async def cult_small_video(
    video_file: str,
    output_directory: str,
    start_time: int,
    end_time: int,
    format_: str
) -> Optional[str]:
    """
    Create a short sample video clip.

    Args:
        video_file: Path to input video.
        output_directory: Directory to save the output file.
        start_time: Start time for the clip in seconds.
        end_time: End time for the clip in seconds.
        format_: File extension (e.g., 'mp4', 'mkv').

    Returns:
        Path to the sample video or None if failed.
    """
    output_file = os.path.join(output_directory, f"{round(time.time())}.{format_.lower()}")
    file_generator_command = [
        "ffmpeg",
        "-i",
        video_file,
        "-ss",
        str(start_time),
        "-to",
        str(end_time),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-y",
        output_file
    ]

    try:
        logger.info(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode("utf-8").strip()
        stderr_str = stderr.decode("utf-8").strip()
        logger.debug(f"FFmpeg stdout: {stdout_str}")
        logger.debug(f"FFmpeg stderr: {stderr_str}")

        if os.path.exists(output_file):
            logger.info(f"Sample video created: {output_file}, Size: {os.path.getsize(output_file)} bytes")
            return output_file

        logger.error("Failed to create sample video")
        return None

    except FileNotFoundError:
        logger.error("FFmpeg executable not found")
        return None

    except Exception as e:
        logger.error(f"Failed to create sample video: {e}")
        return None

async def generate_screen_shots(
    video_file: str,
    output_directory: str,
    no_of_photos: int,
    duration: int
) -> List[str]:
    """
    Generate screenshots from a video.

    Args:
        video_file: Path to input video.
        output_directory: Directory to save screenshots.
        no_of_photos: Number of screenshots to generate.
        duration: Duration of the video in seconds.

    Returns:
        List of screenshot file paths.
    """
    images: List[str] = []
    ttl_step = duration // no_of_photos if no_of_photos > 0 else duration
    current_ttl = ttl_step

    for _ in range(no_of_photos):
        await asyncio.sleep(1)
        video_thumbnail = os.path.join(output_directory, f"{round(time.time())}.jpg")
        file_generator_command = [
            "ffmpeg",
            "-ss",
            str(round(current_ttl)),
            "-i",
            video_file,
            "-vframes",
            "1",
            "-y",
            video_thumbnail
        ]

        try:
            logger.info(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
            process = await asyncio.create_subprocess_exec(
                *file_generator_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode("utf-8").strip()
            stderr_str = stderr.decode("utf-8").strip()
            logger.debug(f"FFmpeg stdout: {stdout_str}")
            logger.debug(f"FFmpeg stderr: {stderr_str}")

            if os.path.exists(video_thumbnail):
                images.append(video_thumbnail)
            current_ttl += ttl_step

        except FileNotFoundError:
            logger.error("FFmpeg executable not found")
            continue

        except Exception as e:
            logger.error(f"Failed to generate screenshot: {e}")
            continue

    return images
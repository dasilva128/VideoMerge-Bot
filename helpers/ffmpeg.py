# (c) Shrimadhav U K & @AbirHasan2005
# Updated by Grok 3 for compatibility with Python 3.10 and error handling

import asyncio
import json
import os
import time
import logging
import shutil
import psutil
from typing import List, Optional, Dict
from configs import Config
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified

# Configure logging
logger = logging.getLogger(__name__)

async def get_video_info(video_file: str) -> Optional[Dict]:
    """
    Get video file information using ffprobe.

    Args:
        video_file: Path to the video file.

    Returns:
        dict: Video info (streams, format) or None if failed.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_format",
            "-show_streams",
            "-print_format",
            "json",
            video_file
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        stderr_str = stderr.decode("utf-8").strip()
        if process.returncode != 0:
            logger.error(f"ffprobe failed for {video_file}: {stderr_str}")
            return None
        return json.loads(stdout.decode("utf-8"))
    except FileNotFoundError:
        logger.error("ffprobe executable not found")
        return None
    except Exception as e:
        logger.error(f"ffprobe error for {video_file}: {e}")
        return None

async def MergeVideo(
    input_file: str,
    user_id: str,
    message: Message,
    format_: str = "mp4"  # Changed default to mp4 to match log
) -> Optional[str]:
    """
    Merge multiple video files into one using FFmpeg.

    Args:
        input_file: Path to the input text file listing video files.
        user_id: User identifier for directory structure.
        message: Pyrogram Message object to update progress.
        format_: Output file extension (default: 'mp4').

    Returns:
        Path to the merged video file or None if failed.
    """
    output_dir = f"{Config.DOWN_PATH}/{user_id}"
    output_file = os.path.join(output_dir, f"[@Savior_128]_Merged.{format_.lower()}")

    # Validate input file
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} does not exist")
        try:
            await message.edit_text(
                "فایل ورودی یافت نشد!",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    # Check disk space
    total, used, free = shutil.disk_usage(Config.DOWN_PATH)
    if free < 2_000_000_000:  # Less than 2GB free
        logger.error(f"Insufficient disk space: {free} bytes free")
        try:
            await message.edit_text(
                "فضای دیسک کافی نیست! لطفاً حداقل 2 گیگابایت فضای ذخیره‌سازی آزاد کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    # Check memory and CPU
    memory = psutil.virtual_memory()
    if memory.available < 1_000_000_000:  # Less than 1GB free
        logger.error(f"Insufficient memory: {memory.available} bytes free")
        try:
            await message.edit_text(
                "حافظه کافی نیست! لطفاً حداقل 1 گیگابایت حافظه آزاد کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None
    cpu_usage = psutil.cpu_percent()
    if cpu_usage > 95:
        logger.warning(f"High CPU usage: {cpu_usage}%")
        try:
            await message.edit_text(
                "بار پردازشی سرور بسیار بالاست! لطفاً چند دقیقه صبر کنید و دوباره امتحان کنید.",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    # Ensure output directory exists and has write permissions
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, "test.txt"), "w") as f:
            f.write("test")
        os.remove(os.path.join(output_dir, "test.txt"))
    except PermissionError:
        logger.error(f"No write permission in directory {output_dir}")
        try:
            await message.edit_text(
                "مجوز نوشتن در مسیر ذخیره‌سازی وجود ندارد! لطفاً مجوزها را بررسی کنید。",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    # Validate input video files
    try:
        with open(input_file, "r") as f:
            video_files = []
            for line in f:
                line = line.strip()
                if line and line.startswith("file "):
                    path = line[5:].strip().strip("'").strip('"')
                    if path:
                        video_files.append(path)
        if not video_files:
            logger.error("No valid video files listed in input file")
            try:
                await message.edit_text(
                    "هیچ فایل ویدیویی معتبر در لیست ورودی یافت نشد!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except MessageNotModified:
                pass
            return None

        # Get video info for first file to set reference resolution and frame rate
        first_video_info = await get_video_info(video_files[0])
        if not first_video_info:
            logger.error(f"Invalid first video file: {video_files[0]}")
            try:
                await message.edit_text(
                    f"فایل ویدیویی {video_files[0]} خراب یا نامعتبر است!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except MessageNotModified:
                pass
            return None

        video_stream = next(
            (stream for stream in first_video_info.get("streams", []) if stream.get("codec_type") == "video"),
            None
        )
        if not video_stream:
            logger.error(f"No video stream in {video_files[0]}")
            try:
                await message.edit_text(
                    f"فایل {video_files[0]} جریان ویدیویی ندارد!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except MessageNotModified:
                pass
            return None

        width = video_stream.get("width", 720)
        height = video_stream.get("height", 1280)
        if not width or not height:
            logger.error(f"Invalid resolution in {video_files[0]}")
            try:
                await message.edit_text(
                    f"رزولوشن فایل {video_files[0]} نامعتبر است!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except MessageNotModified:
                pass
            return None

        # Parse frame rate safely
        frame_rate_str = video_stream.get("r_frame_rate", "30/1")
        try:
            num, denom = map(int, frame_rate_str.split("/"))
            frame_rate = num / denom if denom != 0 else 30
        except (ValueError, ZeroDivisionError):
            logger.warning(f"Invalid frame rate {frame_rate_str}, defaulting to 30")
            frame_rate = 30

        # Validate other video files
        for video in video_files[1:]:
            if not os.path.exists(video):
                logger.error(f"Video file {video} does not exist")
                try:
                    await message.edit_text(
                        f"فایل ویدیویی {video} یافت نشد!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except MessageNotModified:
                    pass
                return None
            video_info = await get_video_info(video)
            if not video_info:
                logger.error(f"Invalid video file: {video}")
                try:
                    await message.edit_text(
                        f"فایل ویدیویی {video} خراب یا نامعتبر است!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except MessageNotModified:
                    pass
                return None

    except Exception as e:
        logger.error(f"Failed to read input file {input_file}: {e}")
        try:
            await message.edit_text(
                "خطا در خواندن فایل ورودی!",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    # FFmpeg command with scale filter to unify resolution
    file_generator_command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", input_file,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={frame_rate}",
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-y",
        output_file
    ]

    try:
        try:
            if message.text != "در حال ادغام ویدیوها...\nلطفاً صبور باشید...":
                await message.edit_text(
                    "در حال ادغام ویدیوها...\nلطفاً صبور باشید...",
                    parse_mode=ParseMode.MARKDOWN
                )
        except MessageNotModified:
            pass

        logger.info(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()  # Removed timeout for Python 3.10 compatibility
        stdout_str = stdout.decode("utf-8").strip()
        stderr_str = stderr.decode("utf-8").strip()
        logger.debug(f"FFmpeg stdout: {stdout_str}")
        logger.debug(f"FFmpeg stderr: {stderr_str}")

        if process.returncode != 0:
            logger.error(f"FFmpeg failed with error: {stderr_str}")
            try:
                await message.edit_text(
                    "خطا در ادغام ویدیوها!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except MessageNotModified:
                pass
            return None

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Merged video created: {output_file}, Size: {os.path.getsize(output_file)} bytes")
            return output_file

        logger.error("Failed to create merged video file")
        try:
            await message.edit_text(
                "خطا در ایجاد فایل ویدیویی ادغام‌شده! فایل خروجی یافت نشد یا خالی است.",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    except FileNotFoundError:
        logger.error("FFmpeg executable not found")
        try:
            await message.edit_text(
                "اجرای FFmpeg یافت نشد! لطفاً مطمئن شوید که FFmpeg نصب شده است.",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
        return None

    except Exception as e:
        logger.error(f"MergeVideo failed: {e}")
        try:
            await message.edit_text(
                "خطا در ادغام ویدیو!",
                parse_mode=ParseMode.MARKDOWN
            )
        except MessageNotModified:
            pass
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
    if start_time >= end_time or start_time < 0:
        logger.error(f"Invalid time range: start_time={start_time}, end_time={end_time}")
        return None

    os.makedirs(output_directory, exist_ok=True)
    output_file = os.path.join(output_directory, f"{round(time.time())}.{format_.lower()}")

    file_generator_command = [
        "ffmpeg",
        "-i", video_file,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        "-y",
        output_file
    ]

    try:
        video_info = await get_video_info(video_file)
        if not video_info:
            logger.error(f"Invalid video file: {video_file}")
            return None

        # Validate time range against video duration
        duration = float(video_info.get("format", {}).get("duration", 0))
        if end_time > duration:
            logger.error(f"End time {end_time} exceeds video duration {duration}")
            return None

        logger.info(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()  # Removed timeout for Python 3.10 compatibility
        stdout_str = stdout.decode("utf-8").strip()
        stderr_str = stderr.decode("utf-8").strip()
        logger.debug(f"FFmpeg stdout: {stdout_str}")
        logger.debug(f"FFmpeg stderr: {stderr_str}")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Sample video created: {output_file}, Size: {os.path.getsize(output_file)} bytes")
            return output_file

        logger.error(f"Failed to create sample video: {stderr_str}")
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
    if no_of_photos <= 0 or duration <= 0:
        logger.error(f"Invalid parameters: no_of_photos={no_of_photos}, duration={duration}")
        return images

    os.makedirs(output_directory, exist_ok=True)
    ttl_step = duration // no_of_photos
    current_ttl = ttl_step

    video_info = await get_video_info(video_file)
    if not video_info:
        logger.error(f"Invalid video file: {video_file}")
        return images

    for _ in range(no_of_photos):
        await asyncio.sleep(1)
        video_thumbnail = os.path.join(output_directory, f"{round(time.time())}.jpg")
        file_generator_command = [
            "ffmpeg",
            "-ss", str(round(current_ttl)),
            "-i", video_file,
            "-vframes", "1",
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
            stdout, stderr = await process.communicate()  # Removed timeout for Python 3.10 compatibility
            stdout_str = stdout.decode("utf-8").strip()
            stderr_str = stderr.decode("utf-8").strip()
            logger.debug(f"FFmpeg stdout: {stdout_str}")
            logger.debug(f"FFmpeg stderr: {stderr_str}")

            if os.path.exists(video_thumbnail) and os.path.getsize(video_thumbnail) > 0:
                images.append(video_thumbnail)
            current_ttl += ttl_step

        except FileNotFoundError:
            logger.error("FFmpeg executable not found")
            continue

        except Exception as e:
            logger.error(f"Failed to generate screenshot: {e}")
            continue

    return images

import asyncio
import os
import time
import logging
import shutil
import psutil
import json
from typing import List, Optional
from configs import Config
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import MessageNotModified
from configs import Config
from pyrogram.types import Message


logger = logging.getLogger(__name__)


async def MergeVideo(input_file: str, user_id: int, message: Message, format_: str):
    output_vid = os.path.join(
        Config.DOWN_PATH, str(user_id), f"Merged_{int(time.time())}.{format_.lower()}"
    )

    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", input_file, "-c", "copy", output_vid
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except NotImplementedError:
        await message.edit("❌ اجرای دستور FFmpeg پشتیبانی نمی‌شود. لطفاً روی محیط Linux/Unix اجرا کنید.")
        await asyncio.sleep(5)
        return None

    await message.edit("🔄 در حال ادغام ویدیوها... لطفاً صبور باشید.")
    stdout, stderr = await process.communicate()
    print(stderr.decode(), stdout.decode())

    if os.path.exists(output_vid):
        return output_vid
    return None


async def cut_small_video(video_file, output_dir, start_time, end_time, format_):
    out_file = os.path.join(output_dir, f"{int(time.time())}.{format_.lower()}")

    cmd = [
        "ffmpeg", "-i", video_file,
        "-ss", str(start_time), "-to", str(end_time),
        "-async", "1", "-strict", "-2",
        out_file
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    print(stderr.decode(), stdout.decode())

    if os.path.exists(out_file):
        return out_file
    return None


async def generate_screenshots(video_file, output_dir, photo_count, duration):
    images = []
    step = duration // photo_count
    current = step

    for _ in range(photo_count):
        await asyncio.sleep(1)
        img_path = os.path.join(output_dir, f"{int(time.time())}.jpg")

        cmd = [
            "ffmpeg", "-ss", str(current),
            "-i", video_file, "-vframes", "1", img_path
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        print(stderr.decode(), stdout.decode())

        images.append(img_path)
        current += step

    return images
    

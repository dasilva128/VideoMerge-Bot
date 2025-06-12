# (c) Shrimadhav U K & @AbirHasan2005
# Updated by Grok 3 for improved functionality and error handling

import asyncio
import json
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple
from configs import Config
from pyrogram.types import Message

async def ensure_directory_exists(directory: str) -> None:
    """Ensure the output directory exists, create it if it doesn't."""
    Path(directory).mkdir(parents=True, exist_ok=True)

async def get_video_info(file_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Get video and audio codec information using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_name,codec_type",
        "-of", "json",
        file_path
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            return None, None
        result = json.loads(stdout.decode().strip())
        video_codec = None
        audio_codec = None
        for stream in result.get("streams", []):
            if stream.get("codec_type") == "video":
                video_codec = stream.get("codec_name")
            elif stream.get("codec_type") == "audio":
                audio_codec = stream.get("codec_name")
        return video_codec, audio_codec
    except Exception as e:
        print(f"Error getting video info for {file_path}: {e}")
        return None, None

async def parse_input_file(input_file: str) -> List[str]:
    """Parse the input file to extract video file paths."""
    video_files = []
    try:
        with open(input_file, "r") as f:
            for line in f:
                if line.startswith("file"):
                    # Extract the file path (removing 'file' prefix and quotes)
                    path = line.strip().split(" ", 1)[1].strip("'")
                    if os.path.exists(path):
                        video_files.append(path)
    except Exception as e:
        print(f"Error parsing input file {input_file}: {e}")
    return video_files

async def MergeVideo(input_file: str, user_id: int, message: Message, format_: str) -> Optional[str]:
    """
    Merge videos together using FFmpeg concat demuxer.

    :param input_file: Path to input.txt file containing video paths.
    :param user_id: User ID as integer.
    :param message: Editable Message for showing FFmpeg progress.
    :param format_: File extension (e.g., 'mp4').
    :return: Path to merged video file or None if failed.
    """
    output_dir = f"{Config.DOWN_PATH}/{str(user_id)}"
    await ensure_directory_exists(output_dir)
    output_vid = f"{output_dir}/[@AbirHasan2005]_Merged.{format_.lower()}"

    # Check codecs of input videos
    video_files = await parse_input_file(input_file)
    if not video_files:
        await message.edit("Error: No valid video files found in input file.")
        return None

    codecs = await asyncio.gather(*(get_video_info(f) for f in video_files))
    video_codecs = {c[0] for c in codecs if c[0]}
    audio_codecs = {c[1] for c in codecs if c[1]}

    if len(video_codecs) > 1 or len(audio_codecs) > 1:
        await message.edit(
            "Warning: Input videos have different codecs. Merging with -c copy may fail.\n"
            f"Video codecs: {video_codecs}\nAudio codecs: {audio_codecs}\n"
            "Proceeding with merge, but results may be unpredictable."
        )
        await asyncio.sleep(3)

    file_generator_command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", input_file,
        "-c", "copy",
        output_vid
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except NotImplementedError:
        await message.edit(
            "Unable to execute FFmpeg command! Got `NotImplementedError`.\n"
            "Please run the bot in a Linux/Unix environment."
        )
        await asyncio.sleep(10)
        return None

    await message.edit("Merging video now...\n\nPlease be patient...")
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    print(e_response)
    print(t_response)

    if os.path.exists(output_vid):
        return output_vid
    return None

async def cut_small_video(
    video_file: str,
    output_directory: str,
    start_time: float,
    end_time: float,
    format_: str,
    accurate: bool = False
) -> Optional[str]:
    """
    Cut a small segment from a video.

    :param video_file: Path to input video file.
    :param output_directory: Directory to save output video.
    :param start_time: Start time in seconds.
    :param end_time: End time in seconds.
    :param format_: Output file extension (e.g., 'mp4').
    :param accurate: If True, re-encode for frame-accurate cutting (slower).
    :return: Path to output video file or None if failed.
    """
    await ensure_directory_exists(output_directory)
    out_put_file_name = f"{output_directory}/{str(round(time.time()))}.{format_.lower()}"

    duration = end_time - start_time
    file_generator_command = ["ffmpeg"]

    if not accurate:
        # Fast seeking (less accurate, faster)
        file_generator_command.extend(["-ss", str(start_time), "-i", video_file, "-t", str(duration)])
    else:
        # Accurate seeking (slower, frame-accurate)
        file_generator_command.extend(["-i", video_file, "-ss", str(start_time), "-t", str(duration)])

    file_generator_command.extend([
        "-async", "1",
        "-strict", "-2"
    ])

    if accurate:
        # Re-encode for accurate cutting
        file_generator_command.extend(["-c:v", "libx264", "-c:a", "aac"])
    else:
        # Copy streams for faster cutting
        file_generator_command.extend(["-c", "copy"])

    file_generator_command.append(out_put_file_name)

    process = await asyncio.create_subprocess_exec(
        *file_generator_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    print(e_response)
    print(t_response)

    if os.path.exists(out_put_file_name):
        return out_put_file_name
    return None

async def generate_screen_shots(
    video_file: str,
    output_directory: str,
    no_of_photos: int,
    duration: float
) -> List[str]:
    """
    Generate screenshots from a video at regular intervals.

    :param video_file: Path to input video file.
    :param output_directory: Directory to save screenshots.
    :param no_of_photos: Number of screenshots to generate.
    :param duration: Duration of the video in seconds.
    :return: List of paths to generated screenshot files.
    """
    await ensure_directory_exists(output_directory)
    images = []
    ttl_step = duration / no_of_photos if no_of_photos > 0 else duration
    current_ttl = ttl_step

    for _ in range(no_of_photos):
        await asyncio.sleep(1)
        video_thumbnail = f"{output_directory}/{str(round(time.time()))}.jpg"
        file_generator_command = [
            "ffmpeg",
            "-ss", str(round(current_ttl)),
            "-i", video_file,
            "-vframes", "1",
            video_thumbnail
        ]
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
        print(e_response)
        print(t_response)
        current_ttl += ttl_step
        if os.path.exists(video_thumbnail):
            images.append(video_thumbnail)

    return images

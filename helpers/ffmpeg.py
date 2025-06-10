# (c) Shrimadhav U K 

import asyncio
import os
import stat
import requests
from configs import Config
from pyrogram.types import Message

async def download_ffmpeg(url: str, destination: str) -> bool:
    """
    Download FFmpeg binary from a URL and save it to the specified destination.
    
    :param url: URL to download FFmpeg binary.
    :param destination: Path to save the FFmpeg binary.
    :return: True if download succeeds, False otherwise.
    """
    try:
        print(f"Downloading FFmpeg from {url}...")
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            # Add execute permissions
            os.chmod(destination, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)
            print(f"FFmpeg downloaded to {destination}")
            return True
        else:
            print(f"Failed to download FFmpeg: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading FFmpeg: {e}")
        return False

async def MergeVideo(input_file: str, user_id: int, message: Message, format_: str):
    """
    Merge videos together using FFmpeg.

    :param input_file: Path to input.txt file containing list of video files.
    :param user_id: User ID as integer.
    :param message: Editable Message for showing FFmpeg progress.
    :param format_: File extension (e.g., mp4, mkv).
    :return: Path to merged video file or None if failed.
    """
    output_vid = f"{Config.DOWN_PATH}/{str(user_id)}/[@savior_128]_Merged.{format_.lower()}"
    ffmpeg_path = f"{Config.DOWN_PATH}/ffmpeg"

    # Check if FFmpeg exists; if not, download it
    if not os.path.exists(ffmpeg_path):
        ffmpeg_url = "YOUR_FFMPEG_URL_HERE"  # Replace with your FFmpeg binary URL
        await message.edit("Downloading FFmpeg...")
        if not await download_ffmpeg(ffmpeg_url, ffmpeg_path):
            await message.edit("Failed to download FFmpeg!")
            return None
        await message.edit("FFmpeg downloaded successfully!")

    # Verify input.txt and video files
    if not os.path.exists(input_file):
        await message.edit(f"Input file not found: {input_file}")
        return None
    with open(input_file, 'r') as f:
        content = f.read()
        print(f"Content of input.txt:\n{content}")
        for line in content.splitlines():
            file_path = line.replace("file '", "").replace("'", "")
            if not os.path.exists(file_path):
                await message.edit(f"Video file not found: {file_path}")
                return None

    file_generator_command = [
        ffmpeg_path,
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
        output_vid
    ]
    print(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
    try:
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await message.edit("Merging Video Now ...\n\nPlease Keep Patience ...")
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
        print(f"FFmpeg stdout: {t_response}")
        print(f"FFmpeg stderr: {e_response}")
        if process.returncode != 0:
            await message.edit(f"FFmpeg failed with error: {e_response}")
            return None
        if os.path.exists(output_vid):
            print(f"Merged video created: {output_vid}, Size: {os.path.getsize(output_vid)} bytes")
            return output_vid
        else:
            await message.edit("Failed to create merged video!")
            return None
    except FileNotFoundError:
        await message.edit("FFmpeg executable not found!")
        return None
    except Exception as e:
        print(f"MergeVideo Error: {e}")
        await message.edit(f"Error during video merging: {e}")
        return None

async def cult_small_video(video_file, output_directory, start_time, end_time, format_):
    """
    Create a short sample video clip.

    :param video_file: Path to input video.
    :param output_directory: Directory to save the output.
    :param start_time: Start time for the clip.
    :param end_time: End time for the clip.
    :param format_: File extension.
    :return: Path to sample video or None if failed.
    """
    ffmpeg_path = f"{Config.DOWN_PATH}/ffmpeg"
    if not os.path.exists(ffmpeg_path):
        ffmpeg_url = "YOUR_FFMPEG_URL_HERE"  # Replace with your FFmpeg binary URL
        if not await download_ffmpeg(ffmpeg_url, ffmpeg_path):
            return None

    out_put_file_name = f"{output_directory}{str(round(time.time()))}.{format_.lower()}"
    file_generator_command = [
        ffmpeg_path,
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
        out_put_file_name
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
        print(f"FFmpeg stdout: {t_response}")
        print(f"FFmpeg stderr: {e_response}")
        if os.path.exists(out_put_file_name):
            return out_put_file_name
        else:
            return None
    except Exception as e:
        print(f"cult_small_video Error: {e}")
        return None

async def generate_screen_shots(video_file, output_directory, no_of_photos, duration):
    """
    Generate screenshots from a video.

    :param video_file: Path to input video.
    :param output_directory: Directory to save screenshots.
    :param no_of_photos: Number of screenshots to generate.
    :param duration: Duration of the video.
    :return: List of screenshot file paths.
    """
    ffmpeg_path = f"{Config.DOWN_PATH}/ffmpeg"
    if not os.path.exists(ffmpeg_path):
        ffmpeg_url = "YOUR_FFMPEG_URL_HERE"  # Replace with your FFmpeg binary URL
        if not await download_ffmpeg(ffmpeg_url, ffmpeg_path):
            return []

    images = []
    ttl_step = duration // no_of_photos
    current_ttl = ttl_step
    for _ in range(no_of_photos):
        await asyncio.sleep(1)
        video_thumbnail = f"{output_directory}/{str(time.time())}.jpg"
        file_generator_command = [
            ffmpeg_path,
            "-ss",
            str(round(current_ttl)),
            "-i",
            video_file,
            "-vframes",
            "1",
            video_thumbnail
        ]
        try:
            process = await asyncio.create_subprocess_exec(
                *file_generator_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            e_response = stderr.decode().strip()
            t_response = stdout.decode().strip()
            print(f"FFmpeg stdout: {t_response}")
            print(f"FFmpeg stderr: {e_response}")
            if os.path.exists(video_thumbnail):
                images.append(video_thumbnail)
            current_ttl += ttl_step
        except Exception as e:
            print(f"generate_screen_shots Error: {e}")
            continue
    return images

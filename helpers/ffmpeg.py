# (c) Shrimadhav U K & @AbirHasan2005

import asyncio
import os
import time
from configs import Config
from pyrogram.types import Message
from pyrogram.errors import MessageNotModified


async def MergeVideo(input_file: str, user_id: int, message: Message, format_: str) -> str | None:
    """
    Merge videos together using FFmpeg.

    Args:
        input_file (str): Path to input.txt file containing list of video files.
        user_id (int): Telegram user ID.
        message (Message): Editable message for showing FFmpeg progress.
        format_ (str): File extension (e.g., 'mp4', 'mkv').

    Returns:
        str | None: Path to merged video file or None if failed.
    """
    output_vid = f"{Config.DOWN_PATH}/{user_id}/[@AbirHasan2005]_Merged.{format_.lower()}"
    
    # Verify input.txt and video files
    if not os.path.exists(input_file):
        await message.edit_text(f"Input file not found: {input_file}", parse_mode="markdown")
        return None
    with open(input_file, "r") as f:
        content = f.read()
        print(f"Content of input.txt:\n{content}")
        for line in content.splitlines():
            file_path = line.replace("file '", "").replace("'", "")
            if not os.path.exists(file_path):
                await message.edit_text(f"Video file not found: {file_path}", parse_mode="markdown")
                return None

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
        "-y",       # Overwrite output file if it exists
        output_vid
    ]
    print(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
    
    try:
        process = await asyncio.create_subprocess_exec(
            *file_generator_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await message.edit_text("Merging Video Now ...\n\nPlease Keep Patience ...", parse_mode="markdown")
        stdout, stderr = await process.communicate()
        e_response = stderr.decode().strip()
        t_response = stdout.decode().strip()
        print(f"FFmpeg stdout: {t_response}")
        print(f"FFmpeg stderr: {e_response}")
        
        if process.returncode != 0:
            await message.edit_text(f"FFmpeg failed with error: `{e_response}`", parse_mode="markdown")
            return None
        
        if os.path.exists(output_vid):
            print(f"Merged video created: {output_vid}, Size: {os.path.getsize(output_vid)} bytes")
            return output_vid
        else:
            await message.edit_text("Failed to create merged video!", parse_mode="markdown")
            return None
    except NotImplementedError:
        await message.edit_text(
            text="Unable to Execute FFmpeg Command! Got `NotImplementedError` ...\n\nPlease run bot in a Linux/Unix Environment.",
            parse_mode="markdown"
        )
        await asyncio.sleep(5)
        return None
    except FileNotFoundError:
        await message.edit_text("FFmpeg executable not found! Please ensure FFmpeg is installed.", parse_mode="markdown")
        return None
    except MessageNotModified:
        pass  # Silently ignore MessageNotModified
    except Exception as e:
        print(f"MergeVideo Error: {e}")
        await message.edit_text(f"Error during video merging: `{e}`", parse_mode="markdown")
        return None


async def cult_small_video(video_file: str, output_directory: str, start_time: int, end_time: int, format_: str) -> str | None:
    """
    Create a short sample video clip.

    Args:
        video_file (str): Path to input video.
        output_directory (str): Directory to save the output.
        start_time (int): Start time for the clip in seconds.
        end_time (int): End time for the clip in seconds.
        format_ (str): File extension (e.g., 'mp4', 'mkv').

    Returns:
        str | None: Path to sample video or None if failed.
    """
    out_put_file_name = f"{output_directory}{round(time.time())}.{format_.lower()}"
    file_generator_command = [
        "ffmpeg",
        "-i",
        video_file,
        "-ss",
        str(start_time),
        "-to",
        str(end_time),
        "-c:v",
        "libx264",  # Re-encode video
        "-c:a",
        "aac",      # Re-encode audio
        "-y",       # Overwrite output file if it exists
        out_put_file_name
    ]
    print(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
    
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
            print(f"Sample video created: {out_put_file_name}, Size: {os.path.getsize(out_put_file_name)} bytes")
            return out_put_file_name
        return None
    except FileNotFoundError:
        print("FFmpeg executable not found")
        return None
    except Exception as e:
        print(f"cult_small_video Error: {e}")
        return None


async def generate_screen_shots(video_file: str, output_directory: str, no_of_photos: int, duration: int) -> list[str]:
    """
    Generate screenshots from a video.

    Args:
        video_file (str): Path to input video.
        output_directory (str): Directory to save screenshots.
        no_of_photos (int): Number of screenshots to generate.
        duration (int): Duration of the video in seconds.

    Returns:
        list[str]: List of screenshot file paths.
    """
    images = []
    ttl_step = duration // no_of_photos if no_of_photos > 0 else duration
    current_ttl = ttl_step
    
    for _ in range(no_of_photos):
        await asyncio.sleep(1)
        video_thumbnail = f"{output_directory}/{round(time.time())}.jpg"
        file_generator_command = [
            "ffmpeg",
            "-ss",
            str(round(current_ttl)),
            "-i",
            video_file,
            "-vframes",
            "1",
            "-y",  # Overwrite output file if it exists
            video_thumbnail
        ]
        print(f"Executing FFmpeg command: {' '.join(file_generator_command)}")
        
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
        except FileNotFoundError:
            print("FFmpeg executable not found")
            continue
        except Exception as e:
            print(f"generate_screen_shots Error: {e}")
            continue
    
    return images
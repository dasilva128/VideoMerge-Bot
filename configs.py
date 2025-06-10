# (c) @Savior_128

import os


class Config(object):
    API_ID = int(os.environ.get("API_ID", 0))  # Ensure integer, default to 0 if not set
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    SESSION_NAME = os.environ.get("SESSION_NAME", "Video-Merge-Bot")
    UPDATES_CHANNEL = os.environ.get("UPDATES_CHANNEL", None)  # Allow None for optional channel
    LOG_CHANNEL = os.environ.get("LOG_CHANNEL", None)  # Allow None for optional channel
    DOWN_PATH = os.environ.get("DOWN_PATH", "./downloads")
    TIME_GAP = int(os.environ.get("TIME_GAP", 5))
    MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS", 5))
    STREAMTAPE_API_USERNAME = os.environ.get("STREAMTAPE_API_USERNAME", "")
    STREAMTAPE_API_PASS = os.environ.get("STREAMTAPE_API_PASS", "")
    MONGODB_URI = os.environ.get("MONGODB_URI", "")
    BROADCAST_AS_COPY = bool(os.environ.get("BROADCAST_AS_COPY", False))
    BOT_OWNER = int(os.environ.get("BOT_OWNER", 5059280908))

    START_TEXT = """
Hi Unkil, I am Video Merge Bot!
I can Merge Multiple Videos in One Video. Video Formats should be same.

Made by @Savior_128
"""
    CAPTION = "Video Merged by @{}\n\nMade by @Savior_128"
    PROGRESS = """
Percentage: {0}%
Done: {1}
Total: {2}
Speed: {3}/s
ETA: {4}
"""
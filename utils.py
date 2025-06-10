import requests
import datetime
import pytz
import asyncio
from pyrogram.errors import BadRequest  # Updated for Pyrogram 2.x

def sync_time():
    """Synchronize time using a public API"""
    apis = [
        "http://worldtimeapi.org/api/timezone/UTC",
        "https://timeapi.io/api/Time/current/zone?timeZone=UTC"
    ]
    for api in apis:
        try:
            response = requests.get(api, timeout=5)
            response.raise_for_status()  # Raise exception for bad status codes
            data = response.json()
            if "datetime" in data:
                utc_time = datetime.datetime.fromisoformat(data["datetime"].replace("Z", "+00:00"))
            elif "dateTime" in data:
                utc_time = datetime.datetime.fromisoformat(data["dateTime"].replace("Z", "+00:00"))
            else:
                continue
            print(f"Synchronized time: {utc_time}")
            return utc_time
        except Exception as e:
            print(f"Error syncing time from {api}: {e}")
    print("All APIs failed, falling back to local time")
    return datetime.datetime.now(pytz.UTC)

async def run_with_retry(app, func):
    """Run a function with retry logic for BadRequest errors"""
    while True:
        try:
            await func()
            break
        except BadRequest as e:
            if "msg_id too low" in str(e).lower():
                print("msg_id error: Retrying after delay...")
                await asyncio.sleep(5)
                continue
            else:
                print(f"Other BadRequest error: {e}")
                break
        except Exception as e:
            print(f"General error: {e}")
            break
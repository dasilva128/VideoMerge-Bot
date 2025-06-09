import requests
import datetime
import pytz
import asyncio
from pyrogram.errors import BadMsgNotification

def sync_time():
    """همگام‌سازی زمان با استفاده از API عمومی"""
    apis = [
        "http://worldtimeapi.org/api/timezone/UTC",
        "https://timeapi.io/api/Time/current/zone?timeZone=UTC"
    ]
    for api in apis:
        try:
            response = requests.get(api, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if "datetime" in data:
                    utc_time = datetime.datetime.fromisoformat(data["datetime"].replace("Z", "+00:00"))
                elif "dateTime" in data:
                    utc_time = datetime.datetime.fromisoformat(data["dateTime"].replace("Z", "+00:00"))
                print(f"زمان همگام‌شده: {utc_time}")
                return utc_time
            else:
                print(f"خطا در دریافت زمان از {api}")
        except Exception as e:
            print(f"خطا در همگام‌سازی زمان از {api}: {e}")
    print("همه APIها失败 کردن، بازگشت به زمان محلی")
    return datetime.datetime.now(pytz.UTC)

async def run_with_retry(app, func):
    """اجرای تابع با مدیریت خطای BadMsgNotification"""
    while True:
        try:
            await func()
            break
        except BadMsgNotification as e:
            if "msg_id is too low" in str(e).lower():
                print("خطای msg_id: تلاش مجدد پس از تأخیر...")
                await asyncio.sleep(5)
                continue
            else:
                print(f"خطای دیگر BadMsgNotification: {e}")
                break
        except Exception as e:
            print(f"خطای عمومی: {e}")
            break

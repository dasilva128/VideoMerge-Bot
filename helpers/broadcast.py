# (c) @AbirHasan2005

import os
import time
import string
import random
import asyncio
import datetime
import aiofiles
import traceback
from configs import Config
from helpers.database.access_db import db
from pyrogram.types import Message
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid

broadcast_ids = {}


async def send_msg(user_id: int, message: Message):
    try:
        if Config.BROADCAST_AS_COPY is False:
            await message.forward(chat_id=user_id)
        else:
            await message.copy(chat_id=user_id)
        return 200, None
    except FloodWait as e:
        await asyncio.sleep(e.value)  # Updated to e.value for Pyrogram 2.x
        return await send_msg(user_id, message)  # Recursive call with await
    except InputUserDeactivated:
        return 400, f"{user_id}: Deactivated\n"
    except UserIsBlocked:
        return 400, f"{user_id}: Blocked the bot\n"
    except PeerIdInvalid:
        return 400, f"{user_id}: User ID invalid\n"
    except Exception as e:
        return 500, f"{user_id}: {traceback.format_exc()}\n"


async def broadcast_handler(m: Message):
    all_users = await db.get_all_users()
    broadcast_msg = m.reply_to_message
    if not broadcast_msg:
        await m.reply_text("Please reply to a message to broadcast!", quote=True)
        return
    while True:
        broadcast_id = ''.join(random.choice(string.ascii_letters) for _ in range(3))
        if broadcast_id not in broadcast_ids:
            break
    out = await m.reply_text(
        text="Broadcast Started! You will be notified with a log file when all users are notified."
    )
    start_time = time.time()
    total_users = await db.total_users_count()
    done = 0
    failed = 0
    success = 0
    broadcast_ids[broadcast_id] = {
        "total": total_users,
        "current": done,
        "failed": failed,
        "success": success
    }
    async with aiofiles.open("broadcast.txt", "w") as broadcast_log_file:
        async for user in all_users:
            if broadcast_ids.get(broadcast_id) is None:
                break
            sts, msg = await send_msg(
                user_id=int(user["id"]),
                message=broadcast_msg
            )
            if msg is not None:
                await broadcast_log_file.write(msg)
            if sts == 200:
                success += 1
            else:
                failed += 1
            if sts == 400:
                await db.delete_user(user["id"])
            done += 1
            broadcast_ids[broadcast_id].update({
                "current": done,
                "failed": failed,
                "success": success
            })
    if broadcast_id in broadcast_ids:
        del broadcast_ids[broadcast_id]
    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await asyncio.sleep(3)
    await out.delete()
    if failed == 0:
        await m.reply_text(
            text=f"Broadcast completed in `{completed_in}`\n\nTotal users: {total_users}\nTotal done: {done}, {success} success, {failed} failed.",
            quote=True,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await m.reply_document(
            document="broadcast.txt",
            caption=f"Broadcast completed in `{completed_in}`\n\nTotal users: {total_users}\nTotal done: {done}, {success} success, {failed} failed.",
            quote=True,
            parse_mode=ParseMode.MARKDOWN
        )
    if os.path.exists("broadcast.txt"):
        os.remove("broadcast.txt")
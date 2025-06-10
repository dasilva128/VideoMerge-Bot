# (c) @Savior_128
# Telegram Videos Merge Bot, updated for Pyrogram 2.0.106
# Updated for June 10, 2025

import os
import time
import string
import shutil
import psutil
import random
import asyncio
from PIL import Image
from configs import Config
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.enums import ParseMode

from helpers.markup_maker import MakeButtons
from helpers.streamtape import UploadToStreamtape
from helpers.clean import delete_all
from hachoir.parser import createParser
from helpers.check_gap import check_time_gap
from helpers.database.access_db import db
from helpers.database.add_user import AddUserToDatabase
from helpers.uploader import UploadVideo
from helpers.settings import OpenSettings
from helpers.forcesub import ForceSub
from hachoir.metadata import extractMetadata
from helpers.display_progress import progress_for_pyrogram, humanbytes
from helpers.broadcast import broadcast_handler
from helpers.ffmpeg import MergeVideo, generate_screen_shots, cult_small_video
from pyrogram.errors import FloodWait, UserNotParticipant, MessageNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, InputMediaPhoto

# Import functions from utils.py
try:
    from utils import sync_time, run_with_retry
except ImportError as e:
    print(f"Error importing utils: {e}")
    raise

QueueDB = {}
ReplyDB = {}
FormtDB = {}

# Remove old session file
session_file = f"{Config.SESSION_NAME}.session"
if os.path.exists(session_file):
    os.remove(session_file)
    print("Old session file deleted.")

# Print PATH for debugging (optional, consider removing in production)
print(f"PATH: {os.environ.get('PATH')}")

# Synchronize time
try:
    sync_time()
except Exception as e:
    print(f"Error synchronizing time: {e}")

# Define Client with Pyrogram 2.x syntax
NubBot = Client(
    name=Config.SESSION_NAME,
    api_id=int(Config.API_ID),
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

@NubBot.on_message(filters.private & filters.command("start"))
async def start_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    await m.reply_text(
        text=Config.START_TEXT,
        disable_web_page_preview=True,
        quote=True,
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Developer - @Savior_128", url="https://t.me/Savior_128")],
                [InlineKeyboardButton("Support Group", url="https://t.me/Savior_128"),
                 InlineKeyboardButton("Bots Channel", url="https://t.me/Savior_128")],
                [InlineKeyboardButton("Open Settings", callback_data="openSettings")],
                [InlineKeyboardButton("Close", callback_data="closeMeh")]
            ]
        )
    )



@NubBot.on_message(filters.private & filters.photo)
async def photo_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    editable = await m.reply_text("Saving Thumbnail to Database ...", quote=True)
    await db.set_thumbnail(m.from_user.id, thumbnail=m.photo.file_id)
    await editable.edit_text(
        text="Thumbnail Saved Successfully!",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Show Thumbnail", callback_data="showThumbnail")],
                [InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]
            ]
        )
    )

@NubBot.on_message(filters.private & filters.command("settings"))
async def settings_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    editable = await m.reply_text("Please Wait ...", quote=True)
    await OpenSettings(editable, m.from_user.id)

@NubBot.on_message(filters.private & filters.command("broadcast") & filters.reply & filters.user(Config.BOT_OWNER))
async def broadcast_handler_func(_, m: Message):
    await broadcast_handler(m)

@NubBot.on_message(filters.private & filters.command("status") & filters.user(Config.BOT_OWNER))
async def status_handler(_, m: Message):
    total, used, free = shutil.disk_usage(".")
    total = humanbytes(total)
    used = humanbytes(used)
    free = humanbytes(free)
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    total_users = await db.total_users_count()
    await m.reply_text(
        text=f"**Total Disk Space:** {total} \n**Used Space:** {used}({disk_usage}%) \n**Free Space:** {free} \n**CPU Usage:** {cpu_usage}% \n**RAM Usage:** {ram_usage}%\n\n**Total Users in DB:** `{total_users}`",
        parse_mode="markdown",
        quote=True
    )

@NubBot.on_message(filters.private & (filters.video | filters.document))
async def videos_handler(bot: Client, m: Message):
    await AddUserToDatabase(bot, m)
    Fsub = await ForceSub(bot, m)
    if Fsub == 400:
        return
    media = m.video or m.document
    if media.file_name is None:
        await m.reply_text("نام فایل یافت نشد!", quote=True)
        return
    if media.file_name.rsplit(".", 1)[-1].lower() not in ["mp4", "mkv", "webm"]:
        await m.reply_text("این فرمت ویدیو مجاز نیست!\nفقط MP4 یا MKV یا WEBM ارسال کنید.", quote=True)
        return
    if QueueDB.get(m.from_user.id) is None:
        QueueDB[m.from_user.id] = []
        FormtDB[m.from_user.id] = media.file_name.rsplit(".", 1)[-1].lower()
    if FormtDB.get(m.from_user.id) and (media.file_name.rsplit(".", 1)[-1].lower() != FormtDB.get(m.from_user.id)):
        await m.reply_text(f"شما ابتدا یک ویدیوی {FormtDB.get(m.from_user.id).upper()} ارسال کردید، حالا فقط همان نوع ویدیو را ارسال کنید.", quote=True)
        return
    input_ = f"{Config.DOWN_PATH}/{m.from_user.id}/input.txt"
    if os.path.exists(input_):
        await m.reply_text("متاسفم، یک فرآیند در حال انجام است!\nلطفا اسپم نکنید.", quote=True)
        return
    isInGap, sleepTime = await check_time_gap(m.from_user.id)
    if isInGap:
        await m.reply_text(f"متاسفم، ارسال سریع مجاز نیست!\nلطفا بعد از `{str(sleepTime)}` ثانیه ویدیو ارسال کنید!", quote=True)
        return
    editable = await m.reply_text("لطفا صبر کنید ...", quote=True)
    MessageText = "خب، حالا ویدیوی بعدی را بفرستید یا دکمه **ادغام کن** را بزنید!"
    QueueDB[m.from_user.id].append(m.id)
    if ReplyDB.get(m.from_user.id):
        await bot.delete_messages(chat_id=m.chat.id, message_ids=ReplyDB.get(m.from_user.id))
    if len(QueueDB[m.from_user.id]) >= Config.MAX_VIDEOS:
        MessageText = "خب، حالا فقط دکمه **ادغام کن** را بزنید!"
        markup = await MakeButtons(bot, m, QueueDB)
        await editable.edit_text(
            text=f"متاسفم، حداکثر {str(Config.MAX_VIDEOS)} ویدیو برای ادغام مجاز است!\nحالا دکمه **ادغام کن** را بزنید!",
            reply_markup=markup  # مستقیماً از markup استفاده می‌شود
        )
    else:
        markup = await MakeButtons(bot, m, QueueDB)
        await editable.edit_text(
            text="ویدیوی شما به صف اضافه شد!",
            reply_markup=markup  # مستقیماً از markup استفاده می‌شود
        )
    reply_ = await m.reply_text(
        text=f"**به صف اضافه شد!**\n\nتعداد ویدیوها در صف: `{len(QueueDB.get(m.from_user.id, []))}`\nحداکثر ویدیوهای مجاز: `{Config.MAX_VIDEOS}`",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("نمایش صف", callback_data="showQueueFiles")]]
        ),
        quote=True
    )
    ReplyDB[m.from_user.id] = reply_.id


@NubBot.on_message(filters.private & filters.command("check") & filters.user(Config.BOT_OWNER))
async def check_handler(bot: Client, m: Message):
    if len(m.command) == 2:
        editable = await m.reply_text(
            text="Checking User Details ..."
        )
        user = await bot.get_users(user_ids=int(m.command[1]))
        detail_text = f"**Name:** [{user.first_name}](tg://user?id={str(user.id)})\n" \
                      f"**Username:** `{user.username or 'None'}`\n" \
                      f"**Upload as Doc:** `{await db.get_upload_as_doc(id=int(m.command[1]))}`\n" \
                      f"**Generate Screenshots:** `{await db.get_generate_ss(id=int(m.command[1]))}`\n"
        await editable.edit_text(
            text=detail_text,
            parse_mode="markdown",
            disable_web_page_preview=True
        )

@NubBot.on_callback_query()
async def callback_handlers(bot: Client, cb: CallbackQuery):
    if "mergeNow" in cb.data:
        vid_list = []
        await cb.message.edit_text(
            text="لطفا صبر کنید ..."
        )
        # ... (بقیه کد)
        if file_size > 2097152000:
            await cb.message.edit_text(
                f"متاسفم،\n\nحجم فایل {humanbytes(file_size)} شده است!\nنمی‌توانم در تلگرام آپلود کنم!\nدر حال آپلود در Streamtape ...",
                parse_mode=ParseMode.MARKDOWN
            )
            await UploadToStreamtape(file=merged_vid_path, editable=cb.message, file_size=file_size)
            await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
            QueueDB.update({cb.from_user.id: []})
            FormtDB.update({cb.from_user.id: None})
            return
        # ... (بقیه کد)
    elif "refreshFsub" in cb.data:
        if Config.UPDATES_CHANNEL:
            try:
                user = await bot.get_chat_member(
                    chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL),
                    user_id=cb.from_user.id
                )
                if user.status == "kicked":
                    await cb.message.edit_text(
                        text="متاسفم، شما از استفاده از من منع شده‌اید. با [گروه پشتیبانی](https://t.me/Savior_128) تماس بگیرید.",
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True
                    )
                    return
            except UserNotParticipant:
                try:
                    invite_link = await bot.create_chat_invite_link(
                        chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL)
                    )
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    invite_link = await bot.create_chat_invite_link(
                        chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL)
                    )
                await cb.message.edit_text(
                    text="**شما هنوز عضو نشده‌اید ☹️، لطفاً به کانال به‌روزرسانی‌های من بپیوندید تا بتوانید از این بات استفاده کنید!**\n\nبه دلیل بار زیاد، فقط اعضای کانال می‌توانند از بات استفاده کنند!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("🤖 پیوستن به کانال به‌روزرسانی‌ها", url=invite_link.invite_link)],
                            [InlineKeyboardButton("🔄 تازه‌سازی 🔄", callback_data="refreshFsub")]
                        ]
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            except Exception:
                await cb.message.edit_text(
                    text="مشکلی پیش آمد. با [گروه پشتیبانی](https://t.me/Savior_128) تماس بگیرید.",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                return
        await cb.message.edit_text(
            text=Config.START_TEXT,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("توسعه‌دهنده - @Savior_128", url="https://t.me/Savior_128"),
                 InlineKeyboardButton("گروه پشتیبانی", url="https://t.me/Savior_128")],
                [InlineKeyboardButton("کانال بات‌ها", url="https://t.me/Savior_128")]
            ]),
            disable_web_page_preview=True)
    
                    return
            except UserNotParticipant:
                try:
                    invite_link = await bot.create_chat_invite_link(chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL))
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    invite_link = await bot.create_chat_invite_link(chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL))
                await cb.message.edit_text(
                    text="**You Still Didn't Join ☹️, Please Join My Updates Channel to use this Bot!**\n\nDue to Overload, Only Channel Subscribers can use the Bot!",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("🤖 Join Updates Channel", url=invite_link.invite_link)],
                            [InlineKeyboardButton("🔄 Refresh 🔄", callback_data="refreshFsub")]
                        ]
                    ),
                    parse_mode="markdown"
                )
                return
            except Exception:
                await cb.message.edit_text(
                    text="Something went Wrong. Contact my [Support Group](https://t.me/Savior_128).",
                    parse_mode="markdown",
                    disable_web_page_preview=True
                )
                return
        await cb.message.edit_text(
            text=Config.START_TEXT,
            parse_mode="markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Developer - @Savior_128", url="https://t.me/Savior_128"),
                 InlineKeyboardButton("Support Group", url="https://t.me/Savior_128")],
                [InlineKeyboardButton("Bots Channel", url="https://t.me/Savior_128")]
            ]),
            disable_web_page_preview=True
        )
    elif "showThumbnail" in cb.data:
        db_thumbnail = await db.get_thumbnail(cb.from_user.id)
        if db_thumbnail is not None:
            await cb.answer("Sending Thumbnail ...", show_alert=True)
            await bot.send_photo(
                chat_id=cb.message.chat.id,
                photo=db_thumbnail,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]
                    ]
                )
            )
        else:
            await cb.answer("No Thumbnail Found for you in Database!")
    elif "deleteThumbnail" in cb.data:
        await db.set_thumbnail(cb.from_user.id, thumbnail=None)
        await cb.message.edit_text("Thumbnail Deleted from Database!")
    elif "triggerUploadMode" in cb.data:
        upload_as_doc = await db.get_upload_as_doc(cb.from_user.id)
        await db.set_upload_as_doc(cb.from_user.id, not upload_as_doc)
        await OpenSettings(m=cb.message, user_id=cb.from_user.id)
    elif "showQueueFiles" in cb.data:
        try:
            markup = await MakeButtons(bot, cb.message, QueueDB)
            await cb.message.edit_text(
                text="Here are the saved files list in your queue:",
                reply_markup=InlineKeyboardMarkup(markup)
            )
        except ValueError:
            await cb.answer("Your Queue Empty Unkil!", show_alert=True)
    elif cb.data.startswith("removeFile_"):
        if (QueueDB.get(cb.from_user.id, None) is not None) and (QueueDB.get(cb.from_user.id) != []):
            QueueDB.get(cb.from_user.id).remove(int(cb.data.split("_", 1)[-1]))
            await cb.message.edit_text(
                text="File removed from queue!",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Go Back", callback_data="openSettings")]
                    ]
                )
            )
        else:
            await cb.answer("Sorry Unkil, Your Queue is Empty!", show_alert=True)
    elif "triggerGenSS" in cb.data:
        generate_ss = await db.get_generate_ss(cb.from_user.id)
        await db.set_generate_ss(cb.from_user.id, not generate_ss)
        await OpenSettings(cb.message, user_id=cb.from_user.id)
    elif "triggerGenSample" in cb.data:
        generate_sample_video = await db.get_generate_sample_video(cb.from_user.id)
        await db.set_generate_sample_video(cb.from_user.id, not generate_sample_video)
        await OpenSettings(cb.message, user_id=cb.from_user.id)
    elif "openSettings" in cb.data:
        await OpenSettings(cb.message, cb.from_user.id)
    elif cb.data.startswith("renameFile_"):
        if (QueueDB.get(cb.from_user.id, None) is None) or (QueueDB.get(cb.from_user.id) == []):
            await cb.answer("Sorry Unkil, Your Queue is Empty!", show_alert=True)
            return
        merged_vid_path = f"{Config.DOWN_PATH}/{str(cb.from_user.id)}/[@Savior_128]_Merged.{FormtDB.get(cb.from_user.id).lower()}"
        if cb.data.split("_", 1)[-1] == "Yes":
            await cb.message.edit_text("Okay Unkil,\nSend me new file name!")
            try:
                ask_ = await bot.listen(cb.message.chat.id, timeout=300)
                if ask_.text:
                    ascii_ = ''.join([i if (i in string.digits or i in string.ascii_letters or i == " ") else "" for i in ask_.text])
                    new_file_name = f"{Config.DOWN_PATH}/{str(cb.from_user.id)}/{ascii_.replace(' ', '_').rsplit('.', 1)[0]}.{FormtDB.get(cb.from_user.id).lower()}"
                    await cb.message.edit_text(f"Renaming File Name to `{new_file_name.rsplit('/', 1)[-1]}`")
                    os.rename(merged_vid_path, new_file_name)
                    await asyncio.sleep(2)
                    merged_vid_path = new_file_name
            except asyncio.TimeoutError:
                await cb.message.edit_text("Time Up!\nNow I will upload file with default name.")
                await asyncio.sleep(Config.TIME_GAP)
            except Exception:
                pass
        await cb.message.edit_text("Extracting Video Data ...")
        duration = 1
        width = 100
        height = 100
        try:
            metadata = extractMetadata(createParser(merged_vid_path))
            if metadata.has("duration"):
                duration = metadata.get('duration').seconds
            if metadata.has("width"):
                width = metadata.get("width")
            if metadata.has("height"):
                height = metadata.get("height")
        except:
            await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
            QueueDB.update({cb.from_user.id: []})
            FormtDB.update({cb.from_user.id: None})
            await cb.message.edit_text("The Merged Video Corrupted!\nTry Again Later.")
            return
        video_thumbnail = None
        db_thumbnail = await db.get_thumbnail(cb.from_user.id)
        if db_thumbnail is not None:
            video_thumbnail = await bot.download_media(message=db_thumbnail, file_name=f"{Config.DOWN_PATH}/{str(cb.from_user.id)}/thumbnail/")
            Image.open(video_thumbnail).convert("RGB").save(video_thumbnail)
            img = Image.open(video_thumbnail)
            img.resize((width, height))
            img.save(video_thumbnail, "JPEG")
        else:
            video_thumbnail = f"{Config.DOWN_PATH}/{str(cb.from_user.id)}/{str(time.time())}.jpg"
            ttl = random.randint(0, int(duration) - 1)
            file_generator_command = [
                "ffmpeg",
                "-ss",
                str(ttl),
                "-i",
                merged_vid_path,
                "-vframes",
                "1",
                video_thumbnail
            ]
            process = await asyncio.create_subprocess_exec(
                *file_generator_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if os.path.exists(video_thumbnail):
                Image.open(video_thumbnail).convert("RGB").save(video_thumbnail)
                img = Image.open(video_thumbnail)
                img.resize((width, height))
                img.save(video_thumbnail, "JPEG")
            else:
                video_thumbnail = None
        await UploadVideo(
            bot=bot,
            cb=cb,
            merged_vid_path=merged_vid_path,
            width=width,
            height=height,
            duration=duration,
            video_thumbnail=video_thumbnail,
            file_size=os.path.getsize(merged_vid_path)
        )
        caption = f"© @{(await bot.get_me()).username}"
        if await db.get_generate_ss(cb.from_user.id):
            await cb.message.edit_text("Now Generating Screenshots ...")
            generate_ss_dir = f"{Config.DOWN_PATH}/{str(cb.from_user.id)}"
            list_images = await generate_screen_shots(merged_vid_path, generate_ss_dir, 9, duration)
            if list_images is None:
                await cb.message.edit_text("Failed to get Screenshots!")
                await asyncio.sleep(Config.TIME_GAP)
            else:
                await cb.message.edit_text("Generated Screenshots Successfully!\nNow Uploading ...")
                photo_album = []
                if list_images:
                    i = 0
                    for image in list_images:
                        if os.path.exists(str(image)):
                            if i == 0:
                                photo_album.append(InputMediaPhoto(media=str(image), caption=caption))
                            else:
                                photo_album.append(InputMediaPhoto(media=str(image)))
                            i += 1
                await bot.send_media_group(
                    chat_id=cb.from_user.id,
                    media=photo_album
                )
        if (await db.get_generate_sample_video(cb.from_user.id)) and (duration >= 15):
            await cb.message.edit_text("Now Generating Sample Video ...")
            sample_vid_dir = f"{Config.DOWN_PATH}/{cb.from_user.id}/"
            ttl = int(duration * 10 / 100)
            sample_video = await cult_small_video(
                video_file=merged_vid_path,
                output_directory=sample_vid_dir,
                start_time=ttl,
                end_time=(ttl + 10),
                format_=FormtDB.get(cb.from_user.id)
            )
            if sample_video is None:
                await cb.message.edit_text("Failed to Generate Sample Video!")
                await asyncio.sleep(Config.TIME_GAP)
            else:
                await cb.message.edit_text("Successfully Generated Sample Video!\nNow Uploading ...")
                sam_vid_duration = 5
                sam_vid_width = 100
                sam_vid_height = 100
                try:
                    metadata = extractMetadata(createParser(sample_video))
                    if metadata.has("duration"):
                        sam_vid_duration = metadata.get('duration').seconds
                    if metadata.has("width"):
                        sam_vid_width = metadata.get("width")
                    if metadata.has("height"):
                        sam_vid_height = metadata.get("height")
                except:
                    await cb.message.edit_text("Sample Video File Corrupted!")
                    await asyncio.sleep(Config.TIME_GAP)
                try:
                    c_time = time.time()
                    await bot.send_video(
                        chat_id=cb.message.chat.id,
                        video=sample_video,
                        thumb=video_thumbnail,
                        width=sam_vid_width,
                        height=sam_vid_height,
                        duration=sam_vid_duration,
                        caption=caption,
                        progress=progress_for_pyrogram,
                        progress_args=(
                            "Uploading Sample Video ...",
                            cb.message,
                            c_time,
                        )
                    )
                except Exception as sam_vid_err:
                    print(f"Got Error While Trying to Upload Sample File:\n{sam_vid_err}")
                    await cb.message.edit_text("Failed to Upload Sample Video!")
                    await asyncio.sleep(Config.TIME_GAP)
        await cb.message.delete()
        await delete_all(root=f"{Config.DOWN_PATH}/{cb.from_user.id}/")
        QueueDB.update({cb.from_user.id: []})
        FormtDB.update({cb.from_user.id: None})
    elif "closeMeh" in cb.data:
        await cb.message.delete()
        if cb.message.reply_to_message:
            await cb.message.reply_to_message.delete()

# Run the bot with error handling
async def main():
    await NubBot.start()
    print("Bot started!")
    await asyncio.Event().wait()  # Keep the bot running

if __name__ == "__main__":
    NubBot.run(run_with_retry(NubBot, main))
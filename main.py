# (c) @Savior_128
# Telegram Videos Merge Bot, updated for Pyrogram 2.0.106
# Rewritten and optimized on June 10, 2025

import os
import time
import string
import shutil
import psutil
import random
import asyncio
import logging
from PIL import Image
from configs import Config
from pyromod import listen
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait, UserNotParticipant, MessageNotModified
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, InputMediaPhoto

from helpers.markup_maker import MakeButtons
from helpers.streamtape import UploadToStreamtape
from helpers.clean import delete_all
from helpers.check_gap import check_time_gap
from helpers.database.access_db import db
from helpers.database.add_user import AddUserToDatabase
from helpers.uploader import UploadVideo
from helpers.settings import OpenSettings
from helpers.forcesub import ForceSub
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from helpers.display_progress import progress_for_pyrogram, humanbytes
from helpers.broadcast import broadcast_handler
from helpers.ffmpeg import MergeVideo, generate_screen_shots, cult_small_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Try importing utils
try:
    from utils import sync_time, run_with_retry
except ImportError as e:
    logger.error(f"Failed to import utils: {e}")
    raise

# Initialize in-memory databases
QueueDB = {}
ReplyDB = {}
FormtDB = {}

# Remove old session file
session_file = f"{Config.SESSION_NAME}.session"
if os.path.exists(session_file):
    os.remove(session_file)
    logger.info("Old session file deleted.")

# Synchronize system time
try:
    sync_time()
except Exception as e:
    logger.warning(f"Failed to synchronize time: {e}")

# Initialize Pyrogram Client
NubBot = Client(
    name=Config.SESSION_NAME,
    api_id=int(Config.API_ID),
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

async def handle_flood_wait(e: FloodWait) -> None:
    """Handle FloodWait exceptions by waiting the required time."""
    await asyncio.sleep(e.value)

async def get_channel_invite_link(bot: Client, channel_id: str) -> str:
    """Generate an invite link for the updates channel."""
    channel = int(channel_id) if channel_id.startswith("-100") else channel_id
    try:
        invite = await bot.create_chat_invite_link(chat_id=channel)
        return invite.invite_link
    except FloodWait as e:
        await handle_flood_wait(e)
        invite = await bot.create_chat_invite_link(chat_id=channel)
        return invite.invite_link

@NubBot.on_message(filters.private & filters.command("start"))
async def start_handler(bot: Client, m: Message):
    """Handle /start command."""
    await AddUserToDatabase(bot, m)
    if await ForceSub(bot, m) == 400:
        return
    await m.reply_text(
        text=Config.START_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        quote=True,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("توسعه‌دهنده - @Savior_128", url="https://t.me/Savior_128")],
            [InlineKeyboardButton("گروه پشتیبانی", url="https://t.me/Savior_128"),
             InlineKeyboardButton("کانال بات‌ها", url="https://t.me/Savior_128")],
            [InlineKeyboardButton("تنظیمات", callback_data="openSettings")],
            [InlineKeyboardButton("بستن", callback_data="closeMeh")]
        ])
    )

@NubBot.on_message(filters.private & filters.photo)
async def photo_handler(bot: Client, m: Message):
    """Handle photo messages to save as thumbnail."""
    await AddUserToDatabase(bot, m)
    if await ForceSub(bot, m) == 400:
        return
    editable = await m.reply_text("در حال ذخیره تصویر کوچک در پایگاه داده ...", quote=True)
    await db.set_thumbnail(m.from_user.id, thumbnail=m.photo.file_id)
    await editable.edit_text(
        text="تصویر کوچک با موفقیت ذخیره شد!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("نمایش تصویر کوچک", callback_data="showThumbnail")],
            [InlineKeyboardButton("حذف تصویر کوچک", callback_data="deleteThumbnail")]
        ])
    )

@NubBot.on_message(filters.private & filters.command("settings"))
async def settings_handler(bot: Client, m: Message):
    """Handle /settings command."""
    await AddUserToDatabase(bot, m)
    if await ForceSub(bot, m) == 400:
        return
    editable = await m.reply_text("لطفاً صبر کنید ...", quote=True)
    await OpenSettings(editable, m.from_user.id)

@NubBot.on_message(filters.private & filters.command("broadcast") & filters.reply & filters.user(Config.BOT_OWNER))
async def broadcast_handler_func(_, m: Message):
    """Handle /broadcast command for bot owner."""
    await broadcast_handler(m)

@NubBot.on_message(filters.private & filters.command("status") & filters.user(Config.BOT_OWNER))
async def status_handler(_, m: Message):
    """Handle /status command for bot owner."""
    total, used, free = shutil.disk_usage(".")
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    total_users = await db.total_users_count()
    await m.reply_text(
        text=(
            f"**فضای کل دیسک:** {humanbytes(total)}\n"
            f"**فضای استفاده‌شده:** {humanbytes(used)} ({disk_usage}%)\n"
            f"**فضای آزاد:** {humanbytes(free)}\n"
            f"**استفاده از CPU:** {cpu_usage}%\n"
            f"**استفاده از RAM:** {ram_usage}%\n\n"
            f"**تعداد کل کاربران در پایگاه داده:** `{total_users}`"
        ),
        parse_mode=ParseMode.MARKDOWN,
        quote=True
    )

@NubBot.on_message(filters.private & (filters.video | filters.document))
async def videos_handler(bot: Client, m: Message):
    """Handle video or document messages for merging."""
    await AddUserToDatabase(bot, m)
    if await ForceSub(bot, m) == 400:
        return
    media = m.video or m.document
    if media.file_name is None:
        await m.reply_text("نام فایل یافت نشد!", quote=True)
        return
    file_ext = media.file_name.rsplit(".", 1)[-1].lower()
    if file_ext not in ["mp4", "mkv", "webm"]:
        await m.reply_text("این فرمت ویدیو مجاز نیست!\nفقط MP4، MKV یا WEBM ارسال کنید.", quote=True)
        return
    user_id = m.from_user.id
    if QueueDB.get(user_id) is None:
        QueueDB[user_id] = []
        FormtDB[user_id] = file_ext
    if FormtDB.get(user_id) and file_ext != FormtDB.get(user_id):
        await m.reply_text(
            f"شما ابتدا یک ویدیوی {FormtDB.get(user_id).upper()} ارسال کردید، حالا فقط همان نوع ویدیو را ارسال کنید.",
            quote=True
        )
        return
    input_path = f"{Config.DOWN_PATH}/{user_id}/input.txt"
    if os.path.exists(input_path):
        await m.reply_text("یک فرآیند در حال انجام است!\nلطفاً اسپم نکنید.", quote=True)
        return
    is_in_gap, sleep_time = await check_time_gap(user_id)
    if is_in_gap:
        await m.reply_text(
            f"ارسال سریع مجاز نیست!\nلطفاً پس از `{sleep_time}` ثانیه دوباره تلاش کنید!",
            quote=True
        )
        return
    editable = await m.reply_text("لطفاً صبر کنید ...", quote=True)
    QueueDB[user_id].append(m.id)
    if ReplyDB.get(user_id):
        await bot.delete_messages(chat_id=m.chat.id, message_ids=ReplyDB.get(user_id))
    message_text = (
        "خب، حالا ویدیوی بعدی را بفرستید یا دکمه **ادغام کن** را بزنید!"
        if len(QueueDB[user_id]) < Config.MAX_VIDEOS
        else f"حداکثر {Config.MAX_VIDEOS} ویدیو مجاز است!\nحالا دکمه **ادغام کن** را بزنید!"
    )
    markup = await MakeButtons(bot, m, QueueDB)
    await editable.edit_text(
        text="ویدیوی شما به صف اضافه شد!" if len(QueueDB[user_id]) < Config.MAX_VIDEOS else message_text,
        reply_markup=markup
    )
    reply_ = await m.reply_text(
        text=f"**به صف اضافه شد!**\n\nتعداد ویدیوها در صف: `{len(QueueDB[user_id])}`\nحداکثر ویدیوهای مجاز: `{Config.MAX_VIDEOS}`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("نمایش صف", callback_data="showQueueFiles")]]),
        quote=True
    )
    ReplyDB[user_id] = reply_.id

@NubBot.on_message(filters.private & filters.command("check") & filters.user(Config.BOT_OWNER))
async def check_handler(bot: Client, m: Message):
    """Handle /check command for bot owner."""
    if len(m.command) != 2:
        await m.reply_text("لطفاً یک شناسه کاربر وارد کنید!", quote=True)
        return
    editable = await m.reply_text("در حال بررسی اطلاعات کاربر ...")
    try:
        user = await bot.get_users(int(m.command[1]))
        detail_text = (
            f"**نام:** [{user.first_name}](tg://user?id={user.id})\n"
            f"**نام کاربری:** `{user.username or 'ندارد'}`\n"
            f"**آپلود به‌صورت سند:** `{await db.get_upload_as_doc(user.id)}`\n"
            f"**تولید تصاویر کوچک:** `{await db.get_generate_ss(user.id)}`\n"
        )
        await editable.edit_text(
            text=detail_text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception as e:
        await editable.edit_text(f"خطا در بررسی کاربر: `{e}`", parse_mode=ParseMode.MARKDOWN)

@NubBot.on_callback_query()
async def callback_handlers(bot: Client, cb: CallbackQuery):
    """Handle all callback queries."""
    user_id = cb.from_user.id
    data = cb.data

    if data == "mergeNow":
        await cb.message.edit_text("لطفاً صبر کنید ...")
        vid_list = []
        duration = 0
        list_message_ids = QueueDB.get(user_id, [])
        if not list_message_ids:
            await cb.answer("صف خالی است!", show_alert=True)
            await cb.message.delete()
            return
        list_message_ids.sort()
        input_path = f"{Config.DOWN_PATH}/{user_id}/input.txt"
        if len(list_message_ids) < 2:
            await cb.answer("حداقل دو ویدیو برای ادغام نیاز است!", show_alert=True)
            await cb.message.delete()
            return
        os.makedirs(f"{Config.DOWN_PATH}/{user_id}/", exist_ok=True)
        for msg in await bot.get_messages(chat_id=user_id, message_ids=list_message_ids):
            media = msg.video or msg.document
            try:
                await cb.message.edit_text(f"در حال دانلود `{media.file_name}` ...")
            except MessageNotModified:
                QueueDB[user_id].remove(msg.id)
                await cb.message.edit_text("فایل نادیده گرفته شد!")
                await asyncio.sleep(3)
                continue
            try:
                c_time = time.time()
                file_dl_path = await bot.download_media(
                    message=msg,
                    file_name=f"{Config.DOWN_PATH}/{user_id}/{msg.id}/",
                    progress=progress_for_pyrogram,
                    progress_args=("در حال دانلود ...", cb.message, c_time)
                )
            except Exception as e:
                logger.error(f"Download failed for file {media.file_name}: {e}")
                QueueDB[user_id].remove(msg.id)
                await cb.message.edit_text("فایل نادیده گرفته شد!")
                await asyncio.sleep(3)
                continue
            try:
                metadata = extractMetadata(createParser(file_dl_path))
                if metadata and metadata.has("duration"):
                    duration += metadata.get("duration").seconds
                vid_list.append(f"file '{file_dl_path}'")
            except Exception as e:
                logger.error(f"Metadata extraction failed: {e}")
                await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
                QueueDB[user_id] = []
                FormtDB[user_id] = None
                await cb.message.edit_text("ویدیو خراب است!\nبعداً دوباره امتحان کنید.")
                return
        vid_list = list(dict.fromkeys(vid_list))  # Remove duplicates
        if len(vid_list) < 2:
            await cb.message.edit_text("فقط یک ویدیو در صف وجود دارد!\nممکن است ویدیوی تکراری ارسال کرده باشید.")
            return
        await cb.message.edit_text("در حال ادغام ویدیوها ...")
        with open(input_path, 'w') as f:
            f.write("\n".join(vid_list))
        merged_vid_path = await MergeVideo(
            input_file=input_path,
            user_id=user_id,
            message=cb.message,
            format_=FormtDB.get(user_id, "mkv")
        )
        if not merged_vid_path:
            await cb.message.edit_text("خطا در ادغام ویدیو!")
            await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
            QueueDB[user_id] = []
            FormtDB[user_id] = None
            return
        await cb.message.edit_text("ویدیو با موفقیت ادغام شد!")
        await asyncio.sleep(Config.TIME_GAP)
        file_size = os.path.getsize(merged_vid_path)
        if file_size > 2097152000:
            await cb.message.edit_text(
                f"حجم فایل {humanbytes(file_size)} است!\nنمی‌توان در تلگرام آپلود کرد!\nدر حال آپلود به Streamtape ..."
            )
            await UploadToStreamtape(file=merged_vid_path, editable=cb.message, file_size=file_size)
            await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
            QueueDB[user_id] = []
            FormtDB[user_id] = None
            return
        await cb.message.edit_text(
            text="آیا می‌خواهید نام فایل را تغییر دهید؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("بله", callback_data="renameFile_Yes")],
                [InlineKeyboardButton("خیر", callback_data="renameFile_No")]
            ])
        )

    elif data == "refreshFsub" and Config.UPDATES_CHANNEL:
        try:
            user = await bot.get_chat_member(
                chat_id=(int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL),
                user_id=user_id
            )
            if user.status == "kicked":
                await cb.message.edit_text(
                    text="شما از استفاده از بات منع شده‌اید. با [گروه پشتیبانی](https://t.me/Savior_128) تماس بگیرید.",
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
            invite_link = await get_channel_invite_link(bot, Config.UPDATES_CHANNEL)
            await cb.message.edit_text(
                text=(
                    "**شما هنوز عضو کانال نشده‌اید ☹️**\n"
                    "لطفاً به کانال به‌روزرسانی‌ها بپیوندید تا بتوانید از بات استفاده کنید!\n"
                    "به دلیل بار زیاد، فقط اعضای کانال می‌توانند از بات استفاده کنند."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 پیوستن به کانال", url=invite_link)],
                    [InlineKeyboardButton("🔄 تازه‌سازی", callback_data="refreshFsub")]
                ])
            )
            return
        except Exception as e:
            logger.error(f"Error in refreshFsub: {e}")
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
            disable_web_page_preview=True
        )

    elif data == "showThumbnail":
        db_thumbnail = await db.get_thumbnail(user_id)
        if db_thumbnail:
            await cb.answer("در حال ارسال تصویر کوچک ...", show_alert=True)
            await bot.send_photo(
                chat_id=cb.message.chat.id,
                photo=db_thumbnail,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("حذف تصویر کوچک", callback_data="deleteThumbnail")]])
            )
        else:
            await cb.answer("هیچ تصویر کوچکی در پایگاه داده یافت نشد!")

    elif data == "deleteThumbnail":
        await db.set_thumbnail(user_id, thumbnail=None)
        await cb.message.edit_text("تصویر کوچک از پایگاه داده حذف شد!")

    elif data == "triggerUploadMode":
        upload_as_doc = await db.get_upload_as_doc(user_id)
        await db.set_upload_as_doc(user_id, not upload_as_doc)
        await OpenSettings(cb.message, user_id)

    elif data == "showQueueFiles":
        try:
            markup = await MakeButtons(bot, cb.message, QueueDB)
            await cb.message.edit_text(
                text="لیست فایل‌های موجود در صف شما:",
                reply_markup=markup
            )
        except ValueError:
            await cb.answer("صف شما خالی است!", show_alert=True)

    elif data.startswith("removeFile_"):
        if QueueDB.get(user_id, []):
            QueueDB[user_id].remove(int(data.split("_", 1)[-1]))
            await cb.message.edit_text(
                text="فایل از صف حذف شد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("بازگشت", callback_data="openSettings")]])
            )
        else:
            await cb.answer("صف شما خالی است!", show_alert=True)

    elif data == "triggerGenSS":
        generate_ss = await db.get_generate_ss(user_id)
        await db.set_generate_ss(user_id, not generate_ss)
        await OpenSettings(cb.message, user_id)

    elif data == "triggerGenSample":
        generate_sample_video = await db.get_generate_sample_video(user_id)
        await db.set_generate_sample_video(user_id, not generate_sample_video)
        await OpenSettings(cb.message, user_id)

    elif data == "openSettings":
        await OpenSettings(cb.message, user_id)

    elif data.startswith("renameFile_"):
        if not QueueDB.get(user_id, []):
            await cb.answer("صف شما خالی است!", show_alert=True)
            return
        merged_vid_path = f"{Config.DOWN_PATH}/{user_id}/[@Savior_128]_Merged.{FormtDB.get(user_id, 'mkv').lower()}"
        if data == "renameFile_Yes":
            await cb.message.edit_text("لطفاً نام جدید فایل را ارسال کنید!")
            try:
                ask = await bot.listen(cb.message.chat.id, timeout=300)
                if ask.text:
                    ascii_name = ''.join(i for i in ask.text if i in string.digits or i in string.ascii_letters or i == " ")
                    new_file_name = f"{Config.DOWN_PATH}/{user_id}/{ascii_name.replace(' ', '_').rsplit('.', 1)[0]}.{FormtDB.get(user_id, 'mkv').lower()}"
                    await cb.message.edit_text(f"در حال تغییر نام به `{new_file_name.rsplit('/', 1)[-1]}`")
                    os.rename(merged_vid_path, new_file_name)
                    await asyncio.sleep(2)
                    merged_vid_path = new_file_name
            except asyncio.TimeoutError:
                await cb.message.edit_text("زمان به پایان رسید!\nفایل با نام پیش‌فرض آپلود می‌شود.")
                await asyncio.sleep(Config.TIME_GAP)
            except Exception as e:
                logger.error(f"Error renaming file: {e}")
        await cb.message.edit_text("در حال استخراج اطلاعات ویدیو ...")
        duration, width, height = 1, 100, 100
        try:
            metadata = extractMetadata(createParser(merged_vid_path))
            if metadata:
                if metadata.has("duration"):
                    duration = metadata.get("duration").seconds
                if metadata.has("width"):
                    width = metadata.get("width")
                if metadata.has("height"):
                    height = metadata.get("height")
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
            QueueDB[user_id] = []
            FormtDB[user_id] = None
            await cb.message.edit_text("ویدیوی ادغام‌شده خراب است!\nبعداً دوباره امتحان کنید.")
            return
        video_thumbnail = None
        db_thumbnail = await db.get_thumbnail(user_id)
        if db_thumbnail:
            video_thumbnail = await bot.download_media(
                message=db_thumbnail,
                file_name=f"{Config.DOWN_PATH}/{user_id}/thumbnail/"
            )
            with Image.open(video_thumbnail).convert("RGB") as img:
                img.resize((width, height)).save(video_thumbnail, "JPEG")
        else:
            video_thumbnail = f"{Config.DOWN_PATH}/{user_id}/{time.time()}.jpg"
            ttl = random.randint(0, duration - 1)
            file_generator_command = [
                "ffmpeg", "-ss", str(ttl), "-i", merged_vid_path, "-vframes", "1", video_thumbnail
            ]
            process = await asyncio.create_subprocess_exec(
                *file_generator_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if os.path.exists(video_thumbnail):
                with Image.open(video_thumbnail).convert("RGB") as img:
                    img.resize((width, height)).save(video_thumbnail, "JPEG")
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
        if await db.get_generate_ss(user_id):
            await cb.message.edit_text("در حال تولید تصاویر کوچک ...")
            generate_ss_dir = f"{Config.DOWN_PATH}/{user_id}"
            list_images = await generate_screen_shots(merged_vid_path, generate_ss_dir, 9, duration)
            if not list_images:
                await cb.message.edit_text("خطا در تولید تصاویر کوچک!")
                await asyncio.sleep(Config.TIME_GAP)
            else:
                await cb.message.edit_text("تصاویر کوچک با موفقیت تولید شدند!\nدر حال آپلود ...")
                photo_album = [
                    InputMediaPhoto(media=image, caption=caption if i == 0 else "")
                    for i, image in enumerate(list_images)
                    if os.path.exists(image)
                ]
                if photo_album:
                    await bot.send_media_group(chat_id=user_id, media=photo_album)
        if await db.get_generate_sample_video(user_id) and duration >= 15:
            await cb.message.edit_text("در حال تولید ویدیوی نمونه ...")
            sample_vid_dir = f"{Config.DOWN_PATH}/{user_id}/"
            ttl = int(duration * 10 / 100)
            sample_video = await cult_small_video(
                video_file=merged_vid_path,
                output_directory=sample_vid_dir,
                start_time=ttl,
                end_time=ttl + 10,
                format_=FormtDB.get(user_id)
            )
            if not sample_video:
                await cb.message.edit_text("خطا در تولید ویدیوی نمونه!")
                await asyncio.sleep(Config.TIME_GAP)
            else:
                await cb.message.edit_text("ویدیوی نمونه با موفقیت تولید شد!\nدر حال آپلود ...")
                sam_vid_duration, sam_vid_width, sam_vid_height = 5, 100, 100
                try:
                    metadata = extractMetadata(createParser(sample_video))
                    if metadata:
                        if metadata.has("duration"):
                            sam_vid_duration = metadata.get("duration").seconds
                        if metadata.has("width"):
                            sam_vid_width = metadata.get("width")
                        if metadata.has("height"):
                            sam_vid_height = metadata.get("height")
                except Exception as e:
                    logger.error(f"Sample video metadata extraction failed: {e}")
                    await cb.message.edit_text("فایل ویدیوی نمونه خراب است!")
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
                        progress_args=("در حال آپلود ویدیوی نمونه ...", cb.message, c_time)
                    )
                except Exception as e:
                    logger.error(f"Failed to upload sample video: {e}")
                    await cb.message.edit_text("خطا در آپلود ویدیوی نمونه!")
                    await asyncio.sleep(Config.TIME_GAP)
        await cb.message.delete()
        await delete_all(root=f"{Config.DOWN_PATH}/{user_id}/")
        QueueDB[user_id] = []
        FormtDB[user_id] = None

    elif data == "closeMeh":
        await cb.message.delete()
        if cb.message.reply_to_message:
            await cb.message.reply_to_message.delete()

async def main():
    """Main function to start the bot."""
    try:
        await NubBot.start()
        logger.info("Bot started successfully!")
        await asyncio.Event().wait()  # Keep bot running
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
    finally:
        await NubBot.stop()

if __name__ == "__main__":
    NubBot.run(run_with_retry(NubBot, main))
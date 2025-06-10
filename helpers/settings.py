# (c) @AbirHasan2005

import asyncio
from helpers.database.access_db import db
from pyrogram.errors import MessageNotModified, FloodWait
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


async def OpenSettings(m: Message, user_id: int) -> None:
    """
    Display a settings menu for the user to configure bot options.

    Args:
        m (Message): The message to edit with the settings menu.
        user_id (int): The Telegram user ID.

    Raises:
        Exception: If an unexpected error occurs during message editing.
    """
    try:
        upload_as_doc = await db.get_upload_as_doc(id=user_id)
        generate_sample = await db.get_generate_sample_video(id=user_id)
        generate_ss = await db.get_generate_ss(id=user_id)
        
        await m.edit_text(
            text="Here You Can Change or Configure Your Settings:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(
                        f"Upload as {'Video' if not upload_as_doc else 'Document'} ✅",
                        callback_data="triggerUploadMode"
                    )],
                    [InlineKeyboardButton(
                        f"Generate Sample Video {'✅' if generate_sample else '❌'}",
                        callback_data="triggerGenSample"
                    )],
                    [InlineKeyboardButton(
                        f"Generate Screenshots {'✅' if generate_ss else '❌'}",
                        callback_data="triggerGenSS"
                    )],
                    [InlineKeyboardButton("Show Thumbnail", callback_data="showThumbnail")],
                    [InlineKeyboardButton("Show Queue Files", callback_data="showQueueFiles")],
                    [InlineKeyboardButton("Close", callback_data="closeMeh")]
                ]
            )
        )
    except MessageNotModified:
        pass  # Silently ignore if the message content hasn't changed
    except FloodWait as e:
        await asyncio.sleep(e.value)  # Updated to e.value for Pyrogram 2.x
        await m.edit_text("You Are Spamming!")
    except Exception as err:
        print(f"Error in OpenSettings: {err}")
        raise err
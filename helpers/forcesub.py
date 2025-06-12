# (c) @AbirHasan2005

import asyncio
from configs import Config
from pyrogram import Client
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message


async def ForceSub(bot: Client, cmd: Message) -> int:
    """
    Check if a user is subscribed to the updates channel and prompt them to join if not.

    Args:
        bot (Client): Pyrogram Client instance.
        cmd (Message): The incoming message to check.

    Returns:
        int: 200 if the user is subscribed or no channel is set, 400 if action is needed (e.g., user must join or is banned).
    """
    if not Config.UPDATES_CHANNEL:
        return 200  # No force-sub required if UPDATES_CHANNEL is not set

    try:
        channel_id = int(Config.UPDATES_CHANNEL) if Config.UPDATES_CHANNEL.startswith("-100") else Config.UPDATES_CHANNEL
        invite_link = await bot.create_chat_invite_link(chat_id=channel_id)
    except FloodWait as e:
        await asyncio.sleep(e.value)  # Updated to e.value for Pyrogram 2.x
        invite_link = await bot.create_chat_invite_link(chat_id=channel_id)
    except Exception as err:
        print(f"Unable to create invite link for {Config.UPDATES_CHANNEL}: {err}")
        await cmd.reply_text(
            text="Something went wrong. Contact my [Support Group](https://t.me/Savior_128).",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return 400

    try:
        user = await bot.get_chat_member(chat_id=channel_id, user_id=cmd.from_user.id)
        if user.status == "kicked":
            await cmd.reply_text(
                text="Sorry Sir, You are Banned to use me. Contact my [Support Group](https://t.me/Savior_128).",
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            return 400
    except UserNotParticipant:
        await cmd.reply_text(
            text="**Please Join My Updates Channel to use this Bot!**\n\nDue to Overload, Only Channel Subscribers can use the Bot!",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🤖 Join Updates Channel", url=invite_link.invite_link)],
                    [InlineKeyboardButton("🔄 Refresh 🔄", callback_data="refreshFsub")]
                ]
            ),
            parse_mode=ParseMode.MARKDOWN
        )
        return 400
    except Exception as err:
        print(f"Error checking user subscription: {err}")
        await cmd.reply_text(
            text="Something went wrong. Contact my [Support Group](https://t.me/Savior_128).",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        return 400
    return 200
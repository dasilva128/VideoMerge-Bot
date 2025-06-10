# (c) @AbirHasan2005

from pyrogram import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message


async def MakeButtons(bot: Client, m: Message, db: dict) -> InlineKeyboardMarkup:
    """
    Generate inline keyboard buttons for video files in the user's queue.

    Args:
        bot (Client): Pyrogram Client instance.
        m (Message): The incoming message context.
        db (dict): Dictionary containing user queue data (e.g., QueueDB).

    Returns:
        InlineKeyboardMarkup: Markup with buttons for video files, merge, and clear actions.

    Raises:
        ValueError: If the queue is empty for the user.
    """
    markup = []
    user_queue = db.get(m.chat.id, [])
    if not user_queue:
        raise ValueError("No files in queue")

    messages = await bot.get_messages(chat_id=m.chat.id, message_ids=user_queue)
    for msg in messages:
        media = msg.video or msg.document
        if media and media.file_name:
            markup.append([InlineKeyboardButton(
                media.file_name,
                callback_data=f"showFileName_{msg.id}"  # Updated to msg.id
            )])
    
    markup.append([InlineKeyboardButton("Merge Now", callback_data="mergeNow")])
    markup.append([InlineKeyboardButton("Clear Files", callback_data="cancelProcess")])
    return InlineKeyboardMarkup(markup)
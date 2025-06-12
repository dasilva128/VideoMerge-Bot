# (c) @Savior_128

import aiohttp
from configs import Config
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import MessageNotModified
from helpers.display_progress import humanbytes


async def UploadToStreamtape(file: str, editable: Message, file_size: int) -> None:
    """
    Upload a file to Streamtape and update the message with the download link.

    Args:
        file (str): Path to the file to upload.
        editable (Message): The message to edit with upload status.
        file_size (int): Size of the file in bytes.
    """
    try:
        async with aiohttp.ClientSession() as session:
            main_api = "https://api.streamtape.com/file/ul?login={}&key={}"
            async with session.get(main_api.format(Config.STREAMTAPE_API_USERNAME, Config.STREAMTAPE_API_PASS)) as hit_api:
                hit_api.raise_for_status()  # Raise exception for bad status codes
                json_data = await hit_api.json()
                temp_api = json_data["result"]["url"]
            
            async with session.post(temp_api, data={"file1": open(file, "rb")}) as response:
                response.raise_for_status()
                data_f = await response.json(content_type=None)
                download_link = data_f["result"]["url"]
            
            filename = file.rsplit("/", 1)[-1].replace("_", " ")
            text_edit = (
                f"File Uploaded to Streamtape!\n\n"
                f"**File Name:** `{filename}`\n"
                f"**Size:** `{humanbytes(file_size)}`\n"
                f"**Link:** `{download_link}`"
            )
            await editable.edit_text(
                text=text_edit,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open Link", url=download_link)]])
            )
    except aiohttp.ClientResponseError as e:
        print(f"Streamtape API error: {e}")
        await editable.edit_text(
            text=f"Sorry, Something went wrong!\n\nCan't Upload to Streamtape. Error: `{e.message}`\n"
                 f"You can report at [Support Group](https://t.me/Savior_128)",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except MessageNotModified:
        pass  # Silently ignore if the message content hasn't changed
    except Exception as e:
        print(f"Error in UploadToStreamtape: {e}")
        await editable.edit_text(
            text=f"Sorry, Something went wrong!\n\nCan't Upload to Streamtape. Error: `{e}`\n"
                 f"You can report at [Support Group](https://t.me/Savior_128)",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
# (c) @AbirHasan2005

import shutil
import os


async def delete_all(root: str) -> None:
    """
    Delete a folder and its contents.

    Args:
        root (str): Path to the folder to delete.
    """
    try:
        if os.path.exists(root):
            shutil.rmtree(root, ignore_errors=True)
        else:
            print(f"Directory {root} does not exist.")
    except Exception as e:
        print(f"Error deleting directory {root}: {e}")
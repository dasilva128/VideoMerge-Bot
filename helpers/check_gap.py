import time
from configs import Config

GAP = {}


async def check_time_gap(user_id: int) -> tuple[bool, int | None]:
    """
    Check if the user is within the time gap for sending videos.

    Args:
        user_id: Telegram User ID

    Returns:
        Tuple containing:
        - bool: True if the user is within the time gap, False otherwise
        - int or None: Remaining seconds until the gap is cleared, or None if no gap
    """
    user_id_str = str(user_id)
    current_time = time.time()

    if user_id_str in GAP:
        previous_time = GAP[user_id_str]
        time_diff = round(current_time - previous_time)
        if time_diff < Config.TIME_GAP:
            return True, round(Config.TIME_GAP - time_diff)
        else:
            del GAP[user_id_str]
    GAP[user_id_str] = current_time
    return False, None
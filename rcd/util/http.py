import logging
import traceback
from typing import Any, Optional

from aiohttp import ClientSession


async def fetch_from_url(session: ClientSession, url: str) -> Optional[Any]:
    """
    Asynchronously fetch data from a URL using a given session.

    Args:
        session: The aiohttp ClientSession to use for the request.
        url: The URL to fetch data from.

    Returns:
        The fetched data as a Python object (usually a dictionary), or None if an error occurs.
    """
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logging.error(f"Error fetching from {url}: {response.status}")
                return None
    except Exception as e:
        logging.error(f"Exception during fetching from {url}: {e}")
        logging.error(traceback.format_exc())

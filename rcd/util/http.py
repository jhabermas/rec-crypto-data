import logging
import traceback
from typing import Any, Dict, Optional

from aiohttp import ClientSession

log = logging.getLogger(__name__)


async def fetch_from_url(
    session: ClientSession, url: str, headers: Optional[Dict] = None
) -> Optional[Any]:
    """
    Asynchronously fetch data from a URL using a given session.

    Args:
        session: The aiohttp ClientSession to use for the request.
        url: The URL to fetch data from.
        headers: Optional dictionary of additional headers.

    Returns:
        The fetched data as a Python object (usually a dictionary), or None if an error occurs.
    """
    all_headers = {"Accepts": "application/json"}
    if headers:
        all_headers.update(headers)
        logging.debug(f"Using cusomt headers {all_headers}")
    try:
        async with session.get(url, headers=all_headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                data = await response.json()
                logging.error(f"Error fetching from {url}: {data}")
    except Exception as e:
        log.error(f"Exception during fetching from {url}: {e}")
        log.error(traceback.format_exc())
    return None

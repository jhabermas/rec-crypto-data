import decimal
import logging
from typing import Any, Dict, List

import aiofiles
import orjson as json

log = logging.getLogger(__name__)


def default(obj: Any) -> str:
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError


async def save_to_json(data: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
    filename = f"{params['name']}.json"
    log.debug(f"Saving data to {filename}")
    async with aiofiles.open(filename, "a") as f:
        await f.write(
            json.dumps(
                data,
                default=default,
                option=json.OPT_INDENT_2 | json.OPT_APPEND_NEWLINE,
            ).decode("utf-8")
        )
        await f.write("\n")

import decimal
import logging
from functools import partial
from pprint import pp
from typing import Any, Dict, List

import aiofiles
import orjson as json


def default(obj: Any) -> str:
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError


async def print_data(data: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
    logging.debug(f"Print data: {params['name']}")
    for item in data:
        pp(f"{params['name']} : {item}")


async def save_to_json(data: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
    filename = f"{params['name']}.json"
    logging.debug(f"Saving data to {filename}")
    async with aiofiles.open(filename, "a") as f:
        for item in data:
            await f.write(json.dumps(item, default=default).decode("utf-8"))


async def save_to_db(
    db_client, data: List[Dict[str, Any]], params: Dict[str, Any]
) -> None:
    logging.debug(f"Saving to DB: {params['name']}")
    db_client.save_to_db(data, params["name"])


class DataSink:
    """
    A data sink for storing data in various ways.
    """

    def __init__(self, config):
        logging.info(f"Data sink: {config.storage_method}")
        match config.storage_method:
            case "print":
                self.storage_method = print_data
            case "json":
                self.storage_method = save_to_json
            case "db":
                from .mongo import DatabaseClient

                self.db_client = DatabaseClient(config)
                self.storage_method = partial(save_to_db, self.db_client)
            case _:
                raise RuntimeError("Invalid storage method")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.cleanup()

    async def store_data(
        self, data: List[Dict[str, Any]], params: Dict[str, Any]
    ) -> None:
        logging.debug(f"Store data: {params['name']}")
        await self.storage_method(data, params)

    async def cleanup(self) -> None:
        logging.info("Cleaning up")
        if hasattr(self, "db_client"):
            await self.db_client.flush_data()

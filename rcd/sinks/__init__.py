import logging
from functools import partial
from pprint import pp
from typing import Any, Dict, List

from rcd.sinks.json import save_to_json

log = logging.getLogger(__name__)


async def print_data(data: List[Dict[str, Any]], params: Dict[str, Any]) -> None:
    log.debug(f"Print data: {params['name']}")
    for item in data:
        pp(f"{params['name']} : {item}")


async def save_to_db(
    db_client, data: List[Dict[str, Any]], params: Dict[str, Any]
) -> None:
    log.debug(f"Saving to DB: {params['name']}")
    await db_client.save_to_db(data, params["name"])


class DataSink:
    """
    A data sink for storing data in various ways.
    """

    def __init__(self, config):
        log.info(f"Data sink: {config.storage_method}")
        match config.storage_method:
            case "print":
                self.storage_method = print_data
            case "json":
                self.storage_method = save_to_json
            case "mongo":
                from .mongo import MongoDBClient

                self.db_client = MongoDBClient(config)
                self.storage_method = partial(save_to_db, self.db_client)
            case "oracle":
                from .oracle import OracleDBClient

                self.db_client = OracleDBClient(config)
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
        log.debug(f"Store data: {params['name']}")
        await self.storage_method(data, params)

    async def cleanup(self) -> None:
        log.info("Cleaning up")
        if hasattr(self, "db_client"):
            await self.db_client.flush_data()

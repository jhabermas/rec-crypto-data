import json
import logging
from asyncio import Lock
from typing import Any, Dict, List, Optional

from motor.core import AgnosticClient
from motor.motor_asyncio import AsyncIOMotorClient

log = logging.getLogger(__name__)


class MongoDBClient:
    def __init__(self, config: Any) -> None:
        """
        Initialize the DatabaseClient with configuration.

        Args:
            config: Configuration object with database settings.
        """
        self.lock = Lock()
        self.dry_run = config.dry_run
        self.batch_data: Dict[str, List[Any]] = {}
        self.batch_size = config.batch_size.to_dict()
        if not self.dry_run:
            self.client: AgnosticClient = AsyncIOMotorClient(config.mongo.conn_str)
            self.db = self.client[config.user]
        else:
            log.info("Database Client created in dry_run mode")

    async def save_to_db(
        self, data: List[Dict[str, Any]], collection_name: str
    ) -> Optional[List[Any]]:
        """
        Save data to the database in batches.

        Args:
            data: The data to be saved.
            collection_name: The name of the collection where data will be stored.

        Returns:
            List of inserted document IDs, if a batch insert occurs.
        """
        async with self.lock:
            if collection_name not in self.batch_data:
                self.batch_data[collection_name] = []
                if collection_name not in self.batch_size:
                    self.batch_size[collection_name] = self.batch_size["default"]

            self.batch_data[collection_name].extend(data)
            if (
                len(self.batch_data[collection_name])
                >= self.batch_size[collection_name]
            ):
                if self.dry_run:
                    await self._dry_insert_many(collection_name)
                else:
                    await self._insert_many(collection_name)
            return None

    async def flush_data(self) -> Optional[List[Any]]:
        log.info("Flushing data to database")
        all_ids = []
        for collection_name, data in self.batch_data.items():
            if data:
                if self.dry_run:
                    all_ids.extend(await self._dry_insert_many(collection_name))
                else:
                    all_ids.extend(await self._insert_many(collection_name))
        return all_ids

    async def _insert_many(self, collection_name):
        log.info(
            f"Inserting {len(self.batch_data[collection_name])} items into {collection_name}"
        )
        try:
            collection = self.db[collection_name]
            result = await collection.insert_many(self.batch_data[collection_name])
            self.batch_data[collection_name].clear()
            log.info(f"Inserted {len(result.inserted_ids)} records")
            return result.inserted_ids
        except Exception as e:
            log.error(f"Error saving data to database: {e}")

    async def _dry_insert_many(self, collection_name):
        num_items = len(self.batch_data[collection_name])
        log.info(f"Dry inserting {num_items} items into {collection_name}")
        ids = [i for i in range(0, num_items)]
        self.batch_data[collection_name].clear()
        return ids

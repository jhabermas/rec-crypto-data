import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticClient


class DatabaseClient:
    def __init__(self, config: Any) -> None:
        """
        Initialize the DatabaseClient with configuration.

        Args:
            config: Configuration object with database settings.
        """
        self.client: AgnosticClient = AsyncIOMotorClient(config.db.uri)
        self.db = self.client[config.db.name]
        self.batch_data: Dict[str, List[Any]] = {}
        self.batch_size = config.db.batch_size

    async def save_to_db(self, data: List[Dict[str, Any]], collection_name: str) -> Optional[List[Any]]:
        """
        Save data to the database in batches.

        Args:
            data: The data to be saved.
            collection_name: The name of the collection where data will be stored.

        Returns:
            List of inserted document IDs, if a batch insert occurs.
        """
        if collection_name not in self.batch_data:
            self.batch_data[collection_name] = []

        self.batch_data[collection_name].extend(data)

        if len(self.batch_data[collection_name]) >= self.batch_size:
            try:
                collection = self.db[collection_name]
                result = await collection.insert_many(self.batch_data[collection_name])
                self.batch_data[collection_name].clear()
                return result.inserted_ids
            except Exception as e:
                logging.error(f"Error saving data to database: {e}")
        return None

    async def flush_data(self):
        logging.info("Flushing data to database")
        for collection_name, data in self.batch_data.items():
            if data:
                try:
                    collection = self.db[collection_name]
                    await collection.insert_many(data)
                except Exception as e:
                    logging.error(f"Error flushing data to database: {e}")
                finally:
                    self.batch_data[collection_name].clear()

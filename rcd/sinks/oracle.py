import logging
from typing import Any, Dict, List

import oracledb

log = logging.getLogger(__name__)


class OracleDBClient:
    def __init__(self, config: Any) -> None:
        """
        Initialize the OracleDBClient with configuration.

        Args:
            config: Configuration object with database settings.
        """
        dsn = oracledb.makedsn(config.db.host, config.db.port, sid=config.db.sid)
        self.pool = oracledb.create_pool(
            user=config.db.username, password=config.db.password, dsn=dsn
        )
        self.batch_data: Dict[str, List[Any]] = {}
        self.batch_size = config.db.batch_size

    async def save_to_db(self, data: List[Dict[str, Any]], table_name: str) -> None:
        """
        Save data to the database in batches.

        Args:
            data: The data to be saved.
            table_name: The name of the table where data will be stored.
        """
        if table_name not in self.batch_data:
            self.batch_data[table_name] = []

        self.batch_data[table_name].extend(data)

        if len(self.batch_data[table_name]) >= self.batch_size:
            try:
                async with self.pool.acquire() as connection:
                    async with connection.cursor() as cursor:
                        query = f"insert into {table_name} values :json_data"
                        await cursor.setinputsizes(oracledb.DB_TYPE_JSON)
                        await cursor.executemany(query, self.batch_data[table_name])
                        self.batch_data[table_name].clear()
            except oracledb.Error as e:
                log.error(f"Error saving data to database: {e}")

    async def flush_data(self):
        log.info("Flushing data to database")
        for table_name, data in self.batch_data.items():
            if data:
                try:
                    async with self.pool.acquire() as connection:
                        async with connection.cursor() as cursor:
                            query = f"insert into {table_name} values :json_data"
                            await cursor.setinputsizes(oracledb.DB_TYPE_JSON)
                            await cursor.executemany(query, data)
                except oracledb.Error as e:
                    log.error(f"Error flushing data to database: {e}")
                    log.exception(e)
                finally:
                    self.batch_data[table_name].clear()

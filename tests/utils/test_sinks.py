from unittest.mock import AsyncMock, MagicMock

import pytest

from rcd.sinks.mongo import MongoDBClient


@pytest.fixture
def mock_db_config():
    return MagicMock(
        db=MagicMock(
            dry_run=False,
            mongo=MagicMock(conn_str="dummy_conn_str"),
            user="test_user",
            batch_size=MagicMock(to_dict=lambda: {"default": 5}),
        )
    )


@pytest.fixture
def mongodb_client(mock_db_config):
    return MongoDBClient(mock_db_config)


@pytest.mark.asyncio
async def test_save_to_db_normal_operation(mongodb_client):
    mongodb_client._insert_many = AsyncMock(return_value=["id1", "id2"])

    data = [{"name": "item1"}, {"name": "item2"}]
    await mongodb_client.save_to_db(data, "test_collection")

    mongodb_client._insert_many.assert_not_called()
    assert len(mongodb_client.batch_data["test_collection"]) == 2


@pytest.mark.asyncio
async def test_flush_data_dry_run(mock_db_config):
    mock_db_config.db.dry_run = True
    mongodb_client = MongoDBClient(mock_db_config)

    mongodb_client.batch_data["test_collection"] = [
        {"name": "item1"},
        {"name": "item2"},
    ]
    result = await mongodb_client.flush_data()

    assert len(result) == 2
    assert len(mongodb_client.batch_data["test_collection"]) == 0

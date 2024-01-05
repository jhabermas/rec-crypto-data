from datetime import datetime
from unittest.mock import MagicMock

import pytest

from rcd.util.mapping import map_data


def test_map_data_basic():
    # Setup
    data = {"original_key1": "value1", "original_key2": "value2"}
    mapping_format = MagicMock(
        mapping={"mapped_key1": "original_key1", "mapped_key2": "original_key2"}
    )
    exchange = "test_exchange"
    channel = "test_channel"

    # Execute
    result = map_data(data, mapping_format, exchange, channel)

    # Assert
    assert result == {
        "exchange": "test_exchange",
        "channel": "test_channel",
        "mapped_key1": "value1",
        "mapped_key2": "value2",
        "ts": pytest.approx(datetime.utcnow().timestamp() * 1000, abs=20),
    }


def test_map_data_missing_ts():
    data = {"original_key": "value"}
    mapping_format = MagicMock(mapping={"new_key": "original_key"})
    exchange = "test_exchange"
    channel = "test_channel"

    result = map_data(data, mapping_format, exchange, channel)

    assert "ts" in result and type(result["ts"]) is float
    assert result["ts"] == pytest.approx(datetime.utcnow().timestamp() * 1000, abs=20)


def test_map_data_with_existing_ts():
    data = {"original_ts": 1234567890}
    mapping_format = MagicMock(mapping={"ts": "original_ts"})
    exchange = "test_exchange"
    channel = "test_channel"

    result = map_data(data, mapping_format, exchange, channel)

    assert result["ts"] == 1234567890

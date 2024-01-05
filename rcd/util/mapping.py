import logging
from datetime import datetime
from functools import partial
from typing import Any, Dict, List

from rcd.config import mappings


def map_data(
    data: Dict[str, Any], format: Any, exchange: str, channel: str
) -> Dict[str, Any]:
    """
    Map data from an exchange channel to a standard format.

    Args:
        data: The original data to be mapped.
        format: The mapping format read from a toml file using Dynaconf.
        exchange: The name of the exchange.
        channel: The channel from which data is sourced.

    Returns:
        A dictionary of mapped data.
    """
    out = {"exchange": exchange, "channel": channel}
    for k, v in format.mapping.items():
        out[k] = data[v]
    if "ts" not in out or out["ts"] is None:
        out["ts"] = datetime.utcnow().timestamp() * 1000
    if "map_symbols" in format:
        out["symbol"] = format.map_symbols[out["symbol"]]
    return out


def map_lib_data(
    lib: str, exchange: str, channel: str, data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Map data from a specific library (e.g., ccxt, cryptofeed) using predefined mappings.

    Args:
        lib: The name of the library.
        exchange: The name of the exchange.
        channel: The channel from which data is sourced.
        data: The original data to be mapped.

    Returns:
        A list containing dictionaries of mapped data.
    """
    try:
        format = mappings[lib][channel]
        return [map_data(data, format, exchange, channel)]
    except Exception as e:
        logging.error(f"Error mapping data for {lib} {exchange} {channel}: {e} {data}")
    return []


map_ccxt_data = partial(map_lib_data, "ccxt")
map_cryptofeed_data = partial(map_lib_data, "cryptofeed")


def map_api_data(
    exchange: str, channel: str, symbol: str, message: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Map data from an API message to a standard format.

    Args:
        exchange: The name of the exchange.
        channel: The channel from which data is sourced.
        message: The original API message to be mapped.

    Returns:
        A list containing dictionaries of mapped data.
    """
    results = []
    try:
        format = mappings[exchange][channel]
        data = message[format.data_root] if format.data_root else message
        data = data[format.subnode] if "subnode" in format else data
        if format.is_array:
            items = data[format.array_root] if format.array_root else data
            for item in items:
                mapped_data = map_data(item, format, exchange, channel)
                mapped_data["symbol"] = symbol
                results.append(mapped_data)
        else:
            mapped_data = map_data(data, format, exchange, channel)
            mapped_data["symbol"] = symbol
            results.append(mapped_data)
    except Exception as e:
        logging.error(f"Error mapping data for {exchange} {channel}: {e} {data}")
    return results

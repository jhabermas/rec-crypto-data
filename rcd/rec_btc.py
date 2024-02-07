import asyncio
import logging
import sys
import time
import traceback
from contextlib import suppress
from datetime import datetime
from functools import partial
from signal import SIGINT, SIGTERM
from typing import Any, Dict, List, Optional

import aiohttp
import uvloop
from ccxt.async_support import Exchange

from rcd.config import log_config, settings
from rcd.sinks import DataSink, save_to_json
from rcd.util.ccxt import (
    fetch_funding_rate,
    fetch_order_book,
    instantiate_exchanges,
    terminate_connections,
)
from rcd.util.feed import run_feed
from rcd.util.http import fetch_from_url
from rcd.util.mapping import map_api_data, map_ccxt_data, map_cryptofeed_data

log = logging.getLogger(__name__)


async def save_data(
    sink: DataSink, exchange: str, channel: str, symbol: str, data: Optional[Any]
) -> None:
    """
    Save data from a given exchange and channel using the provided data sink.

    Args:
        sink: The data sink object used for storing data.
        exchange: The name of the exchange where the data is coming from.
        channel: The channel or type of data being processed (e.g., funding, oi, ticker).
        data: The data to be saved. Can be None, in which case a warning is logged.
    """
    if data is not None:
        log.debug(f"Saving data from {exchange}")
        if settings.rec_raw_data:
            await save_to_json(data, {"name": f"{exchange}_{channel}_api"})
        await sink.store_data(
            map_api_data(exchange, channel, symbol, data),
            {"name": channel},
        )
    else:
        log.warning(f"No {channel} data to save from {exchange}")


async def save_ccxt_data(
    sink: DataSink, exchange: str, channel: str, data: Any
) -> None:
    """
    Save data obtained with CCXT from a given exchange and channel using the provided data sink.

    Args:
        sink: The data sink object used for storing data.
        exchange: The name of the exchange where the data is coming from.
        channel: The channel or type of data being processed.
        data: The data fetched via the CCXT library to be saved.
    """
    log.debug(f"Saving {channel} from {exchange}")
    if settings.rec_raw_data:
        await save_to_json(data, {"name": f"{exchange}_{channel}_ccxt"})
    await sink.store_data(map_ccxt_data(exchange, channel, data), {"name": channel})


async def oi_feed_handler(sink: DataSink, data: Any, receipt: Any) -> None:
    """
    Handle and store OI data from cryptofeed using the provided data sink.

    Args:
        sink: The data sink object used for storing data.
        data: The OI data to be handled and stored.
        receipt: Data receipt timestamp.
    """
    try:
        data_dict = data.to_dict()
        data_dict["receipt"] = receipt * 1000
        data_dict["timestamp"] = data_dict["timestamp"] * 1000
        data_dict["open_interest"] = str(data_dict["open_interest"])
        if settings.rec_raw_data:
            exchange = data.exchange
            await save_to_json(data_dict, {"name": f"{exchange}_oi_cryptofeed"})
        await sink.store_data(
            map_cryptofeed_data(data.exchange, "oi", data_dict), {"name": "oi"}
        )
    except Exception as e:
        log.error(f"OI handler error: {e}")


async def fetch_and_save_http(
    session: aiohttp.ClientSession,
    exchange: str,
    url: str,
    channel: str,
    symbol: str,
    interval: int,
    sink: DataSink,
) -> None:
    """
    Continuously fetch data from a specified API endpoint at regular intervals and save it using the provided data sink.

    Args:
        session: The aiohttp ClientSession used for HTTP requests.
        exchange: The name of the exchange associated with the data.
        url: The URL to fetch data from.
        channel: The channel or type of data being processed.
        interval: The interval between fetches in milliseconds.
        sink: The data sink object used for storing data.
    """
    while True:
        start = time.perf_counter()
        data = await fetch_from_url(session, url)
        await save_data(sink, exchange, channel, symbol, data)
        elapsed = time.perf_counter() - start
        await asyncio.sleep((interval / 1000) - elapsed)


async def fetch_http_data(config: Any, sink: DataSink) -> None:
    """
    Initialize an HTTP session and create asynchronous tasks for fetching data from configured HTTP endpoints.

    Args:
        config: The Dynaconf configuration object containing HTTP endpoint configurations.
        sink: The data sink object used for storing data.
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        for endpoint in config.http.endpoints:
            task = asyncio.create_task(
                fetch_and_save_http(
                    session,
                    endpoint.exchange,
                    endpoint.url,
                    endpoint.channel,
                    endpoint.symbol,
                    endpoint.interval,
                    sink,
                )
            )
            tasks.append(task)
        await asyncio.gather(*tasks)


async def fetch_and_save_order_book(
    exchange: Exchange, symbol: str, sink: DataSink
) -> None:
    """
    Fetch and save order book data for a specific exchange and symbol.

    Args:
        exchange: CCXT exchange object to fetch data from.
        symbol: The trading symbol to fetch order book data for.
        sink: The data sink object used for storing data.
    """
    data = await fetch_order_book(exchange, symbol)
    await save_ccxt_data(sink, exchange.id, "ob", data)


async def fetch_and_save_funding(
    exchange: Exchange, symbol: str, sink: DataSink
) -> None:
    """
    Fetch and save funding rate data for a specific exchange and symbol.

    Args:
        exchange: CCXT exchange object to fetch data from.
        symbol: The trading symbol to fetch funding rate data for.
        sink: The data sink object used for storing data.
    """
    data = await fetch_funding_rate(exchange, symbol)
    # Fix for bug in ccxt
    if exchange == "okx":
        data["timestamp"] = int(data["info"]["ts"])
    elif exchange == "bitmex":
        data["fundingTimestamp"] = (
            datetime.strptime(
                data["fundingDatetime"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).timestamp()
            * 1000
        )
    await save_ccxt_data(sink, exchange.id, "funding", data)


async def fetch_exchange_data(
    config: Any, data_sources: List[Dict[str, Any]], sink: DataSink
) -> None:
    """
    Continuously fetch data for configured channels at regular intervals using CCXT.

    Args:
        data_sources: A list of data source configurations, each containing an exchange object
                      and lists of symbols for order book and funding data.
        sink: The data sink object used for storing data.

    Description:
        This function waits until fetch_offset seconds before the next minute, then starts fetching data.
        It fetches order book and funding data for each symbol in the data sources list,
        and repeats this process every fetch_interval.
    """
    now = datetime.now()
    seconds_till_next_minute = 60 - now.second
    # Adjust to align with near candle close
    offset = config.ccxt.fetch_offset
    await asyncio.sleep(seconds_till_next_minute - offset)
    while True:
        log.info("Fetching data...")
        start = time.perf_counter()
        tasks = []
        for source in data_sources:
            exchange = source["exchange"]
            try:
                if config.rec_ob:
                    for symbol in source["ob_symbols"]:
                        task = asyncio.create_task(
                            fetch_and_save_order_book(exchange, symbol, sink)
                        )
                        tasks.append(task)
                if config.rec_funding:
                    for symbol in source["funding_symbols"]:
                        task = asyncio.create_task(
                            fetch_and_save_funding(exchange, symbol, sink)
                        )
                        tasks.append(task)

            except Exception as e:
                tb_str = traceback.format_exc()
                log.error(f"Error fetching data from {exchange.id}: {e}")
                log.debug(tb_str)

        await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        log.info(f"Data fetched in {elapsed:0.5f} seconds.")
        await asyncio.sleep(max(config.ccxt.fetch_interval - elapsed, 0))


async def main():
    log.info("Initialising...")
    log.info(f"Orderbook: {settings.rec_ob}")
    log.info(f"Funding: {settings.rec_funding}")
    log.info(f"Open Interest: {settings.rec_oi}")
    log.info(f"Tickers: {settings.rec_tickers}")
    log.info(f"Raw Data: {settings.rec_raw_data}")
    exchanges = []
    try:
        exchanges = instantiate_exchanges(settings)
        tasks = []
        async with DataSink(settings) as sink:
            tasks.append(
                asyncio.create_task(fetch_exchange_data(settings, exchanges, sink))
            )
            if settings.rec_oi:
                tasks.append(
                    asyncio.create_task(
                        run_feed(settings, partial(oi_feed_handler, sink))
                    )
                )
            if settings.rec_tickers:
                tasks.append(asyncio.create_task(fetch_http_data(settings, sink)))
            await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        log.warning("Keyboard interrupt received. Shutting down...")
    except asyncio.CancelledError:
        log.warning("Tasks cancelled.")
    except Exception as e:
        log.exception(e)
    finally:
        log.info("Terminating exchange connections...")
        await terminate_connections(exchanges)
        log.info("Recording completed.")


if __name__ == "__main__":
    log_config.setup_logging()
    uvloop.run(main())

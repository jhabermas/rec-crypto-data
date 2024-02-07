import asyncio
import logging
import time
from signal import SIGINT, SIGTERM
from typing import Any, Dict, List, Optional

import aiohttp
import uvloop

from rcd.config import get_module_config, log_config, settings
from rcd.sinks import DataSink, save_to_json
from rcd.util.http import fetch_from_url
from rcd.util.mapping import map_market_data

log = logging.getLogger(__name__)
config = get_module_config("markets")


async def save_data(
    sink: DataSink, source: str, channel: str, category: str, data: Optional[Any]
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
        log.debug(f"Saving {channel} [{category}] data from {source}")
        if settings.rec_raw_data:
            await save_to_json(data, {"name": f"{source}_{channel}_api"})
        await sink.store_data(
            map_market_data(source, channel, category, data),
            {"name": channel},
        )
    else:
        log.warning(f"No {channel} data to save from {source}")


async def fetch_and_save_http(
    session: aiohttp.ClientSession,
    exchange: str,
    url: str,
    channel: str,
    category: str,
    headers: Dict,
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
        try:
            start = time.perf_counter()
            data = await fetch_from_url(session, url, headers)
            await save_data(sink, exchange, channel, category, data)
            elapsed = time.perf_counter() - start
            await asyncio.sleep(interval - elapsed)
        except Exception as e:
            log.error(
                f"Error when fetching market data from {exchange} {channel} {category}"
            )
            log.exception(e)


async def fetch_http_data(endpoints: Any, sink: DataSink) -> None:
    """
    Initialize an HTTP session and create asynchronous tasks for fetching data from configured HTTP endpoints.

    Args:
        config: The Dynaconf configuration object containing HTTP endpoint configurations.
        sink: The data sink object used for storing data.
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        logging.info("Connecting to endpoints...")
        for endpoint in endpoints.endpoints:
            interval = (
                endpoint.interval if "interval" in endpoint else endpoints.interval
            )
            headers = endpoint.headers if "headers" in endpoint else None
            category = endpoint.category if "category" in endpoint else None
            logging.info(
                f"Endpoint: {endpoint.api}, channel: {endpoint.channel} : {endpoint.category}, interval: {interval}"
            )
            task = asyncio.create_task(
                fetch_and_save_http(
                    session,
                    endpoint.api,
                    endpoint.url,
                    endpoint.channel,
                    category,
                    headers,
                    interval,
                    sink,
                )
            )
            tasks.append(task)
            await asyncio.sleep(1)
        await asyncio.gather(*tasks)


async def main():
    log.info("Initialising...")
    try:
        tasks = []
        async with DataSink(settings) as sink:
            tasks.append(asyncio.create_task(fetch_http_data(config.markets, sink)))
            tasks.append(asyncio.create_task(fetch_http_data(config.marketcap, sink)))
            tasks.append(asyncio.create_task(fetch_http_data(config.defi, sink)))
            await asyncio.gather(*tasks, return_exceptions=True)
    except KeyboardInterrupt:
        log.warning("Keyboard interrupt received. Shutting down...")
    except asyncio.CancelledError:
        log.warning("Tasks cancelled.")
    except Exception as e:
        log.exception(e)
    finally:
        log.info("Recording completed.")


if __name__ == "__main__":
    log_config.setup_logging()
    uvloop.run(main())

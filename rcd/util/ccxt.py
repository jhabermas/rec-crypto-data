import logging
from datetime import datetime
from typing import Any, Dict, List

import ccxt.async_support as ccxt

log = logging.getLogger(__name__)


async def fetch_order_book(exchange: ccxt.Exchange, symbol: str) -> Dict[str, Any]:
    """
    Fetch the order book for a given symbol from an exchange.

    Args:
        exchange: The CCXT exchange instance.
        symbol: The symbol to fetch the order book for.

    Returns:
        A dictionary representing the order book.
    """
    log.debug(f"Fetching order book for {symbol} from {exchange.id}")
    try:
        order_book = await exchange.fetch_l2_order_book(symbol)
        return order_book
    except Exception as e:
        log.error(f"Error fetching order book for {symbol}: {e}")


async def fetch_funding_rate(exchange: ccxt.Exchange, symbol: str) -> Dict[str, Any]:
    """
    Fetch the funding rate for a given symbol from an exchange.

    Args:
        exchange: The CCXT exchange instance.
        symbol: The symbol to fetch the funding rate for.

    Returns:
        A dictionary representing the funding rate.
    """
    log.debug(f"Fetching funding rate for {symbol} from {exchange.id}")
    try:
        funding_rate = await exchange.fetch_funding_rate(symbol)
        return funding_rate
    except Exception as e:
        log.error(f"Error fetching funding rate for {symbol}: {e}")


def instantiate_exchanges(config: Any) -> List[Dict[str, Any]]:
    """
    Initialize connections to various exchanges as defined in the configuration.

    Args:
        config: Configuration object with exchange settings.

    Returns:
        A list of dictionaries, each containing an exchange instance and symbol information.
    """
    exchanges = []
    log.info("Initializing exchange connections...")
    for e in config.ccxt.exchanges:
        log.info(f"Connecting to {e.id}")
        exchange_class = getattr(ccxt, e.id)
        exchanges.append(
            {
                "exchange": exchange_class({"enableRateLimit": True, "verbose": False}),
                "ob_symbols": e.ob_symbols,
                "funding_symbols": e.funding_symbols,
            }
        )
        if e.id == "coinbase":
            if "coinbase" in config and "api_key" in config.coinbase:
                log.info("Using authenticated coinbase connection")
                exchanges[-1]["exchange"].apiKey = config.coinbase.api_key
                exchanges[-1]["exchange"].secret = config.coinbase.api_secret
            else:
                log.warning(
                    "No API key provided for coinbase. Create .secrets.toml with coinbase.api_key & coinbase.api_secret keys."
                )
    return exchanges


async def terminate_connections(exchanges: List[Dict[str, Any]]) -> None:
    """
    Close connections to all exchanges.

    Args:
        exchanges: A list of dictionaries, each containing an exchange instance.
    """
    for e in exchanges:
        log.debug(f"Closing {e['exchange'].id} connection")
        await e["exchange"].close()

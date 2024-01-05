import logging
from typing import Any, Callable

from cryptofeed import FeedHandler
from cryptofeed.defines import OPEN_INTEREST


def add_oi_feed(
    fh: FeedHandler,
    exchange_id: str,
    symbols: list[str],
    handler: Callable[[Any], None],
) -> None:
    """
    Add an Open Interest (OI) feed to the FeedHandler for a specific exchange.

    Args:
        fh: The FeedHandler instance.
        exchange_id: The ID of the exchange.
        symbols: List of symbols to subscribe to.
        handler: The callback function for the feed.
    """
    try:
        logging.info(f"Adding OI feed from {exchange_id}")
        match exchange_id:
            case "BinanceFutures":
                from cryptofeed.exchanges import BinanceFutures

                fh.add_feed(
                    BinanceFutures(
                        symbols=symbols,
                        channels=[OPEN_INTEREST],
                        callbacks={OPEN_INTEREST: handler},
                    )
                )
            case "Bitmex":
                from cryptofeed.exchanges import Bitmex

                fh.add_feed(
                    Bitmex(
                        symbols=symbols,
                        channels=[OPEN_INTEREST],
                        callbacks={OPEN_INTEREST: handler},
                    )
                )
            case "OKX":
                from cryptofeed.exchanges import OKX

                fh.add_feed(
                    OKX(
                        symbols=symbols,
                        channels=[OPEN_INTEREST],
                        callbacks={OPEN_INTEREST: handler},
                    )
                )
            case _:
                raise RuntimeError(f"Unsupported exchange")
    except Exception as e:
        logging.error(f"Error adding {exchange_id} feed: {e}")


async def run_feed(config: Any, handler: Callable[[Any], None]) -> None:
    """
    Run the feed handler with configured exchanges and open interest symbols.

    Args:
        config: Configuration object with exchange and symbol information.
        handler: The callback function for the feed.
    """
    fh = FeedHandler()
    for ex in config.cryptofeed.exchanges:
        add_oi_feed(fh, ex, config.cryptofeed[ex].oi_symbols, handler)

    fh.run(start_loop=False)

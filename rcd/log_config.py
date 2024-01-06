import logging
import sys


def setup_logging(level: str = "INFO", logfile=None) -> None:
    log_level = getattr(logging, level.upper(), logging.DEBUG)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    stdout_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")
    )

    # Handler for logging WARNING, ERROR, and CRITICAL messages to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")
    )

    handlers = [stdout_handler, stderr_handler]
    if logfile:
        file_handler = logging.FileHandler(logfile)
        handlers.append(file_handler)

    # Basic configuration
    logging.basicConfig(level=log_level, handlers=handlers)

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging(level: str = "INFO", logfile=None) -> None:
    log_level = getattr(logging, level.upper(), logging.DEBUG)
    json_formatter = JsonFormatter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    stdout_handler.setFormatter(json_formatter)

    # Handler for logging WARNING, ERROR, and CRITICAL messages to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(json_formatter)

    handlers = [stdout_handler, stderr_handler]
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(json_formatter)
        handlers.append(file_handler)

    # Basic configuration
    logging.basicConfig(level=log_level, handlers=handlers)

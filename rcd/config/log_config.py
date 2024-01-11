import inspect
import json
import logging
import os.path
import subprocess
import sys
from logging.handlers import RotatingFileHandler

from dynaconf import Dynaconf

from rcd import __version__

config = Dynaconf(
    envvar_prefix="RCD_LOGGING",
    settings_files=["logging.toml"],
    load_dotenv=True
)


def get_git_revision_short_hash():
    try:
        short_hash = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        short_hash = str(short_hash, "utf-8").strip()
        return short_hash
    except Exception:
        return config.get("GIT_HASH", "unknown")


class JsonFormatter(logging.Formatter):
    def __init__(self, app_name):
        super().__init__()
        self.app_name = app_name
        self.git_commit = get_git_revision_short_hash()

    def format(self, record):
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "app": self.app_name,
            "version": __version__,
            "git": self.git_commit,
            "name": record.name,
            "module": record.module,
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging() -> None:
    log_level = getattr(logging, config.logging.level.upper(), logging.DEBUG)

    formatter = None  # logging.Formatter(logging.BASIC_FORMAT)
    if "formatter" in config.logging:
        if config.logging.formatter == "text":
            formatter = logging.Formatter(
                fmt="[%(asctime)s] %(name)s :: %(levelname)-8s :: %(message)s"
            )
        elif config.logging.formatter == "json":
            caller_frame = inspect.stack()[1]
            caller_filename = os.path.splitext(os.path.basename(caller_frame.filename))[
                0
            ]
            formatter = JsonFormatter(caller_filename)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(log_level)
    stdout_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    stdout_handler.setFormatter(formatter)

    # Handler for logging WARNING, ERROR, and CRITICAL messages to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    handlers = [stdout_handler, stderr_handler]
    if "logfile" in config.logging:
        file_handler = logging.FileHandler(config.logfile)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    # Basic configuration
    logging.basicConfig(level=log_level, handlers=handlers)

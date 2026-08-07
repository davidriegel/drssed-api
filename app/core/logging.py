__all__ = ["get_logger"]

import json
import logging
import time
from datetime import datetime
from os import getenv

_RESERVED_RECORD_KEYS = set(logging.makeLogRecord({}).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS:
                log_data[key] = value

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class ConsoleFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",
    }

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime("%H:%M:%S", ct)
        return s

    def format(self, record):
        timestamp = self.formatTime(record)
        level_color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        level = f"{level_color}{record.levelname:<8}{self.COLORS['RESET']}"

        message = record.getMessage()

        extras = [
            f"{key}={value}"
            for key, value in record.__dict__.items()
            if key not in _RESERVED_RECORD_KEYS and value is not None
        ]

        extra_str = f" | {' | '.join(extras)}" if extras else ""

        line = f"{timestamp} | {level} | {message}{extra_str}"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            line += "\n" + record.exc_text
        if record.stack_info:
            line += "\n" + self.formatStack(record.stack_info)

        return line


class Logger:
    _logger: logging.Logger | None = None
    _initialized: bool = False

    @classmethod
    def setup_logging(cls, app=None):
        if cls._initialized:
            return

        cls._logger = logging.getLogger("drssed")

        log_level = getenv("LOG_LEVEL", "DEBUG").upper()
        level = getattr(logging, log_level, logging.DEBUG)
        cls._logger.setLevel(level)

        env = getenv("FLASK_ENV", "development")
        is_production = env == "production"

        cls._logger.handlers.clear()

        console_handler = logging.StreamHandler()

        if is_production:
            console_handler.setFormatter(JsonFormatter())
            console_handler.setLevel(log_level)
        else:
            console_handler.setFormatter(ConsoleFormatter())
            console_handler.setLevel(level)

        cls._logger.addHandler(console_handler)

        logging.getLogger("werkzeug").setLevel(logging.WARNING)

        cls._initialized = True
        cls._logger.info(
            f"Logging initialized - Environment: {env}, Level: {log_level}"
        )

    @classmethod
    def get_logger(cls, name=None) -> logging.Logger:
        if not cls._initialized:
            cls.setup_logging()

        if name:
            return logging.getLogger(f"drssed.{name}")

        assert cls._logger is not None
        return cls._logger


def get_logger(name=None) -> logging.Logger:
    # Convinience function
    return Logger.get_logger(name)


def setup_logging(app=None):
    Logger.setup_logging(app)

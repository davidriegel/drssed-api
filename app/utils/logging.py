__all__ = ["get_logger"]

import logging
import time
import os
from logging.handlers import RotatingFileHandler
from os import getenv

# ! stream_handler is used to print logs to console
# ! remove stream_handler to disable console logs (only file logs; useful for production)

class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime("%Y-%m-%d %H:%M:%S %z", ct)
        return s

    def format(self, record):
        record.asctime = self.formatTime(record, self.datefmt)
        return f"[{record.asctime}] [{record.process}] [{record.levelname}] {record.getMessage()}"

class Logger:
    _logger: logging.Logger = None

    @classmethod
    def get_logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = logging.getLogger()
            log_level = getenv("LOG_LEVEL", "DEBUG").upper()
            level = getattr(logging, log_level, logging.DEBUG)
            cls._logger.setLevel(level)

            if not cls._logger.hasHandlers():
                stream_handler = logging.StreamHandler()
                
                formatter = CustomFormatter()
                stream_handler.setFormatter(formatter)
                
                stream_handler.setLevel(level)

                cls._logger.addHandler(stream_handler)

        return cls._logger

def get_logger() -> logging.Logger:
    return Logger.get_logger()
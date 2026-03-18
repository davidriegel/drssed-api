__all__ = ["get_logger"]

import json
import logging
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from os import getenv

class JsonFormatter(logging.Formatter):
    def format(self, record) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "process": record.process,
            "message": record.getMessage()
        }
        
        user_id = getattr(record, 'user_id', None)
        if user_id is not None:
            log_data['user_id'] = user_id
            
        endpoint = getattr(record, 'endpoint', None)
        if endpoint:
            log_data['endpoint'] = endpoint
            
        method = getattr(record, 'method', None)
        if method:
            log_data['method'] = method
            
        status_code = getattr(record, 'status_code', None)
        if status_code:
            log_data['status_code'] = status_code
            
        duration_ms = getattr(record, 'duration_ms', None)
        if duration_ms is not None:
            log_data['duration_ms'] = duration_ms
            
        ip = getattr(record, 'ip', None)
        if ip:
            log_data['ip'] = ip
            
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

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
    _logger: logging.Logger | None = None

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
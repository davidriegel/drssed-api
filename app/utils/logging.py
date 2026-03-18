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
    
class ConsoleFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m', # Cyan
        'INFO': '\033[32m', # Green
        'WARNING': '\033[33m', # Yellow
        'ERROR': '\033[31m', # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'
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
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        level = f"{level_color}{record.levelname:<8}{self.COLORS['RESET']}"
        
        message = record.getMessage()
        
        extras = []
        user_id = getattr(record, 'user_id', None)
        if user_id is not None:
            extras.append(f"user={user_id}")
            
        endpoint = getattr(record, 'endpoint', None)
        if endpoint:
            extras.append(f"endpoint={endpoint}")
            
        method = getattr(record, 'method', None)
        if method:
            extras.append(f"method={method}")
            
        status_code = getattr(record, 'status_code', None)
        if status_code:
            extras.append(f"status={status_code}")
            
        duration_ms = getattr(record, 'duration_ms', None)
        if duration_ms:
            extras.append(f"duration={duration_ms}")
            
        extra_str = f" | {' | '.join(extras)}" if extras else ""
        
        return f"{timestamp} | {level} | {message}{extra_str}"

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
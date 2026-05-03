__all__ = ["get_logger"]

import json
import os
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
        
        if is_production:
            log_dir = "logs"
            os.makedirs(log_dir, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                f"{log_dir}/drssed-api.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(JsonFormatter())
            file_handler.setLevel(log_level)
            cls._logger.addHandler(file_handler)
            
            error_handler = RotatingFileHandler(
                f"{log_dir}/drssed-errors.log",
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5
            )
            error_handler.setFormatter(JsonFormatter())
            error_handler.setLevel(logging.ERROR)
            cls._logger.addHandler(error_handler)
        
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        
        cls._initialized = True
        cls._logger.info(f"Logging initialized - Environment: {env}, Level: {log_level}")

    @classmethod
    def get_logger(cls, name=None) -> logging.Logger:
        if not cls._initialized:
            cls.setup_logging()
        
        if name:
            return logging.getLogger(f"drssed.{name}")
        return cls._logger


def get_logger(name=None) -> logging.Logger:
    # Convinience function
    return Logger.get_logger(name)


def setup_logging(app=None):
    Logger.setup_logging(app)
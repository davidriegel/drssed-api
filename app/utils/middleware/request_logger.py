import time
import logging
from flask import request, g
from functools import wraps

logger = logging.getLogger("drssed.requests")

def init_request_logging(app):
    
    @app.before_request
    def log_request_start():
        g.start_time = time.time()
        
    @app.after_request
    def log_request_end(response):
        if not hasattr(g, "start_time"):
            return response
        
        duration_ms = round((time.time() - g.start_time) * 1000, 2)
        
        user_id = getattr(g, "user_id", None)
        
        extra = {
            "endpoint": request.endpoint,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "ip": request.remote_addr
        }
        
        message = f"{request.method} {request.path} → {response.status_code} ({duration_ms}ms)"
        
        # Use different log level for status code severity
        if response.status_code >= 500:
            logger.error(message, extra=extra)
        elif response.status_code >= 400:
            logger.warning(message, extra=extra)
        else:
            logger.info(message, extra=extra)
            
        return response
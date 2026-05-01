from time import time, sleep, perf_counter
from flask import jsonify, make_response
from flask_limiter import Limiter, RequestLimit
from flask_limiter.util import get_remote_address
from app.utils.logging import get_logger
from redis import Redis, RedisError
from os import getenv

logger = get_logger()

REDIS_URI = getenv("REDIS_URI", "redis://localhost:6379")
HEALTH_CHECK_TIMEOUT = 2.0

def rateLimitResponse(rateLimit: RequestLimit):
    reset_in_seconds = rateLimit.reset_at - time()
    
    return make_response(jsonify({"error": f"Rate limit exceeded and will reset in {reset_in_seconds:.0f} seconds."}), 429)

def checkRedisConnection(limiter: Limiter):
    if not limiter.enabled:
        return
    
    retries = 0
    max_retries = 10
    retry_delay = 10

    while retries < max_retries:
        try:
            redis_client = Redis.from_url(REDIS_URI)
            redis_client.ping()
            redis_client.close()
            logger.debug("Successfully connected to Redis.")
            return
        except RedisError as e:
            retries += 1
            logger.error(f"Failed to connect to Redis (attempt {retries}/{max_retries}): {e}")
            if retries < max_retries:
                sleep(retry_delay)
            else:
                logger.critical("Max retries reached. Unable to connect to Redis.")
                raise e
            
def health() -> dict:
    start = perf_counter()
    
    if not limiter.enabled:
        return {"status": "disabled"}
    
    client = None
    try:
        client = Redis.from_url(
            REDIS_URI,
            socket_connect_timeout=HEALTH_CHECK_TIMEOUT,
            socket_timeout=HEALTH_CHECK_TIMEOUT,
        )
        if not client.ping():
            raise RuntimeError("PING returned falsy")
        return {
            "status": "ok",
            "latency_ms": round((perf_counter() - start) * 1000, 2),
        }
    except (RedisError, Exception) as exc:
        logger.warning(f"Redis health check failed: {exc}")
        return {
            "status": "error",
            "latency_ms": round((perf_counter() - start) * 1000, 2),
        }
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

try:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=REDIS_URI,
        on_breach=rateLimitResponse,
        enabled=True if getenv("RATELIMITER_ENABLED", "True").lower() == "true" else False,
    )
    
    logger.debug(f"Rate limiter enabled: {limiter.enabled}")
    
    checkRedisConnection(limiter)
except RedisError as e:
    logger.critical("Failed to connect to Redis")
    raise e
except Exception as e:
    logger.critical("Failed to initialize rate limiter")
    logger.critical(e)
    raise e
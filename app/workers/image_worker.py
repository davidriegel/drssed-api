import os

from redis import Redis
from rq import Queue, SimpleWorker

from app.core.logging import get_logger

logger = get_logger()

QUEUE_NAME = "images"
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")


def main() -> None:
    redis_conn = Redis.from_url(REDIS_URI)
    queue = Queue(QUEUE_NAME, connection=redis_conn)
    worker = SimpleWorker([queue], connection=redis_conn)

    logger.info(f"Image worker starting, listening on queue '{QUEUE_NAME}'")
    worker.work()


if __name__ == "__main__":
    main()

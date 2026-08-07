import os

from redis import Redis
from rq import Queue, SimpleWorker

from app.core.email import EMAIL_QUEUE_NAME
from app.core.logging import get_logger

logger = get_logger()

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")


def main() -> None:
    redis_conn = Redis.from_url(REDIS_URI)
    queue = Queue(EMAIL_QUEUE_NAME, connection=redis_conn)
    worker = SimpleWorker([queue], connection=redis_conn)

    logger.info(f"Email worker starting, listening on queue '{EMAIL_QUEUE_NAME}'")
    # Retries are put on the scheduled registry, so without this they never run.
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()

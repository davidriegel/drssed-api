import os

from redis import Redis
from rq import Queue, SimpleWorker

from app.core.logging import get_logger

logger = get_logger()

QUEUE_NAME = "images"
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")


def _load_model() -> None:
    """Builds the model before any job can arrive.

    RQ resolves the job by dotted path, so without this the module is imported by
    the first job to come in - and building the model takes over a minute, which
    the client waiting on that upload has long since given up on.
    """
    logger.info("Loading the image processing model...")

    import app.services.image_processing  # noqa: F401

    logger.info("Image processing model ready")


def main() -> None:
    _load_model()

    redis_conn = Redis.from_url(REDIS_URI)
    queue = Queue(QUEUE_NAME, connection=redis_conn)
    worker = SimpleWorker([queue], connection=redis_conn)

    logger.info(f"Image worker starting, listening on queue '{QUEUE_NAME}'")
    worker.work()


if __name__ == "__main__":
    main()

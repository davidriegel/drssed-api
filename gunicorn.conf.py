import os


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


bind = "0.0.0.0:8000"

# Default to 1 worker per CPU core, capped at 4 to avoid OOM on bigger hosts. Override via env on machines with more RAM.
_cpu_count = os.cpu_count() or 2
workers = _int_env("GUNICORN_WORKERS", min(4, max(2, _cpu_count)))
threads = _int_env("GUNICORN_THREADS", 2)
worker_class = "gthread"

timeout = _int_env("GUNICORN_TIMEOUT", 180)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)

preload_app = False

accesslog = None
errorlog = "-"
loglevel = "warning"

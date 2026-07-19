import os


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.strip() else default


bind = "0.0.0.0:8000"

workers = _int_env("GUNICORN_WORKERS", 2)
threads = _int_env("GUNICORN_THREADS", 4)
worker_class = "gthread"

timeout = _int_env("GUNICORN_TIMEOUT", 180)
graceful_timeout = _int_env("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int_env("GUNICORN_KEEPALIVE", 5)

preload_app = False

accesslog = None
errorlog = "-"
loglevel = "warning"

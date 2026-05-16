__all__ = ["spec", "db", "get_session"]

import os
from contextlib import contextmanager
from typing import Generator

from sqlspec import SQLSpec
from sqlspec.adapters.pymysql import PyMysqlConfig

from app.core.logging import get_logger

logger = get_logger()


def _get_required_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Required environment variable '{key}' is not set. "
            f"Check your .env file or docker-compose configuration."
        )
    return value


spec = SQLSpec()

db = spec.add_config(
    PyMysqlConfig(
        pool_config={
            "host": _get_required_env("DATABASE_HOST"),
            "port": int(os.getenv("DATABASE_PORT", "3306")),
            "user": _get_required_env("DATABASE_USERNAME"),
            "password": _get_required_env("DATABASE_PASSWORD"),
            "database": _get_required_env("DATABASE_NAME"),
            "charset": "utf8mb4",
            "autocommit": False,
            "maxconnections": int(os.getenv("DATABASE_POOL_SIZE", "10")),
        }
    )
)


@contextmanager
def get_session() -> Generator:
    """
    Provide a database session with automatic commit/rollback.
    
    Use for write operations or multi-statement transactions:
    
        with get_session() as session:
            session.execute("INSERT INTO ...", params)
            session.execute("INSERT INTO ...", params)
            # auto-commits if no exception, rolls back otherwise
    """
    session = None
    try:
        with spec.provide_session(db) as session:
            yield session
            session.commit()
    except Exception as e:
        if session is not None:
            try:
                session.rollback()
            except Exception as rollback_error:
                logger.error(
                    f"Failed to rollback transaction: {rollback_error}",
                    exc_info=True,
                )
        logger.error(f"Database session failed: {e}", exc_info=True)
        raise
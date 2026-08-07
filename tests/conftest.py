import os

import pytest

os.environ.setdefault("DATABASE_HOST", "127.0.0.1")
os.environ.setdefault("DATABASE_PORT", "3306")
os.environ.setdefault("DATABASE_USERNAME", "root")
os.environ.setdefault("DATABASE_PASSWORD", "root")
os.environ.setdefault("DATABASE_NAME", "drssed_test")
os.environ.setdefault("SECRET_TOKEN_KEY", "k" * 32)
os.environ.setdefault("RATELIMITER_ENABLED", "False")
os.environ.setdefault("EMAIL_ENABLED", "False")
os.environ.setdefault("DISABLE_SCHEDULER", "true")
os.environ.setdefault("FLASK_ENV", "testing")


def _database_reachable() -> bool:
    try:
        from app.persistence.queries import system as system_queries

        return system_queries.ping()
    except Exception:
        return False


needs_database = pytest.mark.skipif(
    not _database_reachable(), reason="no database reachable"
)


@pytest.fixture(scope="session")
def api():
    import main

    return main.api


@pytest.fixture
def client(api):
    return api.test_client()


@pytest.fixture
def user_ids():
    """Creates two throwaway users and removes them plus their rows afterwards."""
    from app.core.database import get_session

    owner, stranger = "test-owner", "test-stranger"

    with get_session() as session:
        session.execute(
            "DELETE FROM users WHERE user_id IN (:a, :b)", {"a": owner, "b": stranger}
        )
        session.execute(
            "INSERT INTO users (user_id, is_guest) VALUES (:a, 0), (:b, 0)",
            {"a": owner, "b": stranger},
        )

    yield owner, stranger

    with get_session() as session:
        session.execute(
            "DELETE FROM users WHERE user_id IN (:a, :b)", {"a": owner, "b": stranger}
        )

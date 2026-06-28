from app.core.database import spec, db
from app.persistence.schemas.cleanup import LockResult
from pydantic import BaseModel, ConfigDict


class _PingResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    ok: int


def ping() -> bool:
    """Runs a trivial SELECT to confirm the database connection is healthy."""
    with spec.provide_session(db) as session:
        result = session.select_one_or_none(
            "SELECT 1 AS ok",
            {},
            schema_type=_PingResult,
        )
        return result is not None and result.ok == 1


def try_acquire_lock(session, lock_name: str) -> bool:
    """
    Attempts to acquire a named MySQL advisory lock without waiting.
    """
    result = session.select_one_or_none(
        "SELECT GET_LOCK(:lock_name, 0) AS acquired",
        {"lock_name": lock_name},
        schema_type=LockResult,
    )
    return result is not None and result.acquired == 1


def release_lock(session, lock_name: str) -> None:
    """Releases a named MySQL advisory lock acquired in this session."""
    session.execute(
        "SELECT RELEASE_LOCK(:lock_name)",
        {"lock_name": lock_name},
    )
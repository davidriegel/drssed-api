from app.persistence.schemas.cleanup import LockResult


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
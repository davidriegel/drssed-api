import pytest

from tests.conftest import needs_database

pytestmark = needs_database


def _set_password(user_id: str, password: str) -> None:
    from argon2 import PasswordHasher

    from app.core.database import get_session

    with get_session() as session:
        session.execute(
            "UPDATE users SET password_hash = :h WHERE user_id = :u",
            {"h": PasswordHasher().hash(password), "u": user_id},
        )


def _refresh_tokens(user_id: str) -> list[str]:
    from app.persistence.queries import refresh_token as refresh_token_queries

    return [row.refresh_token for row in refresh_token_queries.get_by_user_id(user_id)]


def test_wrong_current_password_is_unauthorized(user_ids):
    """A failed re-auth is 401, the same as every other wrong-credentials answer."""
    from app.services.authentication import authentication_manager
    from app.utils.exceptions import UnauthorizedError

    owner, _ = user_ids
    _set_password(owner, "correct-horse")

    with pytest.raises(UnauthorizedError):
        authentication_manager.change_password(owner, "wrong-horse", "new-password")


def test_account_without_a_password_is_unauthorized(user_ids):
    from app.services.authentication import authentication_manager
    from app.utils.exceptions import UnauthorizedError

    owner, _ = user_ids

    with pytest.raises(UnauthorizedError):
        authentication_manager.change_password(owner, "anything", "new-password")


def test_successful_change_replaces_every_refresh_token(user_ids):
    """The old tokens are revoked, so the returned pair is the only way back in."""
    from app.core.database import get_session
    from app.services.authentication import authentication_manager

    owner, _ = user_ids
    _set_password(owner, "correct-horse")

    with get_session() as session:
        session.execute(
            "INSERT INTO refresh_tokens (refresh_token, user_id) VALUES (:t, :u)",
            {"t": "stale-token", "u": owner},
        )

    token = authentication_manager.change_password(
        owner, "correct-horse", "new-password"
    )

    remaining = _refresh_tokens(owner)

    assert "stale-token" not in remaining
    assert remaining == [token.refresh_token]

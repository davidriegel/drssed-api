from app.core.database import get_session
from app.persistence.schemas.password_reset import PasswordResetToken


def get_by_token(token: str) -> PasswordResetToken | None:
    """Retrieves a non-expired password reset token by its token string."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT token, user_id, expires_at, used_at
            FROM password_resets
            WHERE token = :token AND expires_at > NOW()
            """,
            {"token": token},
            schema_type=PasswordResetToken,
        )


def create(session, token: PasswordResetToken) -> None:
    """
    Inserts a new password reset token.

    Session-parameter version: typically called inside a transaction that
    also expires previous tokens for the same user.
    """
    session.execute(
        """
        INSERT INTO password_resets (token, user_id, expires_at)
        VALUES (:token, :user_id, :expires_at)
        """,
        {
            "token": token.token,
            "user_id": token.user_id,
            "expires_at": token.expires_at,
        },
    )


def mark_as_used(session, token: str) -> None:
    """
    Marks a password reset token as used.

    Session-parameter version: typically called inside a transaction with
    user_queries.update_password_hash_in_session.
    """
    session.execute(
        """
        UPDATE password_resets
        SET used_at = NOW()
        WHERE token = :token
        """,
        {"token": token},
    )


def expire_for_user(session, user_id: str) -> None:
    """
    Expires all active password reset tokens for a user.

    Session-parameter version: typically called inside a transaction that
    also creates a new token.
    """
    session.execute(
        """
        UPDATE password_resets
        SET expires_at = NOW()
        WHERE user_id = :user_id
          AND expires_at > NOW()
        """,
        {"user_id": user_id},
    )

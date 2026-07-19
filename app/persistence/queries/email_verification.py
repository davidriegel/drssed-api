from app.core.database import get_session
from app.persistence.schemas.email_verification import EmailVerificationToken


def get_by_token(token: str) -> EmailVerificationToken | None:
    """Retrieves a non-expired email verification token by its token string."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT token, email, user_id, expires_at, used_at
            FROM email_verifications
            WHERE token = :token AND expires_at > NOW()
            """,
            {"token": token},
            schema_type=EmailVerificationToken,
        )


def create(session, token: EmailVerificationToken) -> None:
    """
    Inserts a new email verification token.

    Session-parameter version: typically called inside a transaction that
    also expires previous tokens for the same user.
    """
    session.execute(
        """
        INSERT INTO email_verifications (token, email, user_id, expires_at)
        VALUES (:token, :email, :user_id, :expires_at)
        """,
        {
            "token": token.token,
            "email": token.email,
            "user_id": token.user_id,
            "expires_at": token.expires_at,
        },
    )


def mark_as_used(session, token: str) -> None:
    """
    Marks an email verification token as used.

    Session-parameter version: typically called inside a transaction with
    user_queries.mark_email_as_verified.
    """
    session.execute(
        """
        UPDATE email_verifications
        SET used_at = NOW()
        WHERE token = :token
        """,
        {"token": token},
    )


def expire_for_user(session, user_id: str) -> None:
    """
    Expires all active email verification tokens for a user.

    Session-parameter version: typically called inside a transaction that
    also creates a new token.
    """
    session.execute(
        """
        UPDATE email_verifications
        SET expires_at = NOW()
        WHERE user_id = :user_id
          AND expires_at > NOW()
        """,
        {"user_id": user_id},
    )

from app.core.database import spec, db
from app.persistence.schemas.refresh_token import RefreshToken


def get_by_token(refresh_token: str) -> RefreshToken | None:
    """Retrieves a refresh token from the database using the token string."""
    with spec.provide_session(db) as session:
        return session.select_one_or_none(
            """
            SELECT refresh_token, user_id, refresh_token_expiry
            FROM auth_tokens
            WHERE refresh_token = :refresh_token
            """,
            {"refresh_token": refresh_token},
            schema_type=RefreshToken,
        )


def get_by_user_id(user_id: str) -> list[RefreshToken]:
    """Retrieves all refresh tokens for a given user ID, ordered by expiry date."""
    with spec.provide_session(db) as session:
        return session.select(
            """
            SELECT refresh_token, user_id, refresh_token_expiry
            FROM auth_tokens
            WHERE user_id = :user_id
            ORDER BY refresh_token_expiry ASC
            """,
            {"user_id": user_id},
            schema_type=RefreshToken,
        )


def create(refresh_token: RefreshToken) -> None:
    """Inserts a new refresh token into the database."""
    with spec.provide_session(db) as session:
        session.execute(
            """
            INSERT INTO auth_tokens (refresh_token, user_id, refresh_token_expiry)
            VALUES (:refresh_token, :user_id, :refresh_token_expiry)
            """,
            {
                "refresh_token": refresh_token.refresh_token,
                "user_id": refresh_token.user_id,
                "refresh_token_expiry": refresh_token.refresh_token_expiry,
            },
        )


def update(old_refresh_token: str, new_refresh_token: RefreshToken) -> None:
    """Replaces an existing refresh token with a new one."""
    with spec.provide_session(db) as session:
        session.execute(
            """
            UPDATE auth_tokens
            SET refresh_token = :new_refresh_token,
                refresh_token_expiry = :refresh_token_expiry
            WHERE refresh_token = :old_refresh_token
            """,
            {
                "new_refresh_token": new_refresh_token.refresh_token,
                "refresh_token_expiry": new_refresh_token.refresh_token_expiry,
                "old_refresh_token": old_refresh_token,
            },
        )


def delete_by_token(refresh_token: str) -> None:
    """Deletes a refresh token from the database using the token string."""
    with spec.provide_session(db) as session:
        session.execute(
            "DELETE FROM auth_tokens WHERE refresh_token = :refresh_token",
            {"refresh_token": refresh_token},
        )


def delete_by_user_id(user_id: str) -> None:
    """Deletes all refresh tokens associated with a given user ID."""
    with spec.provide_session(db) as session:
        session.execute(
            "DELETE FROM auth_tokens WHERE user_id = :user_id",
            {"user_id": user_id},
        )
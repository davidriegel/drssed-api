from datetime import datetime

from app.core.database import get_session
from app.persistence.schemas.cleanup import FileReference
from app.persistence.schemas.user import (
    UserCreate,
    UserEmailVerificationStatus,
    UserExistsCheck,
    UserGuestStatus,
    UserProfile,
    UserPublicProfile,
    UserSignIn,
)

# Reads


def get_profile_by_id(user_id: str) -> UserProfile | None:
    """Fetches full profile information for a user by their ID."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, is_guest, username, email, profile_picture, email_verified_at, preferred_language, created_at, updated_at, last_active_at
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
            schema_type=UserProfile,
        )


def get_public_profile_by_id(user_id: str) -> UserPublicProfile | None:
    """Fetches public profile information for a user by their ID."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, is_guest, username, profile_picture, created_at
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
            schema_type=UserPublicProfile,
        )


def get_for_login_by_email(email: str) -> UserSignIn | None:
    """Retrieves user_id and password hash needed for login by email."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, password_hash
            FROM users
            WHERE email = :email
            """,
            {"email": email},
            schema_type=UserSignIn,
        )


def get_for_login_by_username(username: str) -> UserSignIn | None:
    """Retrieves user_id and password hash needed for login by username."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, password_hash
            FROM users
            WHERE username = :username
            """,
            {"username": username},
            schema_type=UserSignIn,
        )


def get_password_hash_by_id(user_id: str) -> UserSignIn | None:
    """Retrieves the password hash for the given user_id."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, password_hash
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
            schema_type=UserSignIn,
        )


def get_guest_status(user_id: str) -> UserGuestStatus | None:
    """Checks if a user is a guest."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, is_guest
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
            schema_type=UserGuestStatus,
        )


def get_email_verification_status(user_id: str) -> UserEmailVerificationStatus | None:
    """Fetches email verification status for a user."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT user_id, email, email_verified_at, preferred_language
            FROM users
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
            schema_type=UserEmailVerificationStatus,
        )


def email_exists(email: str) -> bool:
    """Checks whether a given email is already registered."""
    with get_session() as session:
        result = session.select_one_or_none(
            "SELECT user_id FROM users WHERE email = :email LIMIT 1",
            {"email": email},
            schema_type=UserExistsCheck,
        )
        return result is not None


def username_exists(username: str) -> bool:
    """Checks whether a given username is already taken."""
    with get_session() as session:
        result = session.select_one_or_none(
            "SELECT user_id FROM users WHERE username = :username LIMIT 1",
            {"username": username},
            schema_type=UserExistsCheck,
        )
        return result is not None


# Writes


def create(user: UserCreate) -> None:
    """Inserts a new user into the database."""
    with get_session() as session:
        session.execute(
            """
            INSERT INTO users (user_id, is_guest, username, email, profile_picture, password_hash, apple_user_id, preferred_language)
            VALUES (:user_id, :is_guest, :username, :email, :profile_picture, :password_hash, :apple_user_id, :preferred_language)
            """,
            user.model_dump(),
        )


def upgrade_guest_account(
    user_id: str,
    password_hash: str,
    profile_picture: str,
    email: str | None,
    username: str | None,
) -> None:
    """Converts a guest account to a regular account."""
    with get_session() as session:
        session.execute(
            """
            UPDATE users
            SET is_guest = FALSE,
                email = :email,
                username = :username,
                password_hash = :password_hash,
                profile_picture = :profile_picture
            WHERE user_id = :user_id AND is_guest = TRUE
            """,
            {
                "email": email,
                "username": username,
                "password_hash": password_hash,
                "profile_picture": profile_picture,
                "user_id": user_id,
            },
        )


def update_last_active_at(user_id: str) -> None:
    """Updates the last_active_at timestamp for a user to now."""
    with get_session() as session:
        session.execute(
            """
            UPDATE users
            SET last_active_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
            """,
            {"user_id": user_id},
        )


def mark_email_as_verified(session, user_id: str, email: str) -> None:
    """
    Sets the user's email to the verified address and marks it verified.

    Session-parameter version: meant to be called inside a transaction
    that also marks the corresponding email verification token as used.

    Setting `email` from the verification token is what makes the change-email
    flow work: the new address is only persisted once the user proves control.
    """
    session.execute(
        """
        UPDATE users
        SET email = :email,
            email_verified_at = CURRENT_TIMESTAMP
        WHERE user_id = :user_id
        """,
        {"user_id": user_id, "email": email},
    )


def update_password_hash(user_id: str, password_hash: str) -> None:
    """Updates the password hash for a user."""
    with get_session() as session:
        session.execute(
            """
            UPDATE users
            SET password_hash = :password_hash
            WHERE user_id = :user_id
            """,
            {"user_id": user_id, "password_hash": password_hash},
        )


def delete_by_id(user_id: str) -> None:
    """Deletes a user account by their ID."""
    with get_session() as session:
        session.execute(
            "DELETE FROM users WHERE user_id = :user_id",
            {"user_id": user_id},
        )


def get_inactive_guest_ids(
    session,
    cutoff: datetime,
    limit: int,
) -> list[UserExistsCheck]:
    """
    Returns user_ids of guest accounts inactive since cutoff.
    """
    return session.select(
        """
        SELECT user_id
        FROM users
        WHERE is_guest = TRUE AND last_active_at < :cutoff
        LIMIT :limit
        """,
        {"cutoff": cutoff, "limit": limit},
        schema_type=UserExistsCheck,
    )


def delete_by_id_in_session(session, user_id: str) -> None:
    """
    Deletes a user account by ID, within an externally-managed session.
    """
    session.execute(
        "DELETE FROM users WHERE user_id = :user_id",
        {"user_id": user_id},
    )


def get_referenced_profile_pictures(session) -> list[FileReference]:
    """Returns all profile picture filenames currently referenced in users."""
    return session.select(
        """
        SELECT profile_picture AS file_id
        FROM users
        WHERE profile_picture IS NOT NULL
        """,
        {},
        schema_type=FileReference,
    )

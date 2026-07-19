from pydantic import BaseModel, ConfigDict

from app.persistence.schemas.types import UtcDatetime


class UserPublicProfile(BaseModel):
    """
    Used for returning public user profile information to the client.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    is_guest: bool
    username: str | None
    profile_picture: str | None
    created_at: UtcDatetime


class UserProfile(BaseModel):
    """
    Used for returning the current user's profile information to the client.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    is_guest: bool
    username: str | None
    email: str | None
    profile_picture: str | None
    email_verified_at: UtcDatetime | None
    preferred_language: str
    created_at: UtcDatetime
    updated_at: UtcDatetime
    last_active_at: UtcDatetime | None


class UserSignIn(BaseModel):
    """
    Used for authentication flows.
    Includes the password hash, which should never leave the auth layer.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    password_hash: str


class UserExistsCheck(BaseModel):
    """
    Used for quick existence checks during signup.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str


class UserGuestStatus(BaseModel):
    """
    Used for checking if a user is a guest or not.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    is_guest: bool


class UserEmailVerificationStatus(BaseModel):
    """
    Used for checking if a user's email is verified or not.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    email: str
    email_verified_at: UtcDatetime | None
    preferred_language: str


class UserCreate(BaseModel):
    """
    Used for creating a new user in the database.
    Shouldn't be used as a query result.
    """

    user_id: str
    is_guest: bool = True
    username: str | None = None
    profile_picture: str | None = None
    email: str | None = None
    password_hash: str | None = None
    apple_user_id: str | None = None
    preferred_language: str = "en"

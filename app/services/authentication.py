__all__ = ["authentication_manager"]

import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Optional
from urllib.parse import urljoin

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.database import get_session
from app.core.email import send_password_reset_email, send_verification_email
from app.core.logging import get_logger
from app.models.token import AccessToken, Token
from app.persistence.queries import email_verification as email_verification_queries
from app.persistence.queries import password_reset as password_reset_queries
from app.persistence.queries import refresh_token as refresh_token_queries
from app.persistence.queries import user as user_queries
from app.persistence.schemas import email_verification as email_verification_schemas
from app.persistence.schemas import password_reset as password_reset_schemas
from app.persistence.schemas import refresh_token as refresh_token_schemas
from app.persistence.schemas import user as user_schemas
from app.utils.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionError,
    UnauthorizedError,
    ValidationError,
)
from app.utils.helpers import ensure_utc

SECRET_TOKEN_KEY = getenv("SECRET_TOKEN_KEY")

if not SECRET_TOKEN_KEY or len(SECRET_TOKEN_KEY) < 32:
    raise RuntimeError("⚠️ SECRET_TOKEN_KEY must be set and at least 32 characters long")

ACCESS_TOKEN_EXPIRY_HOURS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 90
REFRESH_TOKEN_LENGTH = 16

EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = 1

logger = get_logger()


class AuthenticationManager:
    def create_email_verification(self, user_id: str, preferred_language: str) -> None:
        is_verified = user_queries.get_email_verification_status(user_id)

        if is_verified and is_verified.email_verified_at:
            raise ConflictError

        if not is_verified or not is_verified.email:
            raise NotFoundError

        new_verification_token = email_verification_schemas.EmailVerificationToken(
            token=secrets.token_urlsafe(24),
            email=is_verified.email,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS),
            used_at=None,
        )

        with get_session() as session:
            email_verification_queries.expire_for_user(session, user_id)
            email_verification_queries.create(session, new_verification_token)

        public_url = str(
            urljoin(
                getenv("API_BASE_URL", ""),
                f"/auth/email/verify?token={new_verification_token.token}",
            )
        )

        send_verification_email(
            is_verified.email,
            preferred_language,
            public_url,
            EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS,
        )

    def verify_email(self, token: str) -> str:
        email_verification_token = email_verification_queries.get_by_token(token)

        if not email_verification_token:
            raise NotFoundError

        if email_verification_token.used_at:
            if ensure_utc(email_verification_token.used_at) < datetime.now(
                timezone.utc
            ):
                return email_verification_token.email

        with get_session() as session:
            email_verification_queries.mark_as_used(session, token)
            user_queries.mark_email_as_verified(
                session,
                email_verification_token.user_id,
                email_verification_token.email,
            )

        return email_verification_token.email

    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        :params refresh_token str:
        :returns Token: A new access token, its expiry in seconds, and a new refresh token
        """
        refresh_token_model = refresh_token_queries.get_by_token(refresh_token)

        if not refresh_token_model:
            raise UnauthorizedError

        if refresh_token_model.refresh_token_expiry and ensure_utc(
            refresh_token_model.refresh_token_expiry
        ) < datetime.now(timezone.utc):
            raise UnauthorizedError

        user_id = refresh_token_model.user_id

        user_guest_status = user_queries.get_guest_status(user_id)
        is_guest = user_guest_status.is_guest if user_guest_status else False
        access_token = self._generate_access_token(
            refresh_token_model.user_id, is_guest=is_guest
        )
        new_refresh_token = self._generate_refresh_token(
            user_id=user_id, with_expiry=not is_guest
        )

        refresh_token_queries.update(refresh_token, new_refresh_token)
        user_queries.update_last_active_at(user_id)

        return Token(
            access_token=access_token.access_token,
            expires_in=access_token.expires_in,
            refresh_token=new_refresh_token.refresh_token,
        )

    def revoke_all_refresh_tokens(self, user_id: str) -> None:
        """
        :params user_id str: The ID of the user whose refresh tokens should be revoked
        """
        refresh_token_queries.delete_by_user_id(user_id)

    def delete_refresh_token(self, refresh_token: str) -> None:
        """
        :params refresh_token str:
        """
        refresh_token_queries.delete_by_token(refresh_token)

    def register_guest(self, preferred_language: str = "en") -> Token:
        """
        :returns Token: A new access token, its expiry in seconds, and a new refresh token
        """
        user_id = self._add_user_to_database(preferred_language=preferred_language)

        return self._generate_token_pair(user_id, is_guest=True)

    def sign_in_user(
        self, email: Optional[str], username: Optional[str], password: str
    ) -> Token:
        if not email and not username:
            raise ValueError

        if email:
            user_sign_in = user_queries.get_for_login_by_email(email)
        elif username:
            user_sign_in = user_queries.get_for_login_by_username(username)
        else:
            user_sign_in = None

        if not user_sign_in:
            raise UnauthorizedError

        try:
            PasswordHasher().verify(user_sign_in.password_hash, password)
        except VerifyMismatchError:
            raise UnauthorizedError

        return self._generate_token_pair(user_sign_in.user_id, is_guest=False)

    def register_user(
        self,
        email: str | None,
        username: str | None,
        password: str,
        profile_picture: str,
        preferred_language: str = "en",
    ) -> Token:
        """
        Use this method to register a new user without having a previous guest account.

        :param email: The email address of the user
        :param username: The username of the user
        :param password: The password of the user
        :param profile_picture: The profile picture of the user
        :param preferred_language: The preferred language of the user

        :return: The new access token, its expiry in seconds, and a new refresh token

        :raises ValidationError: If any form validation fails
        :raises ConflictError: If either email or username already exists
        :raises ValueError: If user does not exist after adding to database
        """
        user_id = self._add_user_to_database(
            is_guest=False,
            email=email,
            username=username,
            password=password,
            profile_picture=profile_picture,
            preferred_language=preferred_language,
        )

        return self._generate_token_pair(user_id, is_guest=False)

    def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> Token:
        if len(new_password) < 8:
            raise ValidationError

        user_sign_in = user_queries.get_password_hash_by_id(user_id)

        if not user_sign_in or not user_sign_in.password_hash:
            raise PermissionError

        hasher = PasswordHasher()

        try:
            hasher.verify(user_sign_in.password_hash, current_password)
        except VerifyMismatchError:
            raise PermissionError

        new_hash = hasher.hash(new_password)
        user_queries.update_password_hash(user_id, new_hash)

        refresh_token_queries.delete_by_user_id(user_id)

        return self._generate_token_pair(user_id, is_guest=False)

    def request_password_reset(self, email: str, preferred_language: str) -> None:
        """
        Sends a password reset link to the given address, if it belongs to an
        account that can sign in with a password.

        Returns without raising when no such account exists, so that callers
        cannot use this method to find out which addresses are registered.

        :param email: The email address the reset link is requested for
        :param preferred_language: The language the email is sent in

        :raises ValidationError: If the email is not a valid address
        """
        email = email.strip().lower()

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            raise ValidationError

        user_sign_in = user_queries.get_for_login_by_email(email)

        if not user_sign_in or not user_sign_in.password_hash:
            logger.debug("Password reset requested for an account without password")
            return

        new_reset_token = password_reset_schemas.PasswordResetToken(
            token=secrets.token_urlsafe(24),
            user_id=user_sign_in.user_id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRY_HOURS),
            used_at=None,
        )

        with get_session() as session:
            password_reset_queries.expire_for_user(session, user_sign_in.user_id)
            password_reset_queries.create(session, new_reset_token)

        public_url = str(
            urljoin(
                getenv("API_BASE_URL", ""),
                f"/auth/password/reset?token={new_reset_token.token}",
            )
        )

        send_password_reset_email(
            email,
            preferred_language,
            public_url,
            PASSWORD_RESET_TOKEN_EXPIRY_HOURS,
        )

    def is_password_reset_token_valid(self, token: str) -> bool:
        """
        :params token str: The password reset token to check

        :returns bool: True if the token exists, is unused and not expired
        """
        reset_token = password_reset_queries.get_by_token(token)

        return bool(reset_token and not reset_token.used_at)

    def reset_password(self, token: str, new_password: str) -> None:
        """
        Sets a new password from a password reset token and signs the user out
        everywhere by revoking all refresh tokens.

        :param token: The password reset token from the emailed link
        :param new_password: The new password of the user

        :raises NotFoundError: If the token is unknown, expired or already used
        :raises ValidationError: If the new password is too short
        """
        reset_token = password_reset_queries.get_by_token(token)

        if not reset_token or reset_token.used_at:
            raise NotFoundError

        if len(new_password) < 8:
            raise ValidationError

        new_hash = PasswordHasher().hash(new_password)

        with get_session() as session:
            password_reset_queries.mark_as_used(session, token)
            user_queries.update_password_hash_in_session(
                session, reset_token.user_id, new_hash
            )

        refresh_token_queries.delete_by_user_id(reset_token.user_id)

    def request_email_change(
        self,
        user_id: str,
        current_password: str,
        new_email: str,
        preferred_language: str,
    ) -> str:
        new_email = new_email.strip().lower()

        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", new_email):
            raise ValidationError

        user_sign_in = user_queries.get_password_hash_by_id(user_id)

        if not user_sign_in or not user_sign_in.password_hash:
            raise UnauthorizedError

        try:
            PasswordHasher().verify(user_sign_in.password_hash, current_password)
        except VerifyMismatchError:
            raise UnauthorizedError

        current_status = user_queries.get_email_verification_status(user_id)

        if current_status and current_status.email == new_email:
            raise ConflictError(field="email")

        if user_queries.email_exists(new_email):
            raise ConflictError(field="email")

        new_verification_token = email_verification_schemas.EmailVerificationToken(
            token=secrets.token_urlsafe(24),
            email=new_email,
            user_id=user_id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS),
            used_at=None,
        )

        with get_session() as session:
            email_verification_queries.expire_for_user(session, user_id)
            email_verification_queries.create(session, new_verification_token)

        public_url = str(
            urljoin(
                getenv("API_BASE_URL", ""),
                f"/auth/email/verify?token={new_verification_token.token}",
            )
        )

        send_verification_email(
            new_email,
            preferred_language,
            public_url,
            EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS,
        )

        return new_email

    def get_user_id_from_token(self, token: str) -> str:
        payload = self._get_payload_from_access_token(token)

        user_id = payload.get("sub")

        if not isinstance(user_id, str):
            raise UnauthorizedError

        return user_id

    def get_is_guest_from_token(self, token: str) -> bool:
        payload = self._get_payload_from_access_token(token)

        is_guest = payload.get("is_guest")

        if not isinstance(is_guest, bool):
            raise UnauthorizedError

        return is_guest

    def _generate_token_pair(self, user_id: str, is_guest: bool) -> Token:
        refresh_tokens = refresh_token_queries.get_by_user_id(user_id)

        if refresh_tokens and len(refresh_tokens) >= 5:
            oldest_token = refresh_tokens[0]

            refresh_token_queries.delete_by_token(oldest_token.refresh_token)

        refresh_token = self._generate_refresh_token(
            user_id=user_id, with_expiry=not is_guest
        )

        refresh_token_queries.create(refresh_token)

        access_token = self._generate_access_token(user_id, is_guest=is_guest)

        token = Token(
            access_token=access_token.access_token,
            expires_in=access_token.expires_in,
            refresh_token=refresh_token.refresh_token,
        )

        return token

    def _add_user_to_database(
        self,
        is_guest: bool = True,
        email: str | None = None,
        username: str | None = None,
        password: str | None = None,
        profile_picture: str | None = None,
        preferred_language: str = "en",
    ) -> str:
        """
        This private function is used to add a user to the database, with verifications for optional emails etc.

        :param is_guest: Defaults to true, to insert new guest accounts quickly
        :param email: Defaults to None, if is not None, verifies email
        :param username: Defaults to None, if is not None, verifies username
        :param password: Defaults to None, if is not None, verifies password and hashes it
        :param profile_picture: Defaults to None, if is not None, verifies profile picture against default options
        :param preferred_language: Defaults to "en"

        """
        user_id = str(uuid.uuid4())
        hashed_password = None

        if isinstance(password, str):
            if len(password) < 8:
                raise ValidationError

            hashed_password = PasswordHasher().hash(password)

        if isinstance(profile_picture, str):
            default_profile_pictures = [
                os.path.splitext(file)[0]
                for file in os.listdir("app/static/profile_pictures/default/")
            ]

            if profile_picture not in default_profile_pictures:
                raise ValidationError

            profile_picture = f"default/{profile_picture}"

            if isinstance(email, str):
                email = email.strip().lower()

                if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                    raise ValidationError

                if user_queries.email_exists(email):
                    raise ConflictError(field="email")
            else:
                email = None

        if isinstance(username, str):
            username = username.strip().lower()

            if len(username) < 3:
                raise ValidationError
            if len(username) > 20:
                raise ValidationError

            if not re.match(r"^[a-zA-Z0-9_]+$", username):
                raise ValidationError

            if user_queries.username_exists(username):
                raise ConflictError(field="username")
        else:
            username = None

        user = user_schemas.UserCreate(
            user_id=user_id,
            is_guest=is_guest,
            email=email,
            username=username,
            password_hash=hashed_password,
            profile_picture=profile_picture,
            preferred_language=preferred_language,
        )

        user_queries.create(user)

        return user_id

    def _get_payload_from_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, SECRET_TOKEN_KEY, algorithms=["HS256"])
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError):
            raise UnauthorizedError

    def _generate_refresh_token(
        self, user_id: str, with_expiry: bool = True
    ) -> refresh_token_schemas.RefreshToken:
        refresh_token = "".join(secrets.token_urlsafe(REFRESH_TOKEN_LENGTH))
        refresh_token_expiry = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRY_DAYS
        )

        return refresh_token_schemas.RefreshToken(
            refresh_token=refresh_token,
            user_id=user_id,
            refresh_token_expiry=refresh_token_expiry if with_expiry else None,
        )

    def _generate_access_token(self, user_id: str, is_guest: bool) -> AccessToken:
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc)
            + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS),
            "is_guest": is_guest,
        }
        access_token = jwt.encode(payload, SECRET_TOKEN_KEY, algorithm="HS256")
        return AccessToken(
            access_token=access_token, expires_in=ACCESS_TOKEN_EXPIRY_HOURS * 60 * 60
        )


authentication_manager = AuthenticationManager()

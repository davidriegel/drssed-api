__all__ = ["user_manager"]

import os
import re
from typing import Optional

from argon2 import PasswordHasher

from app.core.logging import get_logger
from app.persistence.queries import user as user_queries
from app.persistence.schemas import user as user_schemas
from app.utils.exceptions import (
    ConflictError,
    NotFoundError,
    UserNotFoundError,
    ValidationError,
)

logger = get_logger()


class UserManager:
    def upgrade_guest_account(
        self,
        user_id: str,
        password: str,
        profile_picture: str,
        email: Optional[str],
        username: Optional[str],
    ) -> user_schemas.UserProfile:
        if len(password) < 8:
            raise ValidationError

        default_profile_pictures = [
            os.path.splitext(file)[0]
            for file in os.listdir("app/static/profile_pictures/default/")
        ]
        if profile_picture not in default_profile_pictures:
            raise ValidationError

        if profile_picture in default_profile_pictures:
            profile_picture = f"default/{profile_picture}"

        if email:
            email = email.strip().lower()

            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                raise ValidationError

            if user_queries.email_exists(email):
                raise ConflictError(field="email")
        else:
            email = None

        if username:
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

        hashed_password = PasswordHasher().hash(password)

        user_queries.upgrade_guest_account(
            user_id, hashed_password, profile_picture, email, username
        )

        user = user_queries.get_profile_by_id(user_id)

        if not user:
            raise UserNotFoundError

        return user

    def get_public_user_profile_by_id(
        self, user_id: str
    ) -> user_schemas.UserPublicProfile:
        user = user_queries.get_public_profile_by_id(user_id)

        if not user:
            raise NotFoundError()

        return user

    def get_private_user_profile_by_id(self, user_id: str) -> user_schemas.UserProfile:
        user = user_queries.get_profile_by_id(user_id)

        if not user:
            raise NotFoundError()

        return user

    def delete_account_by_id(self, user_id: str) -> None:
        user_queries.delete_by_id(user_id)


user_manager = UserManager()

__all__ = ["user_manager"]

import traceback
import os
from typing import Optional
from app.utils.database import Database
from app.utils.exceptions import ValidationError, NotFoundError, ConflictError, UsernameTooShortError, UsernameMissingError, UsernameAlreadyInUseError, AuthCredentialsWrongError, UserNotFoundError
from app.utils.helpers import helper
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from mysql.connector.errors import IntegrityError
from app.models.user import User
import re
from app.utils.logging import get_logger

logger = get_logger()

class UserManager:
    def upgrade_guest_account(self, user_id: str, password: str, profile_picture: str, email: Optional[str], username: Optional[str]) -> User:
        if not isinstance(password, str) or not password.strip():
            raise ValidationError("Password is required.")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        allowed_pictures = [os.path.splitext(file)[0] for file in os.listdir("app/static/profile_pictures/default/")]
        if profile_picture not in allowed_pictures:
            raise ValidationError("Profile picture must be from the default options.")
        
        if email:
            email = email.strip().lower()
            
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                raise ValidationError("The provided email is invalid.")
        else:
            email = None
                
        if username:
            username = username.strip().lower()
            
            if len(username) < 3:
                raise ValidationError("Username must be at least 3 characters long.")
            if len(username) > 20:
                raise ValidationError("Username must be at most 20 characters long.")
        else:
            username = None
        
        hashed_password = PasswordHasher().hash(password)
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("UPDATE users SET is_guest = FALSE, email = %s, username = %s, password = %s, profile_picture = %s WHERE user_id = %s AND is_guest = TRUE;", (email, username, hashed_password, profile_picture, user_id))
                
                if cursor.rowcount == 0:
                    raise NotFoundError(f"No guest account found with user_id: {user_id}")
                
                cursor.execute("SELECT user_id, is_guest, username, email, created_at, updated_at, profile_picture FROM users WHERE user_id = %s;", (user_id,))
                db_user = cursor.fetchone()

                user = User.from_dict(helper.ensure_dict(db_user))
                
                conn.commit()
        except IntegrityError as e:
            if e.msg and "email" in e.msg:
                raise ConflictError("The provided email is already in use.")
            elif e.msg and "username" in e.msg:
                raise ConflictError("The provided username is already in use.")
            else:
                logger.error(f"Unexpected IntegrityError: {e.msg}")
                raise Exception(e.msg)
        except Exception as e:
            logger.error(f"An unexpected error occurred while upgrading a guest account: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        return user
        
    def delete_account(self, user_id: str, password: str) -> None:
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE user_id = %s;", (user_id, ))
                result = cursor.fetchone()
                
                if result is None:
                    raise UserNotFoundError
                
                hashed_password, = result
            
                PasswordHasher().verify(str(hashed_password), password)
                
                cursor.execute("DELETE FROM users WHERE user_id = %s;", (user_id, ))
                conn.commit()
        except VerifyMismatchError:
            raise AuthCredentialsWrongError
        except Exception as e:
            logger.error(f"An unexpected error occurred while trying to delete a user: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    def get_public_user_profile_by_id(self, user_id: str) -> User:
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT user_id, is_guest, created_at, NULL as updated_at, username, NULL as email, profile_picture FROM users WHERE user_id = %s;", (user_id, ))
                db_user = helper.ensure_dict(cursor.fetchone())
                
                user = User.from_dict(db_user)
                
                return user
        except Exception as e:
            logger.error(f"An unexpected error occurred while getting user profile from database: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    def get_private_user_profile_by_id(self, user_id: str) -> User:
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT user_id, is_guest, created_at, updated_at, username, email, profile_picture FROM users WHERE user_id = %s;", (user_id, ))
                db_user = helper.ensure_dict(cursor.fetchone())
                
                user = User.from_dict(db_user)
                
                return user
        except Exception as e:
            logger.error(f"An unexpected error occurred while getting user profile from database: {e}")
            logger.error(traceback.format_exc())
            raise e

user_manager = UserManager()
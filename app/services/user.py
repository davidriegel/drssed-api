__all__ = ["user_manager"]

import traceback
import os
from typing import Optional
from app.core.database import Database
from app.utils.exceptions import ValidationError, NotFoundError, ConflictError, UnauthorizedError, UserNotFoundError
from app.utils.helpers import helper
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from mysql.connector.errors import IntegrityError
from app.models.user import User
import re
from app.core.logging import get_logger

logger = get_logger()

class UserManager:
    def upgrade_guest_account(self, user_id: str, password: str, profile_picture: str, email: Optional[str], username: Optional[str]) -> User:
        if len(password) < 8:
            raise ValidationError
        
        default_profile_pictures = [os.path.splitext(file)[0] for file in os.listdir("app/static/profile_pictures/default/")]
        if profile_picture not in default_profile_pictures:
            raise ValidationError
        
        if profile_picture in default_profile_pictures:
            profile_picture = f"default/{profile_picture}"
        
        if email:
            email = email.strip().lower()
            
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                raise ValidationError
        else:
            email = None
                
        if username:
            username = username.strip().lower()
            
            if len(username) < 3:
                raise ValidationError
            if len(username) > 20:
                raise ValidationError
        else:
            username = None
        
        hashed_password = PasswordHasher().hash(password)
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("UPDATE users SET is_guest = FALSE, email = %s, username = %s, password = %s, profile_picture = %s WHERE user_id = %s AND is_guest = TRUE;", (email, username, hashed_password, profile_picture, user_id))
                
                if cursor.rowcount == 0:
                    raise NotFoundError
                
                cursor.execute("SELECT user_id, is_guest, username, email, created_at, updated_at, profile_picture FROM users WHERE user_id = %s;", (user_id,))
                db_user = cursor.fetchone()

                user = User.from_dict(helper.ensure_dict(db_user))
                
                conn.commit()
        except IntegrityError as e:
            if e.msg and "email" in e.msg:
                raise ConflictError(field="email")
            elif e.msg and "username" in e.msg:
                raise ConflictError(field="username")
            else:
                raise e
        
        return user
        
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
        
    def delete_account_by_id(self, user_id: str, password: str) -> None:
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password FROM users WHERE user_id = %s;", (user_id, ))
                result = cursor.fetchone()
                
                if result is None:
                    # raise UnauthorizedError instead of NotFoundError to avoid giving away information about which user_ids exist
                    raise UnauthorizedError
                
                hashed_password, = result
            
                PasswordHasher().verify(str(hashed_password), password)
                
                cursor.execute("DELETE FROM users WHERE user_id = %s;", (user_id, ))
                conn.commit()
        except VerifyMismatchError:
            raise UnauthorizedError

user_manager = UserManager()
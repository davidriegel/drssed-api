__all__ = ["authentication_manager"]

import secrets
import uuid
import jwt
from os import getenv
from typing import Optional
import traceback
from datetime import datetime, timedelta
from flask import request, jsonify, g
from functools import wraps
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.utils.database import Database
from app.utils.exceptions import AuthValidationError, AuthTokenExpiredError, AuthAccessTokenInvalidError, AuthRefreshTokenInvalidError, AuthAccessTokenMissingError, AuthRefreshTokenMissingError, UserIDMissingError, AuthCredentialsWrongError, UnauthorizedError
from app.utils.logging import get_logger

SECRET_TOKEN_KEY = getenv("SECRET_TOKEN_KEY")

if not SECRET_TOKEN_KEY or len(SECRET_TOKEN_KEY) < 32:
    raise RuntimeError("⚠️ SECRET_TOKEN_KEY must be set and at least 32 characters long")

ACCESS_TOKEN_EXPIRY_HOURS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 90
REFRESH_TOKEN_LENGTH = 16

logger = get_logger()

class AuthenticationManager:
    def refresh_access_token(self, refresh_token: str) -> tuple[str, int, str]:
        """
        :params refresh_token str:
        :returns access_token: Fresh access token for user
        :returns expires_in: Expiry in seconds
        :returns refresh_token: New refresh token for user if user is signed in otherwise send back same refresh token
        """

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, refresh_token_expiry FROM refresh_tokens WHERE refresh_token = %s;", (refresh_token,))
                result = cursor.fetchone()

                if not result:
                    raise AuthRefreshTokenInvalidError("The provided refresh token is invalid.")
                
                if isinstance(result[1], datetime):
                    if result[1] < datetime.now():
                        raise AuthTokenExpiredError("The provided refresh token is expired.")

                user_id = result[0]
                
                cursor.execute("SELECT is_guest FROM users WHERE user_id = %s", (user_id, ))
                is_guest = cursor.fetchone()[0]
                    
                access_token = self._generate_access_token(user_id, is_guest=is_guest)
                new_refresh_token = self._generate_refresh_token()

                if is_guest:
                    cursor.execute("""
                                UPDATE refresh_tokens
                                SET refresh_token = %s
                                WHERE refresh_token = %s;
                                """, (new_refresh_token, refresh_token,))
                else:
                    refresh_token_expiry = (datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                                    UPDATE refresh_tokens
                                    SET refresh_token_expiry = %s, refresh_token = %s
                                    WHERE refresh_token = %s;
                                    """, (refresh_token_expiry, new_refresh_token, refresh_token,))
                    
                conn.commit()

            return access_token, ACCESS_TOKEN_EXPIRY_HOURS * 60 * 60, new_refresh_token
        except AuthValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while refreshing an access token: {e}")
            logger.error(traceback.format_exc())
            raise e
            
    def delete_refresh_token(self, refresh_token: str) -> None:
        """
        :params refresh_token str:
        """
        if not isinstance(refresh_token, str) or not refresh_token.strip():
            raise AuthRefreshTokenMissingError("The refresh_token is missing or invalid.")

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM refresh_tokens WHERE refresh_token = %s;", (refresh_token,))
                if cursor.rowcount < 1:
                    raise AuthRefreshTokenInvalidError("The provided refresh token is invalid.")

                conn.commit()
        except AuthValidationError:
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while deleting a refresh token: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    def register_guest(self) -> tuple[str, int, str]:
        """
        :returns access_token: Access token for user
        :returns expires_in: Expiry in seconds
        :returns refresh_token: Refresh token for user
        """
        try:
            user_id = self._add_user_to_database()
            
            access_token, expires_in, refresh_token = self._generate_token_pair(user_id, is_guest=True)
            
            return access_token, expires_in, refresh_token
        except Exception as e:
            logger.error(f"An unexpected error occurred while registering guest: {e}")
            raise
        
    def sign_in_user(self, email: Optional[str], username: Optional[str], password: str) -> tuple[str, int, str]:
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                if email:
                    cursor.execute("SELECT password, user_id FROM users WHERE email = %s", (email,))
                else:
                    cursor.execute("SELECT password, user_id FROM users WHERE username = %s", (username,))
                    
                user = cursor.fetchone()
            
                if not user:
                    raise UnauthorizedError
                
                db_password, db_user_id = user
                
                PasswordHasher().verify(str(db_password), password)
        except VerifyMismatchError:
            raise UnauthorizedError
        
        return self._generate_token_pair(str(db_user_id), False)

    def get_user_id_from_token(self, token: Optional[str]) -> str:
        if not isinstance(token, str) or not token.strip():
            raise AuthAccessTokenMissingError("The access_token is missing or invalid.")
        
        try:
            payload = self._get_payload_from_access_token(token)
            
            user_id = payload.get('sub')
            
            if not isinstance(user_id, str):
                raise AuthAccessTokenInvalidError
            
            return user_id
        except AuthValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while getting user ID from token: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    def _generate_token_pair(self, user_id: Optional[str], is_guest: Optional[bool]) -> tuple[str, int, str]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise UserIDMissingError("The user_id is missing or invalid.")
        
        if not isinstance(is_guest, bool):
            raise ValueError("The is_guest parameter must be a boolean value.")

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, refresh_token, refresh_token_expiry from refresh_tokens WHERE user_id = %s ORDER BY refresh_token_expiry ASC", (user_id, ))
                result = cursor.fetchall()
                
                if len(result) >= 5:
                    oldest = result[0]
                    cursor.execute("DELETE FROM refresh_tokens WHERE refresh_token = %s", (oldest[1], ))
            
                refresh_token = self._generate_refresh_token()
                refreshTokenExpiry = (datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
            
                if not is_guest:
                    cursor.execute("INSERT INTO refresh_tokens(user_id, refresh_token, refresh_token_expiry) VALUES (%s, %s, %s);", (user_id, refresh_token, refreshTokenExpiry))
                else:
                    cursor.execute("INSERT INTO refresh_tokens(user_id, refresh_token) VALUES(%s, %s);", (user_id, refresh_token))
                    
                conn.commit()

            access_token = self._generate_access_token(user_id, is_guest=is_guest)

            return access_token, ACCESS_TOKEN_EXPIRY_HOURS * 60 * 60, refresh_token
        except Exception as e:
            logger.error(f"An unexpected error occurred while generating a new token pair: {e}")
            logger.error(traceback.format_exc())
            raise
        
    def _add_user_to_database(self, is_guest: bool = True, email: str = None, username: str = None, password: str = None, profilePicture: str = None) -> str:
        user_id = str(uuid.uuid4())

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users(user_id, is_guest, email, username, password, profile_picture) VALUES (%s, %s, %s, %s, %s, %s);", (user_id, is_guest, email, username, password, profilePicture))
                conn.commit()
        except Exception as e:
            logger.error(f"An unexpected error occurred while creating user: {e}")
            logger.error(traceback.format_exc())
            
        return user_id
        
    def _verify_access_token(self, token: str) -> bool:
        try:
            jwt.decode(token, SECRET_TOKEN_KEY, algorithms=['HS256'])
            return True
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return False
        
    def _get_payload_from_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, SECRET_TOKEN_KEY, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthTokenExpiredError("The provided access token has expired.")
        except jwt.InvalidTokenError:
            raise AuthAccessTokenInvalidError("The provided access token is invalid.")

    def _generate_refresh_token(self) -> str:
        randRefreshToken = "".join(secrets.token_urlsafe(REFRESH_TOKEN_LENGTH))
        return f"{randRefreshToken}"

    def _generate_access_token(self, user_id: str, is_guest: bool) -> str:
        payload = {
            'sub': user_id,
            'exp': datetime.now() + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS),
            'is_guest': is_guest
        }
        return jwt.encode(payload, SECRET_TOKEN_KEY, algorithm='HS256')

authentication_manager = AuthenticationManager()
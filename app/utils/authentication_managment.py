__all__ = ["authentication_manager", "authorize_request"]

import random
import base64
import uuid
import jwt
from os import getenv
from typing import Optional
from string import ascii_letters, digits
import traceback
from datetime import datetime, timedelta
from flask import request, jsonify, g
from functools import wraps
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.utils.database import Database
from app.utils.exceptions import AuthValidationError, AuthTokenExpiredError, AuthAccessTokenInvalidError, AuthRefreshTokenInvalidError, AuthAccessTokenMissingError, AuthRefreshTokenMissingError, UserIDMissingError, AuthCredentialsWrongError, AuthCredentialsMissingError
from app.utils.logging import get_logger

SECRET_TOKEN_KEY = getenv("SECRET_TOKEN_KEY")
ACCESS_TOKEN_EXPIRY_HOURS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 90
REFRESH_TOKEN_LENGTH = 16

logger = get_logger()

def authorize_request(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "No token provided"}), 401

        if not authentication_manager._verify_access_token(token):
            return jsonify({"message": "Unauthorized access"}), 403

        user_id = authentication_manager.get_user_id_from_token(token)

        if not user_id:
            return jsonify({"message": "Unauthorized access"}), 403

        g.user_id = user_id

        return f(*args, **kwargs)

    return wrapper

class AuthenticationManager:
    
    def ensure_table_exists(self) -> None:
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS refresh_tokens(
                           user_id VARCHAR(36) NOT NULL,
                           refresh_token VARCHAR(24) PRIMARY KEY,
                           refresh_token_expiry TIMESTAMP DEFAULT NULL,
                           FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                           );
                           """)
            
            cursor.execute("""CREATE EVENT IF NOT EXISTS delete_expired_refresh_tokens
                            ON SCHEDULE EVERY 1 DAY
                            STARTS CONCAT(CURDATE(), ' 09:00:00')
                            DO
                            DELETE FROM refresh_tokens WHERE refresh_token_expiry < NOW();""")
            conn.commit()

    def refresh_access_token(self, old_access_token: Optional[str], refresh_token:  Optional[str]) -> tuple:
        if not isinstance(old_access_token, str) or not old_access_token.strip():
            raise AuthAccessTokenMissingError("The access_token is missing.")
        if not isinstance(refresh_token, str) or not refresh_token.strip():
            raise AuthRefreshTokenMissingError("The refresh_token is missing.")

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
            
    def delete_refresh_token(self, refresh_token: Optional[str]) -> None:
        if not isinstance(refresh_token, str) or not refresh_token.strip():
            raise AuthRefreshTokenMissingError("The refresh_token is missing or invalid.")

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM refresh_tokens WHERE refresh_token = %s;", (refresh_token,))
                if cursor.rowcount < 1:
                    raise AuthRefreshTokenInvalidError("The provided refresh token is invalid.")

                conn.commit()
        except AuthValidationError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while deleting a refresh token: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    def register_guest(self) -> tuple:
        try:
            user_id = self._add_user_to_database()

            return self._generate_token_pair(user_id, is_guest=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred while registering guest: {e}")
            raise
        
    def sign_in_user(self, email: Optional[str], username: Optional[str], password: Optional[str]) -> tuple:
        if not isinstance(email, str) and not isinstance(username, str):
            raise AuthCredentialsMissingError("Either email or username has to be given.")
        
        if not isinstance(password, str):
            raise AuthCredentialsMissingError("The password is missing.")
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT password, user_id, username, email FROM users WHERE email = %s OR username = %s", (email, username))
                user = cursor.fetchone()
            
                if not user:
                    raise AuthCredentialsWrongError("The provided sign in credentials are wrong.")
                
                db_password, db_user_id, db_username, db_email = user
                
                if email != db_email and str(db_username) != username:
                    raise AuthCredentialsWrongError("The provided sign in credentials are wrong.")
                
                try:
                    PasswordHasher().verify(str(db_password), password)
                except VerifyMismatchError:
                    raise AuthCredentialsWrongError("The provided sign in credentials are wrong.")
        except AuthCredentialsWrongError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while signing in the user: {e}")
            logger.error(traceback.format_exc())
            raise e
        
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
        
    def _generate_token_pair(self, user_id: Optional[str], is_guest: Optional[bool]) -> tuple:
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
                    
                conn.commit()
            
            refresh_token = self._generate_refresh_token()
            refreshTokenExpiry = (datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
            
            with Database.getConnection() as conn:
                cursor = conn.cursor()
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
        randRefreshToken = "".join(random.choices(ascii_letters + digits, k=REFRESH_TOKEN_LENGTH))
        randRefreshTokenb64 = base64.b64encode(randRefreshToken.encode()).decode()
        return f"{randRefreshTokenb64}"

    def _generate_access_token(self, user_id: str, is_guest: bool) -> str:
        payload = {
            'sub': user_id,
            'exp': datetime.now() + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS),
            'is_guest': is_guest
        }
        return jwt.encode(payload, SECRET_TOKEN_KEY, algorithm='HS256')

authentication_manager = AuthenticationManager()
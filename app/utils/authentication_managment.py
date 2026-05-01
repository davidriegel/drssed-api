__all__ = ["authentication_manager"]

import secrets
import uuid
import jwt
from os import getenv
from typing import Optional
import traceback
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.utils.database import Database
from app.models.token import Token
from app.utils.exceptions import UnauthorizedError
from app.utils.logging import get_logger

SECRET_TOKEN_KEY = getenv("SECRET_TOKEN_KEY")

if not SECRET_TOKEN_KEY or len(SECRET_TOKEN_KEY) < 32:
    raise RuntimeError("⚠️ SECRET_TOKEN_KEY must be set and at least 32 characters long")

ACCESS_TOKEN_EXPIRY_HOURS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 90
REFRESH_TOKEN_LENGTH = 16

logger = get_logger()

class AuthenticationManager:
    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        :params refresh_token str:
        :returns Token: A new access token, its expiry in seconds, and a new refresh token
        """
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, refresh_token_expiry FROM refresh_tokens WHERE refresh_token = %s;", (refresh_token,))
            result = cursor.fetchone()

            if not result or not isinstance(result, tuple):
                raise UnauthorizedError
            
            user_id, refresh_token_expiry = result
            
            if not isinstance(user_id, str):
                raise ValueError("expected user_id to be a str")
            
            if isinstance(refresh_token_expiry, datetime):
                if refresh_token_expiry < datetime.now():
                    raise UnauthorizedError
            
            cursor.execute("SELECT is_guest FROM users WHERE user_id = %s", (user_id, ))
            result = cursor.fetchone()
            
            if not result or not isinstance(result, tuple):
                cursor.execute("DELETE FROM refresh_tokens WHERE user_id = %s", (user_id,))
                conn.commit()
                raise Exception("Database integrity error: refresh token exists for non-existent user")
            
            is_guest, = result
            
            if not isinstance(is_guest, int) and not is_guest in (0, 1):
                raise ValueError("expected is_guest to be a int of value 0 or 1")

            access_token = self._generate_access_token(user_id, is_guest=bool(is_guest))
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

        return Token(access_token=access_token, expires_in=ACCESS_TOKEN_EXPIRY_HOURS * 60 * 60, refresh_token=new_refresh_token)
            
    def delete_refresh_token(self, refresh_token: str) -> None:
        """
        :params refresh_token str:
        """
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM refresh_tokens WHERE refresh_token = %s;", (refresh_token,))
            if cursor.rowcount < 1:
                raise UnauthorizedError

            conn.commit()
        
    def register_guest(self) -> Token:
        """
        :returns Token: A new access token, its expiry in seconds, and a new refresh token
        """
        user_id = self._add_user_to_database()
        
        return self._generate_token_pair(user_id, is_guest=True)
        
    def sign_in_user(self, email: Optional[str], username: Optional[str], password: str) -> Token:
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

    def get_user_id_from_token(self, token: str) -> str:
        payload = self._get_payload_from_access_token(token)
        
        user_id = payload.get('sub')
        
        if not isinstance(user_id, str):
            raise UnauthorizedError
        
        return user_id
    
    def get_authorization_status_from_token(self, token: str) -> bool:
        payload = self._get_payload_from_access_token(token)
        
        is_guest = payload.get('is_guest')
        
        if not isinstance(is_guest, bool):
            raise UnauthorizedError
        
        return is_guest
        
    def _generate_token_pair(self, user_id: str, is_guest: bool) -> Token:
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, refresh_token, refresh_token_expiry from refresh_tokens WHERE user_id = %s ORDER BY refresh_token_expiry ASC", (user_id, ))
            result = cursor.fetchall()
            
            if len(result) >= 5:
                refresh_token_list = result[0]
                
                _, refresh_token, _ = refresh_token_list
                
                if not isinstance(refresh_token, str):
                    raise ValueError("expected refresh_token to be a str")
                
                cursor.execute("DELETE FROM refresh_tokens WHERE refresh_token = %s", (refresh_token, ))
        
            refresh_token = self._generate_refresh_token()
            refreshTokenExpiry = (datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
        
            if not is_guest:
                cursor.execute("INSERT INTO refresh_tokens(user_id, refresh_token, refresh_token_expiry) VALUES (%s, %s, %s);", (user_id, refresh_token, refreshTokenExpiry))
            else:
                cursor.execute("INSERT INTO refresh_tokens(user_id, refresh_token) VALUES(%s, %s);", (user_id, refresh_token))
                
            conn.commit()

        access_token = self._generate_access_token(user_id, is_guest=is_guest)

        return Token(access_token=access_token, expires_in=ACCESS_TOKEN_EXPIRY_HOURS * 60 * 60, refresh_token=refresh_token)
        
    def _add_user_to_database(self, is_guest: bool = True, email: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, profilePicture: Optional[str] = None) -> str:
        user_id = str(uuid.uuid4())

        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users(user_id, is_guest, email, username, password, profile_picture) VALUES (%s, %s, %s, %s, %s, %s);", (user_id, is_guest, email, username, password, profilePicture))
            conn.commit()
            
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
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError):
            raise UnauthorizedError

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
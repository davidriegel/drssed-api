__all__ = ["authentication_manager"]

import secrets
import uuid
import jwt
from os import getenv
from urllib.parse import urljoin
from typing import Optional
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.email import send_verification_email
from app.core.database import get_session
from app.models.token import Token, AccessToken
from app.persistence.queries import user as user_queries
from app.persistence.queries import refresh_token as refresh_token_queries
from app.persistence.queries import email_verification as email_verification_queries
from app.persistence.schemas import user as user_schemas
from app.persistence.schemas import refresh_token as refresh_token_schemas
from app.persistence.schemas import email_verification as email_verification_schemas
from app.utils.exceptions import UnauthorizedError, NotFoundError, ConflictError
from app.utils.helpers import ensure_utc
from app.core.logging import get_logger

SECRET_TOKEN_KEY = getenv("SECRET_TOKEN_KEY")

if not SECRET_TOKEN_KEY or len(SECRET_TOKEN_KEY) < 32:
    raise RuntimeError("⚠️ SECRET_TOKEN_KEY must be set and at least 32 characters long")

ACCESS_TOKEN_EXPIRY_HOURS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 90
REFRESH_TOKEN_LENGTH = 16

EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = 24

logger = get_logger()

class AuthenticationManager:
    def create_email_verification(self, user_id: str, preferred_language: str) -> None:
        is_verified = user_queries.get_email_verification_status(user_id)
        
        if is_verified and is_verified.email_verified_at:
            raise ConflictError
        
        if not is_verified or not is_verified.email:
            raise NotFoundError
        
        new_verification_token = email_verification_schemas.EmailVerificationToken(token=secrets.token_urlsafe(24), email=is_verified.email, user_id=user_id, expires_at=datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS), used_at=None)
        
        with get_session() as session:
            email_verification_queries.expire_for_user(session, user_id)
            email_verification_queries.create(session, new_verification_token)
        
        public_url = str(urljoin(getenv("API_BASE_URL", ""), f"/auth/email/verify?token={new_verification_token.token}"))
        
        send_verification_email(is_verified.email, preferred_language, public_url, EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS)
    
    def verify_email(self, token: str) -> str:
        email_verification_token = email_verification_queries.get_by_token(token)
        
        if not email_verification_token:
            raise NotFoundError
        
        if email_verification_token.used_at:
            if ensure_utc(email_verification_token.used_at) < datetime.now(timezone.utc):
                return email_verification_token.email
            
        with get_session() as session:
            email_verification_queries.mark_as_used(session, token)
            user_queries.mark_email_as_verified(session, email_verification_token.user_id)
            
        return email_verification_token.email
            
    
    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        :params refresh_token str:
        :returns Token: A new access token, its expiry in seconds, and a new refresh token
        """
        refresh_token_model = refresh_token_queries.get_by_token(refresh_token)
        
        if not refresh_token_model:
            raise UnauthorizedError
        
        if refresh_token_model.refresh_token_expiry and ensure_utc(refresh_token_model.refresh_token_expiry) < datetime.now(timezone.utc):
            raise UnauthorizedError
        
        user_id = refresh_token_model.user_id
        
        user_guest_status = user_queries.get_guest_status(user_id)
        is_guest = user_guest_status.is_guest if user_guest_status else False
        access_token = self._generate_access_token(refresh_token_model.user_id, is_guest=is_guest)
        new_refresh_token = self._generate_refresh_token(user_id=user_id, with_expiry=not is_guest)
        
        refresh_token_queries.update(refresh_token, new_refresh_token)
        user_queries.update_last_active_at(user_id)
        
        return Token(access_token=access_token.access_token, expires_in=access_token.expires_in, refresh_token=new_refresh_token.refresh_token)
    
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
        
    def sign_in_user(self, email: Optional[str], username: Optional[str], password: str) -> Token:
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

    def get_user_id_from_token(self, token: str) -> str:
        payload = self._get_payload_from_access_token(token)
        
        user_id = payload.get('sub')
        
        if not isinstance(user_id, str):
            raise UnauthorizedError
        
        return user_id
    
    def get_is_guest_from_token(self, token: str) -> bool:
        payload = self._get_payload_from_access_token(token)
        
        is_guest = payload.get('is_guest')
        
        if not isinstance(is_guest, bool):
            raise UnauthorizedError
        
        return is_guest
        
    def _generate_token_pair(self, user_id: str, is_guest: bool) -> Token:
        refresh_tokens = refresh_token_queries.get_by_user_id(user_id)
        
        if refresh_tokens and len(refresh_tokens) >= 5:
            oldest_token = refresh_tokens[0]
            
            refresh_token_queries.delete_by_token(oldest_token.refresh_token)
            
        refresh_token = self._generate_refresh_token(user_id=user_id, with_expiry=not is_guest)
        
        refresh_token_queries.create(refresh_token)

        access_token = self._generate_access_token(user_id, is_guest=is_guest)

        token = Token(access_token=access_token.access_token, expires_in=access_token.expires_in, refresh_token=refresh_token.refresh_token)
        
        return token
        
    def _add_user_to_database(self, is_guest: bool = True, email: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, profilePicture: Optional[str] = None, preferred_language: str = "en") -> str:
        user_id = str(uuid.uuid4())
        
        user = user_schemas.UserCreate(user_id=user_id, is_guest=is_guest, email=email, username=username, password_hash=password, profile_picture=profilePicture, preferred_language=preferred_language)
        
        user_queries.create(user)
            
        return user_id
        
    def _get_payload_from_access_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, SECRET_TOKEN_KEY, algorithms=['HS256'])
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError):
            raise UnauthorizedError

    def _generate_refresh_token(self, user_id: str, with_expiry: bool = True) -> refresh_token_schemas.RefreshToken:
        refresh_token = "".join(secrets.token_urlsafe(REFRESH_TOKEN_LENGTH))
        refresh_token_expiry = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)

        return refresh_token_schemas.RefreshToken(
            refresh_token=refresh_token,
            user_id=user_id,
            refresh_token_expiry=refresh_token_expiry if with_expiry else None
        )

    def _generate_access_token(self, user_id: str, is_guest: bool) -> AccessToken:
        payload = {
            'sub': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRY_HOURS),
            'is_guest': is_guest
        }
        access_token = jwt.encode(payload, SECRET_TOKEN_KEY, algorithm='HS256')
        return AccessToken(access_token=access_token, expires_in=ACCESS_TOKEN_EXPIRY_HOURS * 60 * 60)

authentication_manager = AuthenticationManager()
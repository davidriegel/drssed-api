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
        
    def update_user_username(self, user_id: str, username: Optional[str]) -> None:
        if not isinstance(username, str):
            raise UsernameMissingError("Username is required.")
        
        username = username.lower().strip()
        
        if len(username) < 3:
            raise UsernameTooShortError("The provided username is too short.")
        
        if len(username) > 32:
            raise ValidationError("The provided username is too long.")
            
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET username = %s WHERE user_id = %s;", (username, user_id,))
                conn.commit()
        except IntegrityError as e:
            if e.msg and "username" in e.msg:
                raise UsernameAlreadyInUseError("The provided username is already in use.")
            raise Exception(e.msg)
        except Exception as e:
            logger.error(f"An unexpected error occurred while setting a new username: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    """
                
    def getUserProfilePicture(self, userID: str) -> str:
        if not path.exists(f"static/profile_pictures/{userID}.webp"):
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT profile_picture FROM users WHERE user_id = %s;", (userID, ))
                profilePicture = cursor.fetchone()
                
                if not profilePicture:
                    raise UserNotFoundError("The provided user_id is not associated with any users.")
                
                return profilePicture[0]
        
        return f"/public/profile_pictures/{userID}.webp"
    
    def setProfilePicture(self, file: FileStorage, token: str) -> User:
        fileExtension = file.filename.split(".")[-1].lower()
        
        if fileExtension not in ["jpg", "jpeg", "png"]:
            raise UnsupportedFileTypeError("The provided file type is not supported.")
        
        userID = authentication_manager.retrieveUserIDByToken(token)
        
        try:
            image = Image.open(file.stream)
            image.thumbnail((300, 300))
            image.save(f"app/static/profile_pictures/{userID}.webp", optimize=True, quality=95, format="webp")
            
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET profile_picture = %s WHERE user_id = %s;", (f"/public/profile_pictures/{userID}.webp", userID))
                conn.commit()
        except Exception as e:
            logger.error(f"An unexpected error occurred while setting the profile picture: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        return self.getMyUser(token)
    
    def setDefaultProfilePicture(self, profilePicture: str, token: str) -> User:
        userID = authentication_manager.retrieveUserIDByToken(token)
        
        if profilePicture not in os.listdir("app/static/profile_pictures/default/"):
            raise UserProfilePictureNotFoundError("The provided profile picture is available. Please choose one of the following: " + ", ".join(os.listdir("app/static/profile_pictures/default/")))
        
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET profile_picture = %s WHERE user_id = %s;", ("/public/profile_pictures/default/" + profilePicture, userID))
            conn.commit()
        
        return self.getMyUser(token)
    
    def removeProfilePicture(self, token: str) -> None:
        try:
            userID = authentication_manager.retrieveUserIDByToken(token)
            
            if not path.exists(f"app/static/profile_pictures/{userID}.webp"):
                raise UserProfilePictureNotFoundError("The user profile picture is not set.")
        
            remove(f"app/static/profile_pictures/{userID}.webp")
            
            profilePictures = os.listdir("app/static/profile_pictures/default/")
            profilePicture = f"/public/profile_pictures/default/{random.choice(profilePictures)}"
            
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET profile_picture = %s WHERE user_id = %s;", (profilePicture, userID, ))
                conn.commit()
        except UserProfilePictureNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while removing the profile picture: {e}")
            logger.error(traceback.format_exc())
            raise e
    
    def getMyProfilePicture(self, token: str) -> str:
        userID = authentication_manager.retrieveUserIDByToken(token)
        
        if not path.exists(f"app/static/profile_pictures/{userID}.webp"):
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT profile_picture FROM users WHERE user_id = %s;", (userID, ))
                profilePicture = cursor.fetchone()[0]
                
                return profilePicture
        
        return f"/public/profile_pictures/{userID}.webp"
    
    """

user_manager = UserManager()
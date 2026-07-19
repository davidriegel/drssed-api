
# ! Internal:

class DatabaseError(Exception):
    def __init__(self, message="Database error occurred"):
        self.message = message
        super().__init__(self.message)
        
class InvalidTokenError(Exception):
    def __init__(self, message="Invalid token"):
        self.message = message
        super().__init__(self.message)


# External:

class PermissionError(Exception):
    def __init__(self, message="Permission denied"):
        self.message = message
        super().__init__(self.message)

class EmailAlreadyInUseError(Exception):
    def __init__(self, message="Email already in use"):
        self.message = message
        super().__init__(self.message)
        
class EmailInvalidError(Exception):
    def __init__(self, message="Email is invalid"):
        self.message = message
        super().__init__(self.message)
        
class UsernameAlreadySetError(Exception):
    def __init__(self, message="Username already set"):
        self.message = message
        super().__init__(self.message)
        
class UsernameAlreadyInUseError(Exception):
    def __init__(self, message="Username already in use"):
        self.message = message
        super().__init__(self.message)
        
class UsernameTooShortError(Exception):
    def __init__(self, message="Username has to be at least 3 characters long"):
        self.message = message
        super().__init__(self.message)
        
class UsernameTooLongError(Exception):
    def __init__(self, message="Username has to be at most 32 characters long"):
        self.message = message
        super().__init__(self.message)

class PasswordTooShortError(Exception):
    def __init__(self, message="Password has twaso be at least 8 characters long"):
        self.message = message
        super().__init__(self.message)

class WrongSignInCredentialsError(Exception):
    def __init__(self, message="Wrong email/username or password"):
        self.message = message
        super().__init__(self.message)
        
class UserNotFoundError(Exception):
    def __init__(self, message="User not found"):
        self.message = message
        super().__init__(self.message)
        
class UserProfilePictureNotFoundError(Exception):
    def __init__(self, message="User profile picture not set"):
        self.message = message
        super().__init__(self.message)
        
class ClothingNotFoundError(Exception):
    def __init__(self, message="Clothing not found"):
        self.message = message
        super().__init__(self.message)

class OutfitNameTooShortError(Exception):
    def __init__(self, message="Outfit name has to be at least 3 characters long"):
        self.message = message
        super().__init__(self.message)

class OutfitNameTooLongError(Exception):
    def __init__(self, message="Outfit name has to be at most 50 characters long"):
        self.message = message
        super().__init__(self.message)

class OutfitNotFoundError(Exception):
    def __init__(self, message="Outfit not found"):
        self.message = message
        super().__init__(self.message)
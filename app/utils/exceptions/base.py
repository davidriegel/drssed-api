class ValidationError(Exception):
    def __init__(self, message="Validation error occurred"):
        super().__init__(message)
        
class NotFoundError(Exception):
    def __init__(self, message="Resource not found"):
        super().__init__(message)

class ConflictError(Exception):
    def __init__(self, message="Conflict occurred"):
        super().__init__(message)
        
class PermissionError(Exception):
    def __init__(self, message="You do not have permission to access this resource"):
        super().__init__(message)

# Clothing

class ClothingValidationError(ValidationError):
    def __init__(self, message="Clothing validation error occurred"):
        super().__init__(message)

class ClothingNotFoundError(NotFoundError):
    def __init__(self, message="Clothing not found"):
        super().__init__(message)

class ClothingConflictError(ConflictError):
    def __init__(self, message="Clothing conflict error occurred"):
        super().__init__(message)
        
# Outfit

class OutfitValidationError(ValidationError):
    def __init__(self, message="Outfit validation error occurred"):
        super().__init__(message)
        
class OutfitNotFoundError(NotFoundError):
    def __init__(self, message="The requested outfit does not exist"):
        super().__init__(message)

class OutfitPermissionError(PermissionError):
    def __init__(self, message="You do not have permission to access this outfit"):
        super().__init__(message)
        
# Authentication

class AuthValidationError(ValidationError):
    def __init__(self, message="Authentication validation error occurred"):
        super().__init__(message)
        
# User

class UserValidationError(ValidationError):
    def __init__(self, message="User validation error occurred"):
        super().__init__(message)

class UserNotFoundError(NotFoundError):
    def __init__(self, message="User not found"):
        super().__init__(message)

class UserConflictError(ConflictError):
    def __init__(self, message="User conflict error occurred"):
        super().__init__(message)

class UserPermissionError(PermissionError):
    def __init__(self, message="You do not have permission to access this user"):
        super().__init__(message)
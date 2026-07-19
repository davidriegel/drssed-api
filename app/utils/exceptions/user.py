from app.utils.exceptions.base import UserConflictError, UserValidationError


class SignInNameMissingError(UserValidationError):
    def __init__(self, message="Either an email or username is required."):
        super().__init__(message)


class EmailMissingError(UserValidationError):
    def __init__(self, message="Email is missing or invalid."):
        super().__init__(message)


class UsernameMissingError(UserValidationError):
    def __init__(self, message="Username is missing or invalid."):
        super().__init__(message)


class UserIDMissingError(UserValidationError):
    def __init__(self, message="User ID is missing from the request."):
        super().__init__(message)


class PasswordMissingError(UserValidationError):
    def __init__(self, message="Password is missing or invalid."):
        super().__init__(message)


class EmailInvalidError(UserValidationError):
    def __init__(self, message="Email is invalid."):
        super().__init__(message)


class ProfilePictureInvalidError(UserValidationError):
    def __init__(self, message="Profile picture is invalid."):
        super().__init__(message)


class UsernameTooShortError(UserValidationError):
    def __init__(self, message="Username is too short."):
        super().__init__(message)


class PasswordTooShortError(UserValidationError):
    def __init__(self, message="Password is too short."):
        super().__init__(message)


class UsernameTooLongError(UserValidationError):
    def __init__(self, message="Username is too long."):
        super().__init__(message)


class EmailAlreadyInUseError(UserConflictError):
    def __init__(self, message="The provided email is already in use."):
        super().__init__(message)


class UsernameAlreadyInUseError(UserConflictError):
    def __init__(self, message="The provided username is already in use."):
        super().__init__(message)

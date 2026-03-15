from app.utils.exceptions.base import AuthValidationError

class AuthTokenExpiredError(AuthValidationError):
    def __init__(self, message="Authentication token has expired. Please log in again."):
        super().__init__(message)
        
class AuthAccessTokenInvalidError(AuthValidationError):
    def __init__(self, message="Access token is invalid. Please refresh the token."):
        super().__init__(message)

class AuthRefreshTokenInvalidError(AuthValidationError):
    def __init__(self, message="Refresh token is invalid. Please log in again."):
        super().__init__(message)
        
class AuthAccessTokenMissingError(AuthValidationError):
    def __init__(self, message="Access token is missing from the request."):
        super().__init__(message)
        
class AuthRefreshTokenMissingError(AuthValidationError):
    def __init__(self, message="Refresh token is missing from the request."):
        super().__init__(message)
        
class AuthCredentialsWrongError(AuthValidationError):
    def __init__(self, message="The credentials to sign in are wrong."):
        super().__init__(message)
        
class AuthCredentialsMissingError(AuthValidationError):
    def __init__(self, message="The credentials to sign in are missing."):
        super().__init__(message)
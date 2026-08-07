class DomainError(Exception):
    """Base for errors that describe a rejected request rather than a failure."""


class ValidationError(DomainError):
    def __init__(self, message="Validation failed"):
        super().__init__(message)


class NotFoundError(DomainError):
    def __init__(self, message="Resource not found"):
        super().__init__(message)


class ConflictError(DomainError):
    def __init__(self, message="Resource already exists", field=None):
        super().__init__(message)
        self.field = field


class PermissionError(DomainError):
    def __init__(self, message="Permission denied"):
        super().__init__(message)


class UnauthorizedError(DomainError):
    def __init__(self, message="Invalid credentials"):
        super().__init__(message)


class UnprocessableEntityError(DomainError):
    def __init__(self, message="Unprocessable request") -> None:
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

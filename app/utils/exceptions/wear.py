from app.utils.exceptions.base import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


class WearValidationError(ValidationError):
    def __init__(self, message="Wear validation error occurred"):
        super().__init__(message)


class WearNotFoundError(NotFoundError):
    def __init__(self, message="The requested wear entry does not exist"):
        super().__init__(message)


class WearAlreadyLoggedError(ConflictError):
    def __init__(self, message="This outfit is already logged for that day"):
        super().__init__(message, field="worn_on")


class WearIDMissingError(WearValidationError):
    def __init__(self, message="Wear ID is missing"):
        super().__init__(message)


class WearWornOnInvalidError(WearValidationError):
    def __init__(self, message="Wear timestamp is invalid"):
        super().__init__(message)


class WearWornOnInFutureError(WearValidationError):
    def __init__(self, message="Wear timestamp cannot be in the future"):
        super().__init__(message)


class WearTemperatureInvalidError(WearValidationError):
    def __init__(self, message="Wear temperature is invalid"):
        super().__init__(message)


class WearWeatherInvalidError(WearValidationError):
    def __init__(self, message="Wear weather condition is invalid"):
        super().__init__(message)


class WearOccasionInvalidError(WearValidationError):
    def __init__(self, message="Wear occasion is invalid"):
        super().__init__(message)


class WearRatingInvalidError(WearValidationError):
    def __init__(self, message="Wear rating must be between 1 and 5"):
        super().__init__(message)


class WearNoteTooLongError(WearValidationError):
    def __init__(self, message="Wear note is too long"):
        super().__init__(message)


class WearLimitInvalidError(WearValidationError):
    def __init__(self, message="Wear limit is invalid"):
        super().__init__(message)


class WearOffsetInvalidError(WearValidationError):
    def __init__(self, message="Wear offset is invalid"):
        super().__init__(message)


class WearRangeInvalidError(WearValidationError):
    def __init__(self, message="Wear date range is invalid"):
        super().__init__(message)

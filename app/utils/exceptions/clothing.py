from app.utils.exceptions.base import ClothingConflictError, ClothingValidationError


class ClothingIDMissingError(ClothingValidationError):
    def __init__(self, message="Clothing ID is missing"):
        super().__init__(message)


class ClothingNameMissingError(ClothingValidationError):
    def __init__(self, message="Clothing name is missing"):
        super().__init__(message)


class ClothingSubCategoryMissingError(ClothingValidationError):
    def __init__(self, message="Clothing category is missing"):
        super().__init__(message)


class ClothingImageMissingError(ClothingValidationError):
    def __init__(self, message="Clothing image is missing"):
        super().__init__(message)


class ClothingColorMissingError(ClothingValidationError):
    def __init__(self, message="Clothing color is missing"):
        super().__init__(message)


class ClothingNameTooShortError(ClothingValidationError):
    def __init__(self, message="Clothing name has to be at least 3 characters long"):
        super().__init__(message)


class ClothingNameTooLongError(ClothingValidationError):
    def __init__(self, message="Clothing name has to be at most 50 characters long"):
        super().__init__(message)


class ClothingImageInvalidError(ClothingConflictError):
    def __init__(self, message="Clothing image is invalid"):
        super().__init__(message)


class SeasonsInvalidError(ClothingValidationError):
    def __init__(self, message="Clothing seasons are invalid"):
        super().__init__(message)


class ClothingTagsInvalidError(ClothingValidationError):
    def __init__(self, message="Clothing tags are invalid"):
        super().__init__(message)


class ClothingWarmthLevelInvalidError(ClothingValidationError):
    def __init__(
        self,
        message="Clothing warmth level is invalid, it has to be an integer between 1 and 5",
    ):
        super().__init__(message)

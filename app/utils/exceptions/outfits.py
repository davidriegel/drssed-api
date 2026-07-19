from app.utils.exceptions.base import OutfitValidationError


class OutfitIDMissingError(OutfitValidationError):
    def __init__(self, message="Outfit ID is missing"):
        super().__init__(message)


class OutfitClothingIDsMissingError(OutfitValidationError):
    def __init__(self, message="Outfit clothing ID(s) are missing"):
        super().__init__(message)


class OutfitNameMissingError(OutfitValidationError):
    def __init__(self, message="Outfit name is missing"):
        super().__init__(message)


class OutfitClothingIDInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit clothing ID is invalid"):
        super().__init__(message)


class OutfitSeasonsInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit seasons are invalid"):
        super().__init__(message)


class OutfitTagsInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit tags are invalid"):
        super().__init__(message)


class OutfitLimitInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit limit is invalid."):
        super().__init__(message)


class OutfitOffsetInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit offset is invalid."):
        super().__init__(message)


class OutfitNameTooShortError(OutfitValidationError):
    def __init__(self, message="Outfit name is too short."):
        super().__init__(message)


class OutfitNameTooLongError(OutfitValidationError):
    def __init__(self, message="Outfit name is too long."):
        super().__init__(message)


class OutfitPublicMissingError(OutfitValidationError):
    def __init__(self, message="Outfit is public is missing."):
        super().__init__(message)


class OutfitFavoriteMissingError(OutfitValidationError):
    def __init__(self, message="Outfit is favorite is missing."):
        super().__init__(message)


class OutfitSceneMissingError(OutfitValidationError):
    def __init__(self, message="Outfit scene is missing."):
        super().__init__(message)


class OutfitSceneInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit scene is invalid."):
        super().__init__(message)


class OutfitPreviewInvalidError(OutfitValidationError):
    def __init__(self, message="Outfit preview is invalid."):
        super().__init__(message)

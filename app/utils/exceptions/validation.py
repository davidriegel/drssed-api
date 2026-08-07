from app.utils.exceptions.base import ValidationError


class ImageUnclearError(ValidationError):
    def __init__(self, message="Image is unclear"):
        super().__init__(message)

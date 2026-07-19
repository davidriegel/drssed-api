from app.utils.exceptions.base import ValidationError


class UnsupportedFileTypeError(ValidationError):
    def __init__(self, message="Unsupported file type [Supported: .png, .jpg, .jpeg]"):
        super().__init__(message)


class FileTooLargeError(ValidationError):
    def __init__(self, message="File is too large (max 2MB)"):
        super().__init__(message)


class ImageUnclearError(ValidationError):
    def __init__(self, message="Image is unclear"):
        super().__init__(message)

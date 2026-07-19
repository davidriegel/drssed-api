from pydantic import BaseModel, ConfigDict

from app.persistence.schemas.types import UtcDatetime


class RefreshToken(BaseModel):
    """
    Used for refresh token operations: creation, validation, and cleanup.
    """

    model_config = ConfigDict(frozen=True)

    refresh_token: str
    user_id: str
    refresh_token_expiry: UtcDatetime | None

from pydantic import BaseModel, ConfigDict

from app.persistence.schemas.types import UtcDatetime


class PasswordResetToken(BaseModel):
    """
    Used for validating password reset tokens.
    """

    model_config = ConfigDict(frozen=True)

    token: str
    user_id: str
    expires_at: UtcDatetime
    used_at: UtcDatetime | None

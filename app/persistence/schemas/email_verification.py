from pydantic import BaseModel, ConfigDict

from app.persistence.schemas.types import UtcDatetime


class EmailVerificationToken(BaseModel):
    """
    Used for validating email verification tokens.
    """

    model_config = ConfigDict(frozen=True)

    token: str
    email: str
    user_id: str
    expires_at: UtcDatetime
    used_at: UtcDatetime | None

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class EmailVerificationToken(BaseModel):
    """
    Used for validating email verification tokens.
    """
    model_config = ConfigDict(frozen=True)
    
    token: str
    email: str
    user_id: str
    expires_at: datetime
    used_at: datetime | None
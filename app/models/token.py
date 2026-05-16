from pydantic import BaseModel, ConfigDict

class Token(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    access_token: str
    expires_in: int
    refresh_token: str
    token_type: str = "Bearer"
    
class AccessToken(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    access_token: str
    expires_in: int
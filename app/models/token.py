from dataclasses import dataclass, asdict

@dataclass
class Token:
    access_token: str
    expires_in: int
    refresh_token: str
    
    def to_dict(self) -> dict:
        return asdict(self)
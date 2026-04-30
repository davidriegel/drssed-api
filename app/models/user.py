from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone

@dataclass
class User:
    user_id: str
    is_guest: bool
    created_at: datetime
    updated_at: datetime
    username: Optional[str] = None
    email: Optional[str] = None
    profile_picture: Optional[str] = None
    
    def to_dict(self, exclude_none=True) -> dict:
        d = {
            "user_id": self.user_id,
            "is_guest": bool(self.is_guest),
            "username": self.username,
            "email": self.email,
            "profile_picture": self.profile_picture,
            "created_at": self.created_at.replace(tzinfo=timezone.utc).isoformat(timespec="seconds") if self.created_at else None,
            "updated_at": self.updated_at.replace(tzinfo=timezone.utc).isoformat(timespec="seconds") if self.updated_at else None,
        }
        
        if exclude_none:
            d = {k: v for k, v in d.items() if v is not None}
        
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(
            user_id=data['user_id'],
            is_guest=bool(data['is_guest']),
            username=data.get('username'),
            email=data.get('email'),
            profile_picture=data.get('profile_picture'),
            created_at=data['created_at'],
            updated_at=data['updated_at']
        )
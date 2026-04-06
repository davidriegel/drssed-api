from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

class OutfitTags(str, Enum):
    CASUAL = "Casual"
    FORMAL = "Formal"
    SPORTS = "Sports"
    VINTAGE = "Vintage"
    OUTDOOR = "Outdoor"
    PARTY = "Party"
    WORK = "Work"
    BEACH = "Beach"

class OutfitSeason(str, Enum):
    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter"

@dataclass
class CanvasPlacement:
    clothing_id: str
    x: float
    y: float
    z: int
    scale: float
    rotation: float

@dataclass
class Outfit:
    outfit_id: str
    is_public: bool
    is_favorite: bool
    name: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    scene: Optional[list[CanvasPlacement]] = None
    seasons: Optional[list[OutfitSeason]] = None
    tags: Optional[list[OutfitTags]] = None
    description: Optional[str] = None
        
    def to_dict(self) -> dict:
        data = asdict(self)
        
        if isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
            
        if isinstance(data["updated_at"], datetime):
            data["updated_at"] = data["updated_at"].replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        return data
    
    @classmethod
    def from_dict(cls, core: dict, scene: Optional[list[CanvasPlacement]], seasons: Optional[list[OutfitSeason]], tags: Optional[list[OutfitTags]]):
        return Outfit(
            outfit_id=core.get("outfit_id"),
            is_public=bool(core.get("is_public")),
            is_favorite=bool(core.get("is_favorite")),
            name=core.get("name"),
            created_at=core.get("created_at"),
            updated_at=core.get("updated_at"),
            user_id=core.get("user_id"),
            scene=scene,
            seasons=seasons,
            tags=tags,
            description=core.get("description")
        )
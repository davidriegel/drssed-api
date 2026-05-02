from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, asdict

class ClothingTags(str, Enum):
    CASUAL = "Casual"
    FORMAL = "Formal"
    SPORTS = "Sports"
    VINTAGE = "Vintage"
    
class ClothingSeason(str, Enum):
    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter"
    
class ClothingCategory(str, Enum):
    JACKET = "JACKET"
    TOP = "TOP"
    BOTTOM = "BOTTOM" 
    ONE_PIECE = "ONE_PIECE"
    
class ClothingSubCategory(str, Enum):
    # TOP
    T_SHIRT = "t-shirt"
    SHIRT = "shirt"
    POLO_SHIRT = "polo shirt"
    SWEATER = "sweater"
    HOODIE = "hoodie"
    # BOTTOM
    JEANS = "jeans"
    TROUSERS = "trousers"
    SHORTS = "shorts"
    SKIRT = "skirt"
    # JACKET
    JACKET = "jacket"
    DENIM_JACKET = "denim jacket"
    SPORTS_JACKET = "sports jacket"
    COAT = "coat"
    BLAZER = "blazer"
    # ONE_PIECE
    DRESS = "dress"

@dataclass
class Clothing:
    clothing_id: str
    is_public: bool
    name: str
    category: ClothingCategory
    sub_category: ClothingSubCategory
    color: str
    created_at: datetime
    user_id: str
    image_id: str
    seasons: list[ClothingSeason]
    tags: list[ClothingTags]
    description: Optional[str] = None

    def to_dict(self) -> dict:
        data = asdict(self)
        if isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        return data

    @classmethod
    def from_dict(cls, core: dict, seasons: list[ClothingSeason], tags: list[ClothingTags]):
        return Clothing(
            clothing_id=core.get("clothing_id"),
            is_public=bool(core.get("is_public")),
            name=core.get("name"),
            color=core.get("color"),
            category=ClothingCategory[core.get("category")],
            sub_category=ClothingSubCategory[core.get("sub_category")],
            created_at=core.get("created_at"),
            user_id=core.get("user_id"),
            image_id=core.get("image_id"),
            seasons=seasons,
            tags=tags,
            description=core.get("description")
        )

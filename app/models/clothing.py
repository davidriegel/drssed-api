from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum

from app.models.season import Season


class ClothingTags(str, Enum):
    CASUAL = "CASUAL"
    FORMAL = "FORMAL"
    SPORTS = "SPORTS"
    VINTAGE = "VINTAGE"


class ClothingCategory(str, Enum):
    JACKET = "JACKET"
    TOP = "TOP"
    BOTTOM = "BOTTOM"
    ONE_PIECE = "ONE_PIECE"


class ClothingSubCategory(str, Enum):
    # TOP
    T_SHIRT = "T_SHIRT"
    LONGSLEEVE = "LONGSLEEVE"
    TANK_TOP = "TANK_TOP"
    SHIRT = "SHIRT"
    POLO_SHIRT = "POLO_SHIRT"
    SWEATER = "SWEATER"
    HOODIE = "HOODIE"
    SWEATSHIRT = "SWEATSHIRT"
    CARDIGAN = "CARDIGAN"
    VEST = "VEST"
    TURTLENECK = "TURTLENECK"

    # BOTTOM
    JEANS = "JEANS"
    TROUSERS = "TROUSERS"
    CHINOS = "CHINOS"
    CARGO_PANTS = "CARGO_PANTS"
    SWEATPANTS = "SWEATPANTS"
    LEGGINGS = "LEGGINGS"
    SHORTS = "SHORTS"
    SKIRT = "SKIRT"

    # JACKET
    DENIM_JACKET = "DENIM_JACKET"
    SPORTS_JACKET = "SPORTS_JACKET"
    LEATHER_JACKET = "LEATHER_JACKET"
    BOMBER_JACKET = "BOMBER_JACKET"
    PUFFER_JACKET = "PUFFER_JACKET"
    WINDBREAKER = "WINDBREAKER"
    RAIN_JACKET = "RAIN_JACKET"
    PARKA = "PARKA"
    COAT = "COAT"
    TRENCH_COAT = "TRENCH_COAT"
    BLAZER = "BLAZER"

    # ONE_PIECE
    DRESS = "DRESS"
    JUMPSUIT = "JUMPSUIT"
    OVERALL = "OVERALL"
    SUIT = "SUIT"

    @property
    def category(self) -> "ClothingCategory":
        return _SUBCATEGORY_PARENTS[self]


_SUBCATEGORY_PARENTS: dict[ClothingSubCategory, ClothingCategory] = {
    # TOP
    ClothingSubCategory.T_SHIRT: ClothingCategory.TOP,
    ClothingSubCategory.LONGSLEEVE: ClothingCategory.TOP,
    ClothingSubCategory.TANK_TOP: ClothingCategory.TOP,
    ClothingSubCategory.SHIRT: ClothingCategory.TOP,
    ClothingSubCategory.POLO_SHIRT: ClothingCategory.TOP,
    ClothingSubCategory.SWEATER: ClothingCategory.TOP,
    ClothingSubCategory.HOODIE: ClothingCategory.TOP,
    ClothingSubCategory.SWEATSHIRT: ClothingCategory.TOP,
    ClothingSubCategory.CARDIGAN: ClothingCategory.TOP,
    ClothingSubCategory.VEST: ClothingCategory.TOP,
    ClothingSubCategory.TURTLENECK: ClothingCategory.TOP,
    # BOTTOM
    ClothingSubCategory.JEANS: ClothingCategory.BOTTOM,
    ClothingSubCategory.TROUSERS: ClothingCategory.BOTTOM,
    ClothingSubCategory.CHINOS: ClothingCategory.BOTTOM,
    ClothingSubCategory.CARGO_PANTS: ClothingCategory.BOTTOM,
    ClothingSubCategory.SWEATPANTS: ClothingCategory.BOTTOM,
    ClothingSubCategory.LEGGINGS: ClothingCategory.BOTTOM,
    ClothingSubCategory.SHORTS: ClothingCategory.BOTTOM,
    ClothingSubCategory.SKIRT: ClothingCategory.BOTTOM,
    # JACKET
    ClothingSubCategory.DENIM_JACKET: ClothingCategory.JACKET,
    ClothingSubCategory.SPORTS_JACKET: ClothingCategory.JACKET,
    ClothingSubCategory.LEATHER_JACKET: ClothingCategory.JACKET,
    ClothingSubCategory.BOMBER_JACKET: ClothingCategory.JACKET,
    ClothingSubCategory.PUFFER_JACKET: ClothingCategory.JACKET,
    ClothingSubCategory.WINDBREAKER: ClothingCategory.JACKET,
    ClothingSubCategory.RAIN_JACKET: ClothingCategory.JACKET,
    ClothingSubCategory.PARKA: ClothingCategory.JACKET,
    ClothingSubCategory.COAT: ClothingCategory.JACKET,
    ClothingSubCategory.TRENCH_COAT: ClothingCategory.JACKET,
    ClothingSubCategory.BLAZER: ClothingCategory.JACKET,
    # ONE_PIECE
    ClothingSubCategory.DRESS: ClothingCategory.ONE_PIECE,
    ClothingSubCategory.JUMPSUIT: ClothingCategory.ONE_PIECE,
    ClothingSubCategory.OVERALL: ClothingCategory.ONE_PIECE,
    ClothingSubCategory.SUIT: ClothingCategory.ONE_PIECE,
}


@dataclass
class Clothing:
    clothing_id: str
    is_public: bool
    name: str
    category: ClothingCategory
    sub_category: ClothingSubCategory
    color: str
    warmth_level: int
    created_at: datetime
    user_id: str
    image_id: str
    seasons: list[Season]
    tags: list[ClothingTags]

    def to_dict(self) -> dict:
        data = asdict(self)
        if isinstance(data["created_at"], datetime):
            data["created_at"] = (
                data["created_at"]
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="seconds")
            )
        return data

    @classmethod
    def from_dict(cls, core: dict, seasons: list[Season], tags: list[ClothingTags]):
        return Clothing(
            clothing_id=core["clothing_id"],
            is_public=bool(core["is_public"]),
            name=core["name"],
            color=core["color"],
            category=ClothingCategory(core["category"]),
            sub_category=ClothingSubCategory(core["sub_category"]),
            warmth_level=core["warmth_level"],
            created_at=core["created_at"],
            user_id=core["user_id"],
            image_id=core["image_id"],
            seasons=seasons,
            tags=tags,
        )


assert set(ClothingSubCategory) == set(_SUBCATEGORY_PARENTS), (
    f"Missing Parent-Mapping: {set(ClothingSubCategory) - set(_SUBCATEGORY_PARENTS)}"
)

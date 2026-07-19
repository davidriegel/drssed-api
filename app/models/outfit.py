from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum

from app.models.season import Season


class OutfitTags(str, Enum):
    CASUAL = "CASUAL"
    FORMAL = "FORMAL"
    SPORTS = "SPORTS"
    VINTAGE = "VINTAGE"


@dataclass
class CanvasPlacement:
    clothing_id: str
    x: float
    y: float
    z: int
    scale: float
    rotation: float


@dataclass
class OutfitSummary:
    outfit_id: str
    is_public: bool
    is_favorite: bool
    name: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    seasons: list[Season]
    tags: list[OutfitTags]

    def to_dict(self) -> dict:
        data = asdict(self)

        if isinstance(data["created_at"], datetime):
            data["created_at"] = (
                data["created_at"]
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="seconds")
            )

        if isinstance(data["updated_at"], datetime):
            data["updated_at"] = (
                data["updated_at"]
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="seconds")
            )
        return data

    @classmethod
    def from_dict(
        cls,
        core: dict,
        seasons: list[Season],
        tags: list[OutfitTags],
    ):
        return OutfitSummary(
            outfit_id=core["outfit_id"],
            is_public=bool(core["is_public"]),
            is_favorite=bool(core["is_favorite"]),
            name=core["name"],
            created_at=core["created_at"],
            updated_at=core["updated_at"],
            user_id=core["user_id"],
            seasons=seasons,
            tags=tags,
        )

@dataclass
class Outfit:
    outfit_id: str
    is_public: bool
    is_favorite: bool
    name: str
    created_at: datetime
    updated_at: datetime
    user_id: str
    scene: list[CanvasPlacement]
    seasons: list[Season]
    tags: list[OutfitTags]

    def to_dict(self) -> dict:
        data = asdict(self)

        if isinstance(data["created_at"], datetime):
            data["created_at"] = (
                data["created_at"]
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="seconds")
            )

        if isinstance(data["updated_at"], datetime):
            data["updated_at"] = (
                data["updated_at"]
                .replace(tzinfo=timezone.utc)
                .isoformat(timespec="seconds")
            )
        return data

    @classmethod
    def from_dict(
        cls,
        core: dict,
        scene: list[CanvasPlacement],
        seasons: list[Season],
        tags: list[OutfitTags],
    ):
        return Outfit(
            outfit_id=core["outfit_id"],
            is_public=bool(core["is_public"]),
            is_favorite=bool(core["is_favorite"]),
            name=core["name"],
            created_at=core["created_at"],
            updated_at=core["updated_at"],
            user_id=core["user_id"],
            scene=scene,
            seasons=seasons,
            tags=tags,
        )

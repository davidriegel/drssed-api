from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClothingRow(BaseModel):
    """All columns from the clothing table needed by the domain model."""

    model_config = ConfigDict(frozen=True)

    clothing_id: str
    is_public: bool
    name: str
    category: str
    sub_category: str
    color: str
    warmth_level: int
    created_at: datetime
    user_id: str
    image_id: str


class ClothingIdRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    clothing_id: str


class ClothingImageIdRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    image_id: str


class ClothingSeasonRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    season: str


class ClothingTagRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str


class ClothingIdSeasonRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    clothing_id: str
    season: str


class ClothingIdTagRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    clothing_id: str
    tag: str


class AffectedOutfitRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    outfit_id: str
    item_count: int

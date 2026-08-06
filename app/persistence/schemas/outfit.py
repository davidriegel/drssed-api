from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OutfitRow(BaseModel):
    """All columns from the outfits table needed by the domain model."""

    model_config = ConfigDict(frozen=True)

    outfit_id: str
    is_public: bool
    is_favorite: bool
    name: str
    created_at: datetime
    updated_at: datetime
    user_id: str


class OutfitIdRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    outfit_id: str


class OutfitSeasonRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    season: str


class OutfitTagRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    tag: str


class OutfitSeasonLinkRow(BaseModel):
    """A season row carrying the outfit it belongs to, used for batched fetches."""

    model_config = ConfigDict(frozen=True)

    outfit_id: str
    season: str


class OutfitTagLinkRow(BaseModel):
    """A tag row carrying the outfit it belongs to, used for batched fetches."""

    model_config = ConfigDict(frozen=True)

    outfit_id: str
    tag: str


class OutfitClothingRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    clothing_id: str
    position_x: Decimal
    position_y: Decimal
    z_index: int
    scale: Decimal
    rotation: Decimal


class OutfitClothingLinkRow(BaseModel):
    """A canvas placement carrying the outfit it belongs to, used for batched fetches."""

    model_config = ConfigDict(frozen=True)

    outfit_id: str
    clothing_id: str
    position_x: Decimal
    position_y: Decimal
    z_index: int
    scale: Decimal
    rotation: Decimal


class OutfitCountRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int

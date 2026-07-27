from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class WearRow(BaseModel):
    """All columns from the outfit_wears table needed by the domain model."""

    model_config = ConfigDict(frozen=True)

    wear_id: str
    user_id: str
    outfit_id: str
    worn_on: datetime
    feels_like: Optional[float] = None
    temperature: Optional[float] = None
    weather: Optional[str] = None
    occasion: Optional[str] = None
    rating: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WearWithOutfitRow(WearRow):
    """A wear row joined with the name of its outfit."""

    outfit_name: str


class WearIdRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    wear_id: str


class WearClothingRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    wear_id: str
    clothing_id: str


class WearCountRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int


class WearDateRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    worn_date: date


class WearOutfitCountRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    outfit_id: str
    name: str
    wear_count: int
    last_worn_on: Optional[datetime] = None


class WearClothingCountRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    clothing_id: str
    name: str
    category: str
    sub_category: str
    image_id: str
    wear_count: int
    last_worn_on: Optional[datetime] = None


class WearBucketRow(BaseModel):
    """A generic 'group by X' result — bucket label plus its count."""

    model_config = ConfigDict(frozen=True)

    bucket: Optional[str] = None
    wear_count: int


class WearWeekdayRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    weekday: int
    wear_count: int


class WearSummaryRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_wears: int
    distinct_outfits: int
    days_logged: int
    average_rating: Optional[float] = None
    last_worn_on: Optional[datetime] = None

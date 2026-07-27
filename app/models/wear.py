from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional


class WeatherCondition(str, Enum):
    CLEAR = "CLEAR"
    CLOUDY = "CLOUDY"
    RAIN = "RAIN"
    SNOW = "SNOW"
    WIND = "WIND"
    FOG = "FOG"
    STORM = "STORM"


class WearOccasion(str, Enum):
    EVERYDAY = "EVERYDAY"
    WORK = "WORK"
    SCHOOL = "SCHOOL"
    SPORTS = "SPORTS"
    PARTY = "PARTY"
    DATE = "DATE"
    FORMAL = "FORMAL"
    TRAVEL = "TRAVEL"
    HOME = "HOME"


def _iso(value: Optional[datetime]) -> Optional[str]:
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")


@dataclass
class OutfitWear:
    """A single logged wear of an outfit."""

    wear_id: str
    user_id: str
    outfit_id: str
    worn_on: datetime
    created_at: datetime
    updated_at: datetime
    outfit_name: Optional[str] = None
    feels_like: Optional[float] = None
    temperature: Optional[float] = None
    weather: Optional[WeatherCondition] = None
    occasion: Optional[WearOccasion] = None
    rating: Optional[int] = None
    note: Optional[str] = None
    clothing_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)

        data["worn_on"] = _iso(self.worn_on)
        data["created_at"] = _iso(self.created_at)
        data["updated_at"] = _iso(self.updated_at)

        return data

    @classmethod
    def from_row(cls, row, clothing_ids: Optional[list[str]] = None) -> "OutfitWear":
        return OutfitWear(
            wear_id=row.wear_id,
            user_id=row.user_id,
            outfit_id=row.outfit_id,
            worn_on=row.worn_on,
            created_at=row.created_at,
            updated_at=row.updated_at,
            outfit_name=getattr(row, "outfit_name", None),
            feels_like=float(row.feels_like) if row.feels_like is not None else None,
            temperature=float(row.temperature) if row.temperature is not None else None,
            weather=WeatherCondition(row.weather) if row.weather else None,
            occasion=WearOccasion(row.occasion) if row.occasion else None,
            rating=row.rating,
            note=row.note,
            clothing_ids=clothing_ids or [],
        )


@dataclass
class OutfitWearCount:
    """Wear totals for a single outfit."""

    outfit_id: str
    name: str
    wear_count: int
    last_worn_on: Optional[datetime]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["last_worn_on"] = _iso(self.last_worn_on)
        return data


@dataclass
class ClothingWearCount:
    """Wear totals for a single clothing item."""

    clothing_id: str
    name: str
    category: str
    sub_category: str
    image_id: str
    wear_count: int
    last_worn_on: Optional[datetime]

    def to_dict(self) -> dict:
        data = asdict(self)
        data["last_worn_on"] = _iso(self.last_worn_on)
        return data


@dataclass
class WearStats:
    """Aggregated wear statistics over a date range."""

    date_from: Optional[date]
    date_to: Optional[date]
    total_wears: int
    distinct_outfits: int
    days_logged: int
    current_streak: int
    longest_streak: int
    average_rating: Optional[float]
    last_worn_on: Optional[datetime]
    top_outfits: list[OutfitWearCount]
    by_weekday: dict[str, int]
    by_weather: dict[str, int]
    by_occasion: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "from": self.date_from.isoformat() if self.date_from else None,
            "to": self.date_to.isoformat() if self.date_to else None,
            "total_wears": self.total_wears,
            "distinct_outfits": self.distinct_outfits,
            "days_logged": self.days_logged,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "average_rating": self.average_rating,
            "last_worn_on": _iso(self.last_worn_on),
            "top_outfits": [outfit.to_dict() for outfit in self.top_outfits],
            "by_weekday": self.by_weekday,
            "by_weather": self.by_weather,
            "by_occasion": self.by_occasion,
        }

__all__ = ["wear_manager"]

import traceback
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlspec.exceptions import UniqueViolationError

from app.core.database import get_session
from app.core.logging import get_logger
from app.models.wear import (
    ClothingWearCount,
    OutfitWear,
    OutfitWearCount,
    WearOccasion,
    WearStats,
    WeatherCondition,
)
from app.persistence.queries import outfit as outfit_queries
from app.persistence.queries import wear as wear_queries
from app.utils.exceptions import (
    OutfitIDMissingError,
    OutfitNotFoundError,
    WearAlreadyLoggedError,
    WearIDMissingError,
    WearLimitInvalidError,
    WearNoteTooLongError,
    WearNotFoundError,
    WearOccasionInvalidError,
    WearOffsetInvalidError,
    WearRangeInvalidError,
    WearRatingInvalidError,
    WearTemperatureInvalidError,
    WearValidationError,
    WearWeatherInvalidError,
    WearWornOnInFutureError,
    WearWornOnInvalidError,
)

logger = get_logger()

MAX_NOTE_LENGTH = 255
MIN_TEMPERATURE = -100.0
MAX_TEMPERATURE = 100.0
FUTURE_TOLERANCE = timedelta(days=1)
WEEKDAY_NAMES = [
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
]


def _utc_now() -> datetime:
    """Current UTC time without tzinfo, matching how the database stores timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _parse_worn_on(value: Any) -> datetime:
    """Parses an ISO date or datetime into a naive UTC timestamp."""
    if value is None:
        return _utc_now()

    if not isinstance(value, str) or not value.strip():
        raise WearWornOnInvalidError

    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        raise WearWornOnInvalidError

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    parsed = parsed.replace(microsecond=0)

    if parsed > _utc_now() + FUTURE_TOLERANCE:
        raise WearWornOnInFutureError

    return parsed


def _parse_temperature(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WearTemperatureInvalidError

    if not MIN_TEMPERATURE <= float(value) <= MAX_TEMPERATURE:
        raise WearTemperatureInvalidError

    return float(value)


def _parse_weather(value: Any) -> Optional[WeatherCondition]:
    if value is None:
        return None

    if not isinstance(value, str) or value.strip().upper() not in (
        WeatherCondition.__members__
    ):
        raise WearWeatherInvalidError

    return WeatherCondition[value.strip().upper()]


def _parse_occasion(value: Any) -> Optional[WearOccasion]:
    if value is None:
        return None

    if not isinstance(value, str) or value.strip().upper() not in (
        WearOccasion.__members__
    ):
        raise WearOccasionInvalidError

    return WearOccasion[value.strip().upper()]


def _parse_rating(value: Any) -> Optional[int]:
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int):
        raise WearRatingInvalidError

    if not 1 <= value <= 5:
        raise WearRatingInvalidError

    return value


def _parse_note(value: Any) -> Optional[str]:
    if value is None:
        return None

    if not isinstance(value, str):
        raise WearValidationError

    note = value.strip()

    if not note:
        return None

    if len(note) > MAX_NOTE_LENGTH:
        raise WearNoteTooLongError

    return note


def _parse_pagination(limit: Any, offset: Any) -> tuple[int, int]:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 0 < limit <= 100:
        raise WearLimitInvalidError

    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise WearOffsetInvalidError

    return limit, offset


def _parse_range(
    date_from: Optional[str], date_to: Optional[str]
) -> tuple[Optional[date], Optional[date]]:
    """Parses the inclusive from/to day bounds used by the log and stats endpoints."""
    parsed_from: Optional[date] = None
    parsed_to: Optional[date] = None

    if date_from:
        try:
            parsed_from = date.fromisoformat(date_from)
        except (TypeError, ValueError):
            raise WearRangeInvalidError

    if date_to:
        try:
            parsed_to = date.fromisoformat(date_to)
        except (TypeError, ValueError):
            raise WearRangeInvalidError

    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise WearRangeInvalidError

    return parsed_from, parsed_to


def _streaks(worn_dates: list[date]) -> tuple[int, int]:
    """Returns the current and longest run of consecutive logged days.

    Expects distinct days ordered newest first. The current streak only counts
    when the newest day is today or yesterday.
    """
    if not worn_dates:
        return 0, 0

    today = datetime.now(timezone.utc).date()
    current = 0

    if worn_dates[0] in (today, today - timedelta(days=1)):
        expected = worn_dates[0]
        for worn_date in worn_dates:
            if worn_date != expected:
                break
            current += 1
            expected -= timedelta(days=1)

    longest = 1
    run = 1
    for previous, following in zip(worn_dates, worn_dates[1:]):
        run = run + 1 if previous - following == timedelta(days=1) else 1
        longest = max(longest, run)

    return current, longest


class WearManager:
    def log_wear(
        self,
        user_id: str,
        outfit_id: Optional[str],
        worn_on: Any = None,
        feels_like: Any = None,
        temperature: Any = None,
        weather: Any = None,
        occasion: Any = None,
        rating: Any = None,
        note: Any = None,
    ) -> OutfitWear:
        """Logs that an outfit was worn, snapshotting its current clothing items."""
        if not isinstance(outfit_id, str) or not outfit_id.strip():
            raise OutfitIDMissingError

        parsed_worn_on = _parse_worn_on(worn_on)
        parsed_feels_like = _parse_temperature(feels_like)
        parsed_temperature = _parse_temperature(temperature)
        parsed_weather = _parse_weather(weather)
        parsed_occasion = _parse_occasion(occasion)
        parsed_rating = _parse_rating(rating)
        parsed_note = _parse_note(note)

        wear_id = str(uuid.uuid4())

        try:
            with get_session() as session:
                outfit = outfit_queries.get_basic_for_patch(session, user_id, outfit_id)

                if outfit is None:
                    raise OutfitNotFoundError

                if wear_queries.exists_for_outfit_on_day(
                    session, user_id, outfit_id, parsed_worn_on.date()
                ):
                    raise WearAlreadyLoggedError

                wear_queries.create(
                    session,
                    wear_id=wear_id,
                    user_id=user_id,
                    outfit_id=outfit_id,
                    worn_on=parsed_worn_on,
                    feels_like=parsed_feels_like,
                    temperature=parsed_temperature,
                    weather=parsed_weather.value if parsed_weather else None,
                    occasion=parsed_occasion.value if parsed_occasion else None,
                    rating=parsed_rating,
                    note=parsed_note,
                )

                clothing_ids = [
                    row.clothing_id
                    for row in wear_queries.get_outfit_clothing_ids(session, outfit_id)
                ]
                wear_queries.add_clothing_snapshot(session, wear_id, clothing_ids)
        except (OutfitNotFoundError, WearAlreadyLoggedError, WearValidationError):
            raise
        except UniqueViolationError:
            # Lost the race against a concurrent log of the same outfit and day.
            raise WearAlreadyLoggedError
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while logging a wear of outfit {outfit_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return self.get_wear_by_id(user_id, wear_id)

    def get_wear_by_id(self, user_id: str, wear_id: Optional[str]) -> OutfitWear:
        if not isinstance(wear_id, str) or not wear_id.strip():
            raise WearIDMissingError

        try:
            row = wear_queries.get_by_id_for_user(user_id, wear_id)

            if row is None:
                raise WearNotFoundError

            clothing_ids = [
                link.clothing_id
                for link in wear_queries.get_clothing_ids_by_wear_ids([wear_id])
            ]

            return OutfitWear.from_row(row, clothing_ids)
        except WearNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving wear entry {wear_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

    def get_wear_log(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        outfit_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OutfitWear], int]:
        """Returns a user's wear log, newest first, optionally filtered by day range."""
        limit, offset = _parse_pagination(limit, offset)
        parsed_from, parsed_to = _parse_range(date_from, date_to)

        try:
            rows, total = wear_queries.list_for_user(
                user_id=user_id,
                date_from=parsed_from,
                date_to=parsed_to,
                outfit_id=outfit_id,
                limit=limit,
                offset=offset,
            )

            return self._attach_clothing(rows), total
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving the wear log for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

    def get_wear_log_for_outfit(
        self,
        user_id: str,
        outfit_id: Optional[str],
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OutfitWear], int]:
        """Returns the wear history of a single outfit owned by the user."""
        if not isinstance(outfit_id, str) or not outfit_id.strip():
            raise OutfitIDMissingError

        if outfit_queries.get_by_id_for_user(user_id, outfit_id) is None:
            raise OutfitNotFoundError

        return self.get_wear_log(
            user_id, outfit_id=outfit_id, limit=limit, offset=offset
        )

    def patch_wear(self, user_id: str, wear_id: str, data: dict) -> OutfitWear:
        """Updates the mutable fields of a wear entry that were sent by the client."""
        if not isinstance(wear_id, str) or not wear_id.strip():
            raise WearIDMissingError

        fields: dict = {}

        if "worn_on" in data:
            fields["worn_on"] = _parse_worn_on(data["worn_on"])

        if "feels_like" in data:
            fields["feels_like"] = _parse_temperature(data["feels_like"])

        if "temperature" in data:
            fields["temperature"] = _parse_temperature(data["temperature"])

        if "weather" in data:
            weather = _parse_weather(data["weather"])
            fields["weather"] = weather.value if weather else None

        if "occasion" in data:
            occasion = _parse_occasion(data["occasion"])
            fields["occasion"] = occasion.value if occasion else None

        if "rating" in data:
            fields["rating"] = _parse_rating(data["rating"])

        if "note" in data:
            fields["note"] = _parse_note(data["note"])

        try:
            with get_session() as session:
                current = wear_queries.get_by_id_in_session(session, user_id, wear_id)

                if current is None:
                    raise WearNotFoundError

                new_worn_on = fields.get("worn_on")
                if (
                    new_worn_on is not None
                    and new_worn_on.date() != current.worn_on.date()
                    and wear_queries.exists_for_outfit_on_day(
                        session, user_id, current.outfit_id, new_worn_on.date()
                    )
                ):
                    raise WearAlreadyLoggedError

                wear_queries.update_fields(session, wear_id, fields)
        except (WearNotFoundError, WearAlreadyLoggedError, WearValidationError):
            raise
        except UniqueViolationError:
            raise WearAlreadyLoggedError
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while updating wear entry {wear_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return self.get_wear_by_id(user_id, wear_id)

    def delete_wear(self, user_id: str, wear_id: Optional[str]) -> None:
        if not isinstance(wear_id, str) or not wear_id.strip():
            raise WearIDMissingError

        try:
            with get_session() as session:
                if wear_queries.get_by_id_in_session(session, user_id, wear_id) is None:
                    raise WearNotFoundError

                success = wear_queries.soft_delete_for_user(session, user_id, wear_id)

                if not success:
                    raise WearNotFoundError
        except WearNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while deleting wear entry {wear_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

    def sync_wears(
        self, user_id: str, updated_since: datetime
    ) -> tuple[list[OutfitWear], list[str]]:
        try:
            updated_rows = wear_queries.get_updated_since(user_id, updated_since)
            deleted_rows = wear_queries.get_deleted_ids_since(user_id, updated_since)

            updated_wears = self._attach_clothing(updated_rows)
            deleted_ids = [row.wear_id for row in deleted_rows]
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving updated and deleted wear entries for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return updated_wears, deleted_ids

    def get_stats(
        self,
        user_id: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        top_limit: int = 5,
    ) -> WearStats:
        """Aggregates a user's wear log into totals, streaks and distributions."""
        parsed_from, parsed_to = _parse_range(date_from, date_to)

        if not isinstance(top_limit, int) or isinstance(top_limit, bool):
            raise WearLimitInvalidError

        if not 0 < top_limit <= 50:
            raise WearLimitInvalidError

        try:
            summary = wear_queries.get_summary(user_id, parsed_from, parsed_to)
            worn_dates = [
                row.worn_date
                for row in wear_queries.get_worn_dates(user_id, parsed_from, parsed_to)
            ]
            top_outfits = wear_queries.get_top_outfits(
                user_id, parsed_from, parsed_to, top_limit
            )
            weekday_rows = wear_queries.get_counts_by_weekday(
                user_id, parsed_from, parsed_to
            )
            weather_rows = wear_queries.get_counts_by_column(
                user_id, "weather", parsed_from, parsed_to
            )
            occasion_rows = wear_queries.get_counts_by_column(
                user_id, "occasion", parsed_from, parsed_to
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while aggregating wear stats for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        current_streak, longest_streak = _streaks(worn_dates)

        by_weekday = {name: 0 for name in WEEKDAY_NAMES}
        for weekday_row in weekday_rows:
            if 0 <= weekday_row.weekday < len(WEEKDAY_NAMES):
                by_weekday[WEEKDAY_NAMES[weekday_row.weekday]] = weekday_row.wear_count

        by_weather = {condition.value: 0 for condition in WeatherCondition}
        for weather_row in weather_rows:
            if weather_row.bucket in by_weather:
                by_weather[str(weather_row.bucket)] = weather_row.wear_count

        by_occasion = {occasion.value: 0 for occasion in WearOccasion}
        for occasion_row in occasion_rows:
            if occasion_row.bucket in by_occasion:
                by_occasion[str(occasion_row.bucket)] = occasion_row.wear_count

        average_rating = (
            round(float(summary.average_rating), 2)
            if summary and summary.average_rating is not None
            else None
        )

        return WearStats(
            date_from=parsed_from,
            date_to=parsed_to,
            total_wears=summary.total_wears if summary else 0,
            distinct_outfits=summary.distinct_outfits if summary else 0,
            days_logged=summary.days_logged if summary else 0,
            current_streak=current_streak,
            longest_streak=longest_streak,
            average_rating=average_rating,
            last_worn_on=summary.last_worn_on if summary else None,
            top_outfits=[
                OutfitWearCount(
                    outfit_id=row.outfit_id,
                    name=row.name,
                    wear_count=row.wear_count,
                    last_worn_on=row.last_worn_on,
                )
                for row in top_outfits
            ],
            by_weekday=by_weekday,
            by_weather=by_weather,
            by_occasion=by_occasion,
        )

    def get_clothing_wear_stats(
        self,
        user_id: str,
        least_worn_first: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ClothingWearCount], int]:
        """Returns how often each clothing item was worn, never-worn items included."""
        limit, offset = _parse_pagination(limit, offset)

        try:
            rows, total = wear_queries.get_clothing_wear_counts(
                user_id=user_id,
                least_worn_first=least_worn_first,
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while aggregating clothing wear stats for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return [
            ClothingWearCount(
                clothing_id=row.clothing_id,
                name=row.name,
                category=row.category,
                sub_category=row.sub_category,
                image_id=row.image_id,
                wear_count=row.wear_count,
                last_worn_on=row.last_worn_on,
            )
            for row in rows
        ], total

    def _attach_clothing(self, rows: list) -> list[OutfitWear]:
        """Batch-loads the clothing snapshot for a page of wear rows."""
        if not rows:
            return []

        wear_ids = [row.wear_id for row in rows]
        clothing_by_wear: dict[str, list[str]] = {}

        for link in wear_queries.get_clothing_ids_by_wear_ids(wear_ids):
            clothing_by_wear.setdefault(link.wear_id, []).append(link.clothing_id)

        return [
            OutfitWear.from_row(row, clothing_by_wear.get(row.wear_id, []))
            for row in rows
        ]


wear_manager = WearManager()

__all__ = ["recommendation_manager", "plausible_seasons", "target_warmth"]

import traceback
from typing import Any, Optional

from app.core.logging import get_logger
from app.models.outfit import OutfitSummary, OutfitTags
from app.models.season import Season
from app.persistence.queries import outfit as outfit_queries
from app.persistence.queries import recommendation as recommendation_queries
from app.utils.exceptions import ValidationError

logger = get_logger()

MIN_FEELS_LIKE = -50.0
MAX_FEELS_LIKE = 60.0
MIN_LIMIT = 1
MAX_LIMIT = 20

# (tolerance, cooldown_days) walked in order, each step topping up what the previous
# ones already found. The last step drops both filters, so a user who owns outfits
# never gets an empty answer.
FALLBACK_STEPS: tuple[tuple[Optional[int], int], ...] = ((1, 7), (2, 7), (None, 0))


def plausible_seasons(feels_like: float) -> list[str]:
    """The times of year a felt temperature could plausibly belong to.

    Derived from the temperature rather than from the calendar month on purpose: the
    month says nothing without knowing the hemisphere, while 24 °C means summer clothing
    in Hamburg and in Melbourne alike. Shoulder temperatures deliberately name several
    seasons, so an outfit labelled for either one still ranks as a match.
    """
    if feels_like >= 20:
        return [Season.SUMMER.value]

    if feels_like >= 12:
        return [Season.SPRING.value, Season.SUMMER.value, Season.AUTUMN.value]

    if feels_like >= 5:
        return [Season.SPRING.value, Season.AUTUMN.value, Season.WINTER.value]

    return [Season.WINTER.value]


def target_warmth(feels_like: float) -> int:
    """Maps a felt temperature in °C onto the 1..5 warmth scale of clothing items."""
    if feels_like >= 22:
        return 1

    if feels_like >= 15:
        return 2

    if feels_like >= 8:
        return 3

    if feels_like >= 0:
        return 4

    return 5


def _parse_feels_like(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError

    if not MIN_FEELS_LIKE <= float(value) <= MAX_FEELS_LIKE:
        raise ValidationError

    return float(value)


def _parse_limit(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError

    if not MIN_LIMIT <= value <= MAX_LIMIT:
        raise ValidationError

    return value


class RecommendationManager:
    def recommend_outfits(
        self,
        user_id: str,
        feels_like: Any = None,
        limit: Any = 5,
    ) -> list[OutfitSummary]:
        """Recommends outfits of a user that suit the felt temperature sent by the client."""
        parsed_feels_like = _parse_feels_like(feels_like)
        parsed_limit = _parse_limit(limit)
        target = target_warmth(parsed_feels_like)
        seasons = plausible_seasons(parsed_feels_like)

        try:
            outfit_ids: list[str] = []
            seen: set[str] = set()

            for tolerance, cooldown_days in FALLBACK_STEPS:
                if len(outfit_ids) >= parsed_limit:
                    break

                for candidate in recommendation_queries.get_candidates(
                    user_id=user_id,
                    target=target,
                    tolerance=tolerance,
                    cooldown_days=cooldown_days,
                    limit=parsed_limit,
                    seasons=seasons,
                ):
                    if candidate.outfit_id in seen:
                        continue

                    seen.add(candidate.outfit_id)
                    outfit_ids.append(candidate.outfit_id)

            return self._to_summaries(user_id, outfit_ids[:parsed_limit])
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while recommending outfits for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

    def _to_summaries(self, user_id: str, outfit_ids: list[str]) -> list[OutfitSummary]:
        """Batch-loads the outfit rows plus seasons and tags, keeping the candidate order."""
        if not outfit_ids:
            return []

        rows = {
            row.outfit_id: row
            for row in outfit_queries.get_by_ids_for_user(user_id, outfit_ids)
        }

        seasons_by_outfit: dict[str, list[Season]] = {}
        for season_link in outfit_queries.get_seasons_by_outfit_ids(outfit_ids):
            seasons_by_outfit.setdefault(season_link.outfit_id, []).append(
                Season(season_link.season)
            )

        tags_by_outfit: dict[str, list[OutfitTags]] = {}
        for tag_link in outfit_queries.get_tags_by_outfit_ids(outfit_ids):
            tags_by_outfit.setdefault(tag_link.outfit_id, []).append(
                OutfitTags(tag_link.tag)
            )

        return [
            OutfitSummary.from_dict(
                rows[outfit_id].model_dump(),
                seasons_by_outfit.get(outfit_id, []),
                tags_by_outfit.get(outfit_id, []),
            )
            for outfit_id in outfit_ids
            if outfit_id in rows
        ]


recommendation_manager = RecommendationManager()

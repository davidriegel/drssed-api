__all__ = ["clothing_manager"]

import os
import traceback
import uuid
from datetime import datetime, timezone
from re import match as re_match
from typing import Optional, cast

from app.core.database import get_session
from app.core.logging import get_logger
from app.models.clothing import (
    Clothing,
    ClothingCategory,
    ClothingSubCategory,
    ClothingTags,
)
from app.models.season import Season
from app.persistence.queries import clothing as clothing_queries
from app.persistence.queries import outfit as outfit_queries
from app.services.image import image_manager
from app.utils.exceptions import (
    ClothingColorMissingError,
    ClothingIDMissingError,
    ClothingImageMissingError,
    ClothingNameTooLongError,
    ClothingNameTooShortError,
    ClothingNotFoundError,
    ClothingSubCategoryMissingError,
    ClothingTagsInvalidError,
    ClothingValidationError,
    ClothingWarmthLevelInvalidError,
    ConflictError,
    SeasonsInvalidError,
    ValidationError,
)

logger = get_logger()

MIN_WARMTH_LEVEL = 1
MAX_WARMTH_LEVEL = 5


def _is_valid_warmth_level(warmth_level) -> bool:
    """Warmth level must be an integer between 1 (coldest/airiest) and 5 (warmest)."""
    return (
        isinstance(warmth_level, int)
        and not isinstance(warmth_level, bool)
        and MIN_WARMTH_LEVEL <= warmth_level <= MAX_WARMTH_LEVEL
    )


class ClothingManager:
    def sync_clothes(
        self, user_id: str, updated_since: datetime
    ) -> tuple[list[Clothing], list[str]]:
        try:
            updated_rows = clothing_queries.get_updated_since(user_id, updated_since)
            deleted_rows = clothing_queries.get_deleted_ids_since(
                user_id, updated_since
            )

            updated_clothes: list[Clothing] = []
            for row in updated_rows:
                seasons = clothing_queries.get_seasons_by_clothing_id(row.clothing_id)
                tags = clothing_queries.get_tags_by_clothing_id(row.clothing_id)

                updated_clothes.append(
                    Clothing.from_dict(
                        row.model_dump(),
                        [Season[s.season] for s in seasons],
                        [ClothingTags[t.tag] for t in tags],
                    )
                )

            deleted_ids = [row.clothing_id for row in deleted_rows]
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving updated and deleted clothes for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return updated_clothes, deleted_ids

    def create_clothing(
        self,
        user_id: str,
        name: str,
        sub_category: ClothingSubCategory,
        image_id: str,
        color: str,
        warmth_level: int,
        seasons: list[Season],
        tags: list[ClothingTags],
    ) -> Clothing:
        color_regex = r"^#([A-Fa-f0-9]{6})$"
        if isinstance(color, str) and not re_match(color_regex, color):
            raise ValidationError

        if not _is_valid_warmth_level(warmth_level):
            raise ClothingWarmthLevelInvalidError

        if not os.path.exists(
            os.path.join("app", "static", "temp", image_id + ".webp")
        ):
            raise ValidationError("The provided image file does not exist.")

        if len(name) < 3 or len(name) > 50:
            raise ValidationError

        clothing_id = str(uuid.uuid4())

        clothing = Clothing(
            clothing_id,
            True,
            name,
            sub_category.category,
            sub_category,
            color,
            warmth_level,
            datetime.now(timezone.utc),
            user_id,
            image_id,
            seasons,
            tags,
        )

        try:
            with get_session() as session:
                clothing_queries.create(
                    session,
                    clothing_id=clothing.clothing_id,
                    is_public=clothing.is_public,
                    name=clothing.name,
                    category=clothing.sub_category.category.name,
                    sub_category=clothing.sub_category.name,
                    image_id=clothing.image_id,
                    user_id=clothing.user_id,
                    color=clothing.color,
                    warmth_level=clothing.warmth_level,
                )
                clothing_queries.add_seasons(
                    session, clothing.clothing_id, [s.name for s in clothing.seasons]
                )
                clothing_queries.add_tags(
                    session, clothing.clothing_id, [t.name for t in clothing.tags]
                )
        except Exception as e:
            if "Duplicate entry" in str(e) or "IntegrityError" in type(e).__name__:
                raise ConflictError
            logger.error(
                f"An unexpected error occurred while adding a new clothing to the database: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        image_manager.move_preview_image_to_permanent(image_id)

        return clothing

    def get_clothing_by_id(self, user_id: str, clothing_id: Optional[str]) -> Clothing:
        if not isinstance(clothing_id, str) or not clothing_id.strip():
            raise ClothingIDMissingError("The clothing ID is missing.")

        try:
            row = clothing_queries.get_by_id(user_id, clothing_id)
            if row is None:
                raise ClothingNotFoundError(
                    "The provided ID does not match any clothing in the database."
                )

            seasons = clothing_queries.get_seasons_by_clothing_id(clothing_id)
            tags = clothing_queries.get_tags_by_clothing_id(clothing_id)

            return Clothing.from_dict(
                row.model_dump(),
                [Season[s.season] for s in seasons],
                [ClothingTags[t.tag] for t in tags],
            )
        except ClothingNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving clothing by ID: {e}"
            )
            logger.error(traceback.format_exc())
            raise

    def get_list_of_clothing_by_user_id(
        self,
        user_id: str,
        category: Optional[ClothingCategory] = None,
        seasons: Optional[list[Season]] = None,
        tags: Optional[list[ClothingTags]] = None,
        limit: int = 50,
        offset: int = 0,
        only_public: bool = True,
    ) -> list[Clothing]:
        category_name = category.name if category else None
        season_names = [s.name for s in seasons] if seasons else None
        tag_names = [t.name for t in tags] if tags else None

        rows = clothing_queries.list_for_user(
            user_id=user_id,
            only_public=only_public,
            category=category_name,
            seasons=season_names,
            tags=tag_names,
            limit=limit,
            offset=offset,
        )

        if not rows:
            return []

        clothing_ids = [row.clothing_id for row in rows]

        seasons_by_clothing: dict[str, list[Season]] = {}
        for season_row in clothing_queries.get_seasons_by_clothing_ids(clothing_ids):
            seasons_by_clothing.setdefault(season_row.clothing_id, []).append(
                Season[season_row.season]
            )

        tags_by_clothing: dict[str, list[ClothingTags]] = {}
        for tag_row in clothing_queries.get_tags_by_clothing_ids(clothing_ids):
            tags_by_clothing.setdefault(tag_row.clothing_id, []).append(
                ClothingTags[tag_row.tag]
            )

        return [
            Clothing.from_dict(
                row.model_dump(),
                seasons_by_clothing.get(row.clothing_id, []),
                tags_by_clothing.get(row.clothing_id, []),
            )
            for row in rows
        ]

    def update_clothing(
        self,
        user_id: str,
        clothing_id: str,
        name: Optional[str] = None,
        sub_category: Optional[str] = None,
        color: Optional[str] = None,
        warmth_level: Optional[int] = None,
        seasons: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        image_id: Optional[str] = None,
    ) -> Clothing:
        try:
            with get_session() as session:
                current = clothing_queries.get_basic_for_update(
                    session, user_id, clothing_id
                )

                if current is None:
                    raise ClothingNotFoundError(
                        "The provided ID does not match any clothing in the database for the current user."
                    )

                fields: dict = {}

                if isinstance(name, str):
                    if len(name) < 3:
                        raise ClothingNameTooShortError(
                            "The provided name is too short, it has to be at least 3 characters long."
                        )
                    if len(name) > 50:
                        raise ClothingNameTooLongError(
                            "The provided name is too long, it has to be at most 50 characters long."
                        )
                    if name != current.name:
                        fields["name"] = name

                color_regex = r"^#([A-Fa-f0-9]{6})$"
                if isinstance(color, str):
                    if not re_match(color_regex, color):
                        raise ClothingColorMissingError(
                            "The color is missing or invalid. It should be a hex color code (e.g., #FFFFFF)."
                        )
                    fields["color"] = color

                if warmth_level is not None:
                    if not _is_valid_warmth_level(warmth_level):
                        raise ClothingWarmthLevelInvalidError(
                            "The warmth level is invalid. It has to be an integer between 1 and 5."
                        )
                    if warmth_level != current.warmth_level:
                        fields["warmth_level"] = warmth_level

                if isinstance(image_id, str):
                    if not os.path.exists(
                        os.path.join("app", "static", "temp", image_id + ".webp")
                    ):
                        raise ClothingImageMissingError(
                            "The provided image file does not exist."
                        )

                    image_manager.delete_clothing_image(image_id=image_id)
                    fields["image_id"] = image_id
                    image_manager.move_preview_image_to_permanent(image_id)

                if isinstance(sub_category, str):
                    if sub_category.upper() not in ClothingSubCategory.__members__:
                        raise ClothingSubCategoryMissingError(
                            "The provided sub category is not valid. It should be one of the following: "
                            + ", ".join(ClothingSubCategory.__members__.keys())
                        )
                    fields["sub_category"] = sub_category.upper()

                if fields:
                    clothing_queries.update_fields(session, clothing_id, fields)

                if seasons is not None:
                    existing_seasons = [
                        s.season
                        for s in clothing_queries.get_seasons_in_session(
                            session, clothing_id
                        )
                    ]
                    if seasons != existing_seasons:
                        new_seasons = [s for s in seasons if s not in existing_seasons]
                        old_seasons = [s for s in existing_seasons if s not in seasons]

                        clothing_queries.remove_seasons(
                            session, clothing_id, old_seasons
                        )

                        normalized_new_seasons = []
                        for season in new_seasons:
                            if season.strip().upper() not in Season.__members__:
                                raise SeasonsInvalidError(
                                    f"The provided season ({season}) is not valid."
                                )
                            normalized_new_seasons.append(season.strip().upper())
                        clothing_queries.add_seasons(
                            session, clothing_id, normalized_new_seasons
                        )

                if tags is not None:
                    existing_tags = [
                        t.tag
                        for t in clothing_queries.get_tags_in_session(
                            session, clothing_id
                        )
                    ]
                    if tags != existing_tags:
                        new_tags = [t for t in tags if t not in existing_tags]
                        old_tags = [t for t in existing_tags if t not in tags]

                        clothing_queries.remove_tags(session, clothing_id, old_tags)

                        normalized_new_tags = []
                        for tag in new_tags:
                            if tag.strip().upper() not in ClothingTags.__members__:
                                raise ClothingTagsInvalidError(
                                    f"The provided tag ({tag}) is not valid."
                                )
                            normalized_new_tags.append(tag.strip().upper())
                        clothing_queries.add_tags(
                            session, clothing_id, normalized_new_tags
                        )
        except (ClothingValidationError, ClothingNotFoundError):
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while updating clothing with ID {clothing_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return self.get_clothing_by_id(user_id, clothing_id)

    def get_image_id_by_clothing_id(self, user_id: str, clothing_id: str) -> str:
        """Returns the image_id for a clothing item owned by the user."""
        clothing = self.get_clothing_by_id(user_id, clothing_id)
        return clothing.image_id

    def soft_delete_clothing_by_id(self, user_id: str, clothing_id: str) -> None:
        try:
            with get_session() as session:
                image_row = clothing_queries.get_image_id(session, user_id, clothing_id)

                if image_row is None:
                    raise ClothingNotFoundError

                affected_outfits = clothing_queries.get_outfits_affected_by_clothing(
                    session, clothing_id
                )

                clothing_queries.soft_delete(session, user_id, clothing_id)
                outfit_queries.remove_clothing_from_outfits(session, clothing_id)

                for affected in affected_outfits:
                    if cast(int, affected.item_count) <= 2:
                        outfit_queries.soft_delete_by_id(session, affected.outfit_id)

            image_manager.delete_clothing_image(image_row.image_id)
        except ClothingNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error while soft deleting clothing {clothing_id}: {e}"
            )
            raise


clothing_manager = ClothingManager()

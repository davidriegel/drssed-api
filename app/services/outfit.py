__all__ = ["outfit_manager"]

import traceback
import uuid
from datetime import datetime, timezone
from random import choice, random
from typing import Optional

from app.core.database import get_session
from app.core.logging import get_logger
from app.models.clothing import Clothing, ClothingCategory, ClothingTags
from app.models.outfit import CanvasPlacement, Outfit, OutfitSummary, OutfitTags
from app.models.season import Season
from app.persistence.queries import clothing as clothing_queries
from app.persistence.queries import outfit as outfit_queries
from app.persistence.schemas.outfit import OutfitClothingRow
from app.services.clothing import clothing_manager
from app.services.image import image_manager
from app.utils.exceptions import (
    OutfitClothingIDInvalidError,
    OutfitFavoriteMissingError,
    OutfitIDMissingError,
    OutfitLimitInvalidError,
    OutfitNameMissingError,
    OutfitNameTooLongError,
    OutfitNameTooShortError,
    OutfitNotFoundError,
    OutfitOffsetInvalidError,
    OutfitPermissionError,
    OutfitPublicMissingError,
    OutfitSceneInvalidError,
    OutfitSceneMissingError,
    OutfitTagsInvalidError,
    OutfitValidationError,
    SeasonsInvalidError,
    UnprocessableEntityError,
)

logger = get_logger()


def _canvas_from_row(row: OutfitClothingRow) -> CanvasPlacement:
    return CanvasPlacement(
        clothing_id=row.clothing_id,
        x=float(row.position_x),
        y=float(row.position_y),
        z=int(row.z_index),
        scale=float(row.scale),
        rotation=float(row.rotation),
    )


class OutfitManager:
    def generate_outfit(
        self,
        user_id: str,
        seasons: Optional[list[Season]] = None,
        tags: Optional[list[OutfitTags]] = None,
        anchor: Optional[list[str]] = None,
        amount: int = 3,
    ) -> list[Outfit]:
        """Generate new outfit options, optionally based on season, tags or anchor clothing items."""
        clothing_tags = [ClothingTags[t.name] for t in tags] if tags else None

        suitable_clothes: list[Clothing] = (
            clothing_manager.get_list_of_clothing_by_user_id(
                user_id,
                seasons=seasons,
                tags=clothing_tags,
                limit=1000,
                only_public=False,
            )
        )  # high limit, outfit generation needs full filtered pool

        if not suitable_clothes:
            raise UnprocessableEntityError

        items_by_category: dict[ClothingCategory, list[Clothing]] = {}
        for clothing in suitable_clothes:
            items_by_category.setdefault(clothing.category, []).append(clothing)

        jackets = items_by_category.get(ClothingCategory.JACKET, [])
        tops = items_by_category.get(ClothingCategory.TOP, [])
        bottoms = items_by_category.get(ClothingCategory.BOTTOM, [])
        one_pieces = items_by_category.get(ClothingCategory.ONE_PIECE, [])

        can_build_default = bool(tops) and bool(bottoms)
        can_build_one_pice = bool(one_pieces)

        if not can_build_default and not can_build_one_pice:
            raise UnprocessableEntityError

        outfits: list[Outfit] = []
        for _ in range(amount):
            if can_build_default and can_build_one_pice:
                use_one_piece = choice([True, False])
            else:
                use_one_piece = can_build_one_pice

            chosen_items: list[Clothing] = []
            if use_one_piece:
                chosen_items.append(choice(one_pieces))
            else:
                chosen_items.append(choice(tops))
                chosen_items.append(choice(bottoms))

            if jackets and random() < 0.5:
                chosen_items.append(choice(jackets))

            scene = self._build_default_scene(chosen_items)

            outfit = Outfit(
                outfit_id=str(uuid.uuid4()),
                is_public=False,
                is_favorite=False,
                name="",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                user_id=user_id,
                scene=scene,
                seasons=seasons or [season for season in Season],
                tags=tags or [tag for tag in OutfitTags],
            )
            outfits.append(outfit)

        if not outfits:
            raise UnprocessableEntityError

        return outfits

    def _build_default_scene(self, items: list[Clothing]) -> list[CanvasPlacement]:
        DEFAULT_POSITIONS = {
            ClothingCategory.JACKET: (0.5, 0.2, 4),
            ClothingCategory.TOP: (0.5, 0.4, 3),
            ClothingCategory.BOTTOM: (0.5, 0.7, 2),
            ClothingCategory.ONE_PIECE: (0.5, 0.5, 1),
        }

        placements: list[CanvasPlacement] = []
        for clothing in items:
            x, y, z = DEFAULT_POSITIONS[clothing.category]
            placements.append(CanvasPlacement(clothing.clothing_id, x, y, z, 0.25, 0))

        return placements

    def sync_outfits(
        self, user_id: str, updated_since: datetime
    ) -> tuple[list[Outfit], list[str]]:
        try:
            updated_rows = outfit_queries.get_updated_since(user_id, updated_since)
            deleted_rows = outfit_queries.get_deleted_ids_since(user_id, updated_since)

            updated_outfits: list[Outfit] = []
            for row in updated_rows:
                season_rows = outfit_queries.get_seasons_by_outfit_id(row.outfit_id)
                tag_rows = outfit_queries.get_tags_by_outfit_id(row.outfit_id)
                canvas_rows = outfit_queries.get_clothing_canvas(row.outfit_id)

                updated_outfits.append(
                    Outfit.from_dict(
                        row.model_dump(),
                        [_canvas_from_row(c) for c in canvas_rows],
                        [Season[s.season] for s in season_rows],
                        [OutfitTags[t.tag] for t in tag_rows],
                    )
                )

            deleted_ids = [row.outfit_id for row in deleted_rows]
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving updated and deleted outfits for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return updated_outfits, deleted_ids

    def create_outfit(
        self,
        user_id: str,
        name: str,
        scene: dict,
        seasons: Optional[list[str]],
        tags: Optional[list[str]],
        is_public: bool,
        is_favorite: bool,
    ) -> Outfit:
        if not isinstance(name, str) or not name.strip():
            raise OutfitNameMissingError("The provided name is missing or invalid.")

        if len(name) < 3:
            raise OutfitNameTooShortError(
                "The provided name is too short, it has to be at least 3 characters long."
            )

        if len(name) > 50:
            raise OutfitNameTooLongError(
                "The provided name is too long, it has to be at most 50 characters long."
            )

        seasons_typed: Optional[list[Season]] = None
        if seasons is not None:
            if not isinstance(seasons, list) or not all(
                isinstance(season, str) for season in seasons
            ):
                raise SeasonsInvalidError("Seasons must be a list of strings.")

            for season in seasons:
                if season.strip().upper() not in Season.__members__:
                    raise SeasonsInvalidError(
                        f"The provided season ({season}) is not valid."
                    )

            seasons_typed = [Season[season.strip().upper()] for season in seasons]

        tags_typed: Optional[list[OutfitTags]] = None
        if tags is not None:
            if not isinstance(tags, list) or not all(
                isinstance(tag, str) for tag in tags
            ):
                raise OutfitTagsInvalidError("Tags must be a list of strings.")

            for tag in tags:
                if tag.strip().upper() not in OutfitTags.__members__:
                    raise OutfitTagsInvalidError(
                        f"The provided tag ({tag}) is not valid."
                    )

            tags_typed = [OutfitTags[tag.strip().upper()] for tag in tags]

        if not isinstance(is_public, bool):
            raise OutfitPublicMissingError("The is_public is missing.")

        if not isinstance(is_favorite, bool):
            raise OutfitFavoriteMissingError("The is_favorite is missing.")

        if not isinstance(scene, list):
            raise OutfitSceneMissingError("scene is missing or invalid.")

        if len(scene) < 2:
            raise OutfitSceneInvalidError("scene.items must contain at least 2 items.")

        clothing_ids = []
        for item in scene:
            cid = item.get("clothing_id")
            if not isinstance(cid, str) or not cid.strip():
                raise OutfitSceneInvalidError("scene item clothing_id missing.")
            clothing_ids.append(cid)

            for sub_key in ("x", "y", "scale", "rotation", "z"):
                if sub_key not in item:
                    raise OutfitSceneInvalidError(f"scene item missing '{sub_key}'.")

        outfit_id = str(uuid.uuid4())

        with get_session() as session:
            for cid in clothing_ids:
                if not clothing_queries.exists_active_for_user(session, user_id, cid):
                    raise OutfitClothingIDInvalidError(
                        f"Clothing ID {cid} invalid or not owned by user."
                    )

        validated_items = []
        clothing_canvas: list[CanvasPlacement] = []

        for item in scene:
            clothing_id = item["clothing_id"]
            image_id = clothing_manager.get_image_id_by_clothing_id(
                user_id=user_id,
                clothing_id=clothing_id,
            )

            validated_items.append({"item": item, "image_id": image_id})

            clothing_canvas.append(
                CanvasPlacement(
                    clothing_id=clothing_id,
                    x=item["x"],
                    y=item["y"],
                    z=item["z"],
                    scale=item["scale"],
                    rotation=item["rotation"],
                )
            )

        image_manager.generate_outfit_preview(outfit_id, items=validated_items)

        outfit = Outfit(
            outfit_id=outfit_id,
            is_public=is_public,
            is_favorite=is_favorite,
            name=name,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            user_id=user_id,
            scene=clothing_canvas,
            seasons=seasons_typed,
            tags=tags_typed,
        )

        try:
            with get_session() as session:
                outfit_queries.create(
                    session,
                    outfit_id=outfit_id,
                    is_public=is_public,
                    is_favorite=is_favorite,
                    name=name,
                    user_id=user_id,
                )

                if outfit.seasons:
                    outfit_queries.add_seasons(
                        session, outfit_id, [s.name for s in outfit.seasons]
                    )
                if outfit.tags:
                    outfit_queries.add_tags(
                        session, outfit_id, [t.name for t in outfit.tags]
                    )

                outfit_queries.add_clothing_placements(
                    session,
                    outfit_id,
                    [
                        {
                            "clothing_id": p.clothing_id,
                            "x": p.x,
                            "y": p.y,
                            "z": p.z,
                            "scale": p.scale,
                            "rotation": p.rotation,
                        }
                        for p in clothing_canvas
                    ],
                )
        except Exception:
            try:
                image_manager.delete_outfit_preview(outfit_id)
            except Exception:
                pass
            raise

        return outfit

    def get_outfit_by_id(self, user_id: str, outfit_id: Optional[str]) -> Outfit:
        if not isinstance(outfit_id, str) or not outfit_id.strip():
            raise OutfitIDMissingError("The provided outfit ID is missing or invalid.")

        try:
            row = outfit_queries.get_by_id_for_user(user_id, outfit_id)

            if row is None:
                raise OutfitNotFoundError(
                    "The provided ID does not match any outfit in the database."
                )

            seasons = [
                Season[s.season]
                for s in outfit_queries.get_seasons_by_outfit_id(outfit_id)
            ]
            tags = [
                OutfitTags[t.tag]
                for t in outfit_queries.get_tags_by_outfit_id(outfit_id)
            ]
            clothing_canvas = [
                _canvas_from_row(c)
                for c in outfit_queries.get_clothing_canvas(outfit_id)
            ]

            return Outfit(
                outfit_id=row.outfit_id,
                is_public=row.is_public,
                is_favorite=row.is_favorite,
                name=row.name,
                created_at=row.created_at,
                updated_at=row.updated_at,
                user_id=user_id,
                scene=clothing_canvas,
                seasons=seasons,
                tags=tags,
            )
        except OutfitNotFoundError:
            raise
        except OutfitPermissionError:
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving outfit with ID {outfit_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

    def get_list_of_outfits_by_user_id(
        self,
        user_id: Optional[str],
        limit: int = 50,
        offset: int = 0,
        include_private: bool = False,
    ) -> tuple[list[OutfitSummary], int]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise OutfitIDMissingError("The provided user ID is missing or invalid.")

        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise OutfitLimitInvalidError(
                "The limit must be a positive integer and cannot exceed 100."
            )

        if not isinstance(offset, int) or offset < 0:
            raise OutfitOffsetInvalidError("The offset must be a positive integer.")

        try:
            rows, total_outfits = outfit_queries.list_for_user(
                user_id=user_id,
                include_private=include_private,
                limit=limit,
                offset=offset,
            )

            outfit_list: list[OutfitSummary] = []
            for row in rows:
                season_rows = outfit_queries.get_seasons_by_outfit_id(row.outfit_id)
                tag_rows = outfit_queries.get_tags_by_outfit_id(row.outfit_id)

                outfit_list.append(
                    OutfitSummary.from_dict(
                        row.model_dump(),
                        [Season(s.season) for s in season_rows],
                        [OutfitTags(t.tag) for t in tag_rows],
                    )
                )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while retrieving outfits for user {user_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return outfit_list, total_outfits

    def patch_outfit(
        self,
        user_id: str,
        outfit_id: str,
        name: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        is_public: Optional[bool] = None,
        seasons: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        scene: Optional[list[dict]] = None,
    ) -> Outfit:
        try:
            with get_session() as session:
                current = outfit_queries.get_basic_for_patch(
                    session, user_id, outfit_id
                )

                if current is None:
                    raise OutfitNotFoundError

                fields: dict = {}

                if isinstance(name, str):
                    if len(name) < 3:
                        raise OutfitNameTooShortError()
                    if len(name) > 50:
                        raise OutfitNameTooLongError()
                    if name != current.name:
                        fields["name"] = name

                if is_public is not None and is_public != current.is_public:
                    fields["is_public"] = is_public

                if is_favorite is not None and is_favorite != current.is_favorite:
                    fields["is_favorite"] = is_favorite

                outfit_queries.update_fields(session, outfit_id, fields)

                if seasons is not None:
                    self._update_outfit_seasons(session, outfit_id, seasons)

                if tags is not None:
                    self._update_outfit_tags(session, outfit_id, tags)

                if scene is not None:
                    self._update_outfit_scene(session, user_id, outfit_id, scene)
        except (OutfitValidationError, OutfitNotFoundError):
            raise
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while updating outfit with ID {outfit_id}: {e}"
            )
            logger.error(traceback.format_exc())
            raise

        return self.get_outfit_by_id(user_id, outfit_id)

    def _update_outfit_scene(
        self, session, user_id: str, outfit_id: str, scene: list
    ) -> None:
        if len(scene) < 2:
            raise OutfitSceneInvalidError("scene.items must contain at least 2 items.")

        clothing_ids = []
        for item in scene:
            cid = item.get("clothing_id")
            if not isinstance(cid, str) or not cid.strip():
                raise OutfitSceneInvalidError("scene item clothing_id missing.")
            clothing_ids.append(cid)

            for sub_key in ("x", "y", "scale", "rotation", "z"):
                if sub_key not in item:
                    raise OutfitSceneInvalidError(f"scene item missing '{sub_key}'.")

        for cid in clothing_ids:
            if not clothing_queries.exists_for_user(session, user_id, cid):
                raise OutfitClothingIDInvalidError(
                    f"Clothing ID {cid} invalid or not owned by user."
                )

        validated_items = []
        clothing_canvas: list[CanvasPlacement] = []

        for item in scene:
            clothing_id = item["clothing_id"]
            image_id = clothing_manager.get_image_id_by_clothing_id(
                user_id=user_id,
                clothing_id=clothing_id,
            )

            validated_items.append({"item": item, "image_id": image_id})

            clothing_canvas.append(
                CanvasPlacement(
                    clothing_id=clothing_id,
                    x=item["x"],
                    y=item["y"],
                    z=item["z"],
                    scale=item["scale"],
                    rotation=item["rotation"],
                )
            )

        image_manager.generate_outfit_preview(
            outfit_id=outfit_id, items=validated_items
        )

        outfit_queries.clear_clothing_placements(session, outfit_id)
        outfit_queries.add_clothing_placements(
            session,
            outfit_id,
            [
                {
                    "clothing_id": p.clothing_id,
                    "x": p.x,
                    "y": p.y,
                    "z": p.z,
                    "scale": p.scale,
                    "rotation": p.rotation,
                }
                for p in clothing_canvas
            ],
        )

    def _update_outfit_seasons(
        self, session, outfit_id: str, new_seasons: list[str]
    ) -> None:
        existing_seasons = {
            s.season for s in outfit_queries.get_seasons_in_session(session, outfit_id)
        }
        new_seasons_set = {season.strip().upper() for season in new_seasons}

        for season in new_seasons_set:
            if season not in Season.__members__:
                raise SeasonsInvalidError(f"Invalid season: {season}")

        seasons_to_add = new_seasons_set - existing_seasons
        seasons_to_remove = existing_seasons - new_seasons_set

        outfit_queries.remove_seasons(session, outfit_id, list(seasons_to_remove))
        outfit_queries.add_seasons(session, outfit_id, list(seasons_to_add))

    def _update_outfit_tags(self, session, outfit_id: str, new_tags: list[str]) -> None:
        existing_tags = {
            t.tag for t in outfit_queries.get_tags_in_session(session, outfit_id)
        }
        new_tags_set = {tag.strip().upper() for tag in new_tags}

        for tag in new_tags_set:
            if tag not in OutfitTags.__members__:
                raise OutfitTagsInvalidError(f"Invalid tag: {tag}")

        tags_to_add = new_tags_set - existing_tags
        tags_to_remove = existing_tags - new_tags_set

        outfit_queries.remove_tags(session, outfit_id, list(tags_to_remove))
        outfit_queries.add_tags(session, outfit_id, list(tags_to_add))

    def soft_delete_outfit_by_id(self, user_id: str, outfit_id: str) -> None:
        try:
            with get_session() as session:
                affected = outfit_queries.soft_delete_for_user(
                    session, user_id, outfit_id
                )

                if affected == 0:
                    raise OutfitNotFoundError
        except OutfitNotFoundError:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error while soft deleting outfit {outfit_id}: {e}"
            )
            raise

        image_manager.delete_outfit_preview(outfit_id)


outfit_manager = OutfitManager()

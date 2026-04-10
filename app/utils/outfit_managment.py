__all__ = ["outfit_manager"]

import traceback
import uuid
import threading
from datetime import datetime
from app.utils.database import Database
from app.utils.exceptions import OutfitNotFoundError, OutfitNameTooShortError, OutfitNameTooLongError, OutfitDescriptionTooLongError, OutfitNameMissingError, OutfitClothingIDsMissingError, OutfitClothingIDInvalidError, OutfitSeasonsInvalidError, OutfitTagsInvalidError, OutfitIDMissingError, OutfitPermissionError, OutfitLimitInvalidError, OutfitOffsetInvalidError, OutfitValidationError, OutfitPublicMissingError, OutfitFavoriteMissingError, OutfitSceneMissingError, OutfitSceneInvalidError
from typing import Optional, cast
from mysql.connector.errors import IntegrityError
from app.models.outfit import Outfit, OutfitTags, OutfitSeason, CanvasPlacement
from app.utils.helpers import helper
from app.utils.clothing_managment import clothing_manager
from app.utils.image_managment import image_manager
from app.utils.logging import get_logger

logger = get_logger()

class OutfitManager:
    def sync_outfits(self, user_id: str, updated_since: datetime) -> tuple[list[Outfit], list[str]]:
        updated_outfits: list[Outfit] = []
        deleted_ids: list[str] = []
        
        statement = """
            SELECT outfit_id, name, is_favorite, is_public, created_at, updated_at, description, user_id
            FROM outfits
            WHERE user_id = %s AND updated_at > %s AND deleted_at IS NULL
            ORDER BY updated_at ASC
        """
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(statement, (user_id, updated_since,))

                updated_rows = cursor.fetchall()
                
                for outfit in updated_rows:
                    outfit = helper.ensure_dict(outfit)
                    
                    cursor.execute("SELECT season FROM outfit_seasons WHERE outfit_id = %s;", (outfit.get("outfit_id"),))
                    seasons = cursor.fetchall()
                    
                    cursor.execute("SELECT tag FROM outfit_tags WHERE outfit_id = %s;", (outfit.get("outfit_id"),))
                    tags = cursor.fetchall()
                    
                    cursor.execute("SELECT clothing_id, position_x, position_y, z_index, scale, rotation FROM outfit_clothing WHERE outfit_id = %s ORDER BY z_index;", (outfit.get("outfit_id"),))
                    clothing_list = cursor.fetchall()
                    
                    clothing_canvas = [
                        CanvasPlacement(
                            clothing_id=helper.ensure_dict(clothing).get("clothing_id"),
                            x=helper.ensure_dict(clothing).get("position_x"),
                            y=helper.ensure_dict(clothing).get("position_y"),
                            z=helper.ensure_dict(clothing).get("z_index"),
                            scale=helper.ensure_dict(clothing).get("scale"),
                            rotation=helper.ensure_dict(clothing).get("rotation")
                        )
                        for clothing in clothing_list
                    ]
                    
                    seasons_list = [
                        OutfitSeason[helper.ensure_dict(season).get("season", "")]
                        for season in seasons
                    ]

                    tags_list = [
                        OutfitTags[helper.ensure_dict(tag).get("tag", "")]
                        for tag in tags
                    ]

                    outfit_instance = Outfit.from_dict(
                        outfit,
                        clothing_canvas,
                        seasons_list,
                        tags_list
                    )
                    
                    updated_outfits.append(outfit_instance)
                    
                cursor.execute("""
                    SELECT outfit_id
                    FROM outfits
                    WHERE user_id = %s AND deleted_at IS NOT NULL AND deleted_at > %s
                    """,
                    (user_id, updated_since, )
                )
                
                deleted_rows = cursor.fetchall()
                
                for row in deleted_rows:
                    row = helper.ensure_dict(row)
                    deleted_ids.append(row.get("outfit_id", ""))
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving updated and deleted outfits for user {user_id}: {e}")
            logger.error(traceback.format_exc())
            raise e

        return updated_outfits, deleted_ids

    def create_outfit(self, user_id: str, name: str, scene: dict, seasons: Optional[list[str]], tags: Optional[list[str]], is_public: bool, is_favorite: bool, description: Optional[str] = None) -> Outfit:
        if not isinstance(name, str) or not name.strip():
            raise OutfitNameMissingError("The provided name is missing or invalid.")
        
        if len(name) < 3:
            raise OutfitNameTooShortError("The provided name is too short, it has to be at least 3 characters long.")

        if len(name) > 50:
            raise OutfitNameTooLongError("The provided name is too long, it has to be at most 50 characters long.")

        if seasons is not None:
            if not isinstance(seasons, list) or not all(isinstance(season, str) for season in seasons):
                raise OutfitSeasonsInvalidError("Seasons must be a list of strings.")
            
            for season in seasons:
                if season.strip().upper() not in OutfitSeason.__members__:
                    raise OutfitSeasonsInvalidError(f"The provided season ({season}) is not valid.")

            seasons = [OutfitSeason[season.strip().upper()] for season in seasons]

        if tags is not None:
            if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
                raise OutfitTagsInvalidError("Tags must be a list of strings.")

            for tag in tags:
                if tag.strip().upper() not in OutfitTags.__members__:
                    raise OutfitTagsInvalidError(f"The provided tag ({tag}) is not valid.")

            tags = [OutfitTags[tag.strip().upper()] for tag in tags]
        
        if not isinstance(is_public, bool):
            raise OutfitPublicMissingError("The is_public is missing.")
            
        if not isinstance(is_favorite, bool):
            raise OutfitFavoriteMissingError("The is_favorite is missing.")

        if isinstance(description, str) and len(description) > 255:
            raise OutfitDescriptionTooLongError("The provided description is too long, it has to be at most 255 characters long.")

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

        for cid in clothing_ids:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM clothing WHERE clothing_id = %s AND user_id = %s AND deleted_at IS NULL;",
                    (cid, user_id)
                )
                if cursor.fetchone() is None:
                    raise OutfitClothingIDInvalidError(f"Clothing ID {cid} invalid or not owned by user.")
        
        validated_items = []
        clothing_canvas: list[CanvasPlacement] = []

        for item in scene:
            clothing_id = item["clothing_id"]
            image_id = clothing_manager.get_image_id_by_clothing_id(
                user_id=user_id,
                clothing_id=clothing_id
            )

            validated_items.append({
                "item": item,
                "image_id": image_id
            })
            
            clothing_canvas.append(CanvasPlacement(clothing_id=clothing_id, x=item["x"], y=item["y"], z=item["z"], scale=item["scale"], rotation=item["rotation"]))
        
        image_manager.generate_outfit_preview(outfit_id, items=validated_items)

        outfit = Outfit(
            outfit_id=outfit_id,
            is_public=is_public,
            is_favorite=is_favorite,
            name=name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id=user_id,
            scene=clothing_canvas,
            seasons=seasons,
            tags=tags,
            description=description
        )

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO outfits(outfit_id, is_public, is_favorite, name, user_id, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (
                    outfit_id, is_public, is_favorite, name, user_id, description, 
                ))

                if outfit.seasons:
                    for season in outfit.seasons:
                        cursor.execute("INSERT INTO outfit_seasons(outfit_id, season) VALUES (%s, %s);", (outfit_id, season.name))
                if outfit.tags:
                    for tag in outfit.tags:
                        cursor.execute("INSERT INTO outfit_tags(outfit_id, tag) VALUES (%s, %s);", (outfit_id, tag.name))
                for item in clothing_canvas:
                    cursor.execute("INSERT INTO outfit_clothing(outfit_id, clothing_id, position_x, position_y, z_index, scale, rotation) VALUES (%s, %s, %s, %s, %s, %s, %s);", (outfit_id, item.clothing_id, item.x, item.y, item.z, item.scale, item.rotation))

                conn.commit()
        except Exception as e:
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
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT is_public, is_favorite, name, created_at, description, updated_at FROM outfits WHERE outfit_id = %s AND user_id = %s AND deleted_at IS NULL;", (outfit_id, user_id,))
                outfit = cursor.fetchone()
                
                if outfit is None:
                        raise OutfitNotFoundError("The provided ID does not match any outfit in the database.")
                
                outift_is_public, outfit_is_favorite, outfit_name, outfit_created_at, outfit_description, outfit_updated_at = outfit
                    
                cursor.execute("SELECT season FROM outfit_seasons WHERE outfit_id = %s;", (outfit_id,))
                seasons = [OutfitSeason[cast(str, season)] for (season,) in cursor.fetchall()]
                    
                cursor.execute("SELECT tag FROM outfit_tags WHERE outfit_id = %s;", (outfit_id,))
                tags = [OutfitTags[cast(str, tag)] for (tag,) in cursor.fetchall()]
                    
                cursor.execute("SELECT clothing_id, position_x, position_y, z_index, scale, rotation FROM outfit_clothing WHERE outfit_id = %s;", (outfit_id,))
                rows = cast(list[tuple], cursor.fetchall())
                clothing_canvas = [helper._parse_canvas_row(row) for row in rows]
                
                outfit = Outfit(outfit_id, bool(outift_is_public), bool(outfit_is_favorite), cast(str, outfit_name), cast(datetime, outfit_created_at), cast(datetime, outfit_updated_at), user_id, clothing_canvas, seasons, tags, cast(str, outfit_description))
        except OutfitNotFoundError as e:
            raise e
        except OutfitPermissionError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving outfit with ID {outfit_id}: {e}")
            logger.error(traceback.format_exc())
            raise e

        return outfit

    def get_list_of_outfits_by_user_id(self, user_id: Optional[str], limit: int = 1000, offset: int = 0, include_private: bool = False) -> tuple[list[Outfit], int]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise OutfitIDMissingError("The provided user ID is missing or invalid.")
        
        if not isinstance(limit, int) or limit <= 0 or limit > 1000:
            raise OutfitLimitInvalidError("The limit must be a positive integer and cannot exceed 1000.")

        if not isinstance(offset, int) or offset < 0:
            raise OutfitOffsetInvalidError("The offset must be a positive integer.")
        
        outfit_list: list[Outfit] = []
        total_outfits: int = 0
        
        conditions: list[str] = ["user_id = %s"]
        params: list = [user_id]
        
        if not include_private:
            conditions.append("is_public = %s")
            params.append(True)
            
        where_clause = " AND ".join(conditions)
        
        statement = f"""
            SELECT outfit_id, is_public, is_favorite, name, user_id, image_id, created_at
            FROM outfits
            WHERE {where_clause} AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT %s
            OFFSET %s;
        """
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT COUNT(*) as total FROM outfits WHERE " + where_clause + " AND deleted_at IS NULL", tuple(params))
                total_result = cursor.fetchone()
                
                total_result = helper.ensure_dict(total_result)
                total_outfits = total_result.get("total", 0)
                
                params.extend([limit, offset])
                
                cursor.execute(statement, tuple(params))

                outfits = cursor.fetchall()
                
                for outfit in outfits:
                    outfit = helper.ensure_dict(outfit)
                    
                    cursor.execute("SELECT season FROM outfit_seasons WHERE outfit_id = %s;", (outfit.get("outfit_id"),))
                    seasons = cursor.fetchall()
                    
                    cursor.execute("SELECT tag FROM outfit_tags WHERE outfit_id = %s;", (outfit.get("outfit_id"),))
                    tags = cursor.fetchall()

                    seasons_list = [
                        OutfitSeason[helper.ensure_dict(season).get("season", "")]
                        for season in seasons
                    ]

                    tags_list = [
                        OutfitTags[helper.ensure_dict(tag).get("tag", "")]
                        for tag in tags
                    ]

                    outfit_instance = Outfit.from_dict(
                        outfit,
                        None,
                        seasons_list,
                        tags_list
                    )
                    
                    outfit_list.append(outfit_instance)
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving outfits for user {user_id}: {e}")
            logger.error(traceback.format_exc())
            raise e

        return outfit_list, total_outfits
        
    def patch_outfit(self, user_id: str, outfit_id: str, name: Optional[str] = None, is_favorite: Optional[bool] = None, is_public: Optional[bool] = None, seasons: Optional[list[str]] = None, tags: Optional[list[str]] = None, scene: Optional[dict] = None) -> Outfit:
        try: 
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT is_favorite, is_public, name FROM outfits WHERE outfit_id = %s AND user_id = %s AND deleted_at IS NULL;", (outfit_id, user_id))
                result = cursor.fetchone()
                
                if result is None:
                    raise OutfitNotFoundError
                
                current_is_favorite, current_is_public, current_name = result
                
                fields = []
                values = []
            
                if isinstance(name, str):
                    if len(name) < 3:
                        raise OutfitNameTooShortError()
                    if len(name) > 50:
                        raise OutfitNameTooLongError()
                    if name != current_name:
                        fields.append("name = %s")
                        values.append(name)
                        
                if is_public is not None and is_public != current_is_public:
                    fields.append("is_public = %s")
                    values.append(is_public)
                    
                if is_favorite is not None and is_favorite != current_is_favorite:
                    fields.append("is_favorite = %s")
                    values.append(is_favorite)
                    
                if fields:
                    query = f"UPDATE outfits SET {', '.join(fields)} WHERE outfit_id = %s;"
                    cursor.execute(query, (*values, outfit_id))
                    
                if seasons is not None:
                    self._update_outfit_seasons(cursor, outfit_id, seasons)
                        
                if tags is not None:
                    self._update_outfit_tags(cursor, outfit_id, tags)
                        
                if scene is not None:
                    self._update_outfit_scene(cursor, user_id, outfit_id, scene)
                
                conn.commit()
        except (OutfitValidationError, OutfitNotFoundError):
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating outfit with ID {outfit_id}: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        return self.get_outfit_by_id(user_id, outfit_id)
    
    def _update_outfit_scene(self, cursor, user_id: str, outfit_id: str, scene: dict) -> None:
        """
        Returns: image_id
        """
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
            cursor.execute(
                "SELECT 1 FROM clothing WHERE clothing_id = %s AND user_id = %s;",
                (cid, user_id)
            )
            if cursor.fetchone() is None:
                raise OutfitClothingIDInvalidError(f"Clothing ID {cid} invalid or not owned by user.")
        
        validated_items = []
        clothing_canvas: list[CanvasPlacement] = []

        for item in scene:
            clothing_id = item["clothing_id"]
            image_id = clothing_manager.get_image_id_by_clothing_id(
                user_id=user_id,
                clothing_id=clothing_id
            )

            validated_items.append({
                "item": item,
                "image_id": image_id
            })
            
            clothing_canvas.append(CanvasPlacement(clothing_id=clothing_id, x=item["x"], y=item["y"], z=item["z"], scale=item["scale"], rotation=item["rotation"]))
        
        threading.Thread(target=image_manager.generate_outfit_preview, args=(outfit_id, validated_items)).start()
        
        cursor.execute("DELETE FROM outfit_clothing WHERE outfit_id = %s;", (outfit_id, ))
        
        for item in clothing_canvas:
            cursor.execute("INSERT INTO outfit_clothing(outfit_id, clothing_id, position_x, position_y, z_index, scale, rotation) VALUES (%s, %s, %s, %s, %s, %s, %s);", (outfit_id, item.clothing_id, item.x, item.y, item.z, item.scale, item.rotation))
    
    def _update_outfit_seasons(self, cursor, outfit_id: str, new_seasons: list[str]) -> None:
        cursor.execute("SELECT season FROM outfit_seasons WHERE outfit_id = %s;", (outfit_id,))
        existing_seasons = {season[0] for season in cursor.fetchall()}
        new_seasons_set = {season.strip().upper() for season in new_seasons}
        
        for season in new_seasons_set:
            if season not in OutfitSeason.__members__:
                raise OutfitSeasonsInvalidError(f"Invalid season: {season}")
            
        seasons_to_add = new_seasons_set - existing_seasons
        seasons_to_remove = existing_seasons - new_seasons_set
        
        if seasons_to_remove:
            cursor.execute("DELETE FROM outfit_seasons WHERE outfit_id = %s AND season IN %s;", (outfit_id, tuple(seasons_to_remove)))
            
        if seasons_to_add:
            values = [(outfit_id, season) for season in seasons_to_add]
            cursor.executemany("INSERT INTO outfit_seasons (outfit_id, season) VALUES (%s, %s);", values)
            
    def _update_outfit_tags(self, cursor, outfit_id: str, new_tags: list[str]) -> None:
        cursor.execute("SELECT tag FROM outfit_tags WHERE outfit_id = %s;", (outfit_id,))
        existing_tags = {tag[0] for tag in cursor.fetchall()}
        new_tags_set = {tag.strip().upper() for tag in new_tags}
        
        for tag in new_tags_set:
            if tag not in OutfitTags.__members__:
                raise OutfitTagsInvalidError(f"Invalid tag: {tag}")
        
        tags_to_add = new_tags_set - existing_tags
        tags_to_remove = existing_tags - new_tags_set
        
        if tags_to_remove:
            cursor.execute("DELETE FROM outfit_tags WHERE outfit_id = %s AND tag IN %s;", (outfit_id, tuple(tags_to_remove)))
        
        if tags_to_add:
            values = [(outfit_id, tag) for tag in tags_to_add]
            cursor.executemany("INSERT INTO outfit_tags (outfit_id, tag) VALUES (%s, %s);", values)

    def delete_outfit_by_id(self, user_id: str, outfit_id: Optional[str]) -> None:
        if not isinstance(outfit_id, str) or not outfit_id.strip():
            raise OutfitIDMissingError("The provided outfit ID is missing or invalid.")

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM outfits WHERE outfit_id = %s AND user_id = %s AND deleted_at IS NULL;", (outfit_id, user_id))
                result = cursor.fetchone()

                if result is None:
                    raise OutfitNotFoundError("The provided ID does not match any outfit in the database for the current user.")

                cursor.execute("DELETE FROM outfit_seasons WHERE outfit_id = %s;", (outfit_id,))
                cursor.execute("DELETE FROM outfit_tags WHERE outfit_id = %s;", (outfit_id,))
                cursor.execute("DELETE FROM outfit_clothing WHERE outfit_id = %s;", (outfit_id,))
                cursor.execute("DELETE FROM outfits WHERE outfit_id = %s;", (outfit_id,))
                conn.commit()
        except OutfitNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while deleting outfit with ID {outfit_id}: {e}")
            logger.error(traceback.format_exc())
            raise e
        return None
    
    
outfit_manager = OutfitManager()

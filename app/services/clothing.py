__all__ = ["clothing_manager"]

import traceback
import uuid
from re import match as re_match
from datetime import datetime, timezone
from app.core.database import Database
from app.utils.exceptions import ValidationError, ConflictError, NotFoundError, ClothingNotFoundError, ClothingImageInvalidError, ClothingNameMissingError, ClothingCategoryMissingError, ClothingColorMissingError, ClothingImageMissingError, ClothingNameTooShortError, ClothingNameTooLongError, ClothingDescriptionTooLongError, ClothingIDMissingError, SeasonsInvalidError, ClothingTagsInvalidError, ClothingValidationError
from typing import Optional, cast
from mysql.connector.errors import IntegrityError
from app.models.clothing import Clothing, ClothingCategory, ClothingSubCategory, ClothingTags
from app.models.season import Season
from app.core.logging import get_logger
from app.utils.helpers import helper
from app.services.image import image_manager
import os

logger = get_logger()

class ClothingManager:
        
    def sync_clothes(self, user_id: str, updated_since: datetime) -> tuple[list[Clothing], list[str]]:
        updated_clothes: list[Clothing] = []
        deleted_ids: list[str] = []
        
        statement = """
            SELECT *
            FROM clothing
            WHERE user_id = %s AND updated_at > %s AND deleted_at IS NULL
            ORDER BY updated_at ASC
        """
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(statement, (user_id, updated_since,))

                updated_rows = cursor.fetchall()
                
                for clothing in updated_rows:
                    clothing = helper.ensure_dict(clothing)
                    
                    cursor.execute("SELECT season FROM clothing_seasons WHERE clothing_id = %s;", (clothing.get("clothing_id"),))
                    seasons = cursor.fetchall()
                    
                    cursor.execute("SELECT tag FROM clothing_tags WHERE clothing_id = %s;", (clothing.get("clothing_id"),))
                    tags = cursor.fetchall()
                    
                    seasons_list = [
                        Season[helper.ensure_dict(season).get("season", "")]
                        for season in seasons
                    ]

                    tags_list = [
                        ClothingTags[helper.ensure_dict(tag).get("tag", "")]
                        for tag in tags
                    ]

                    clothing_instance = Clothing.from_dict(
                        clothing,
                        seasons_list,
                        tags_list
                    )
                    
                    updated_clothes.append(clothing_instance)
                    
                cursor.execute("""
                    SELECT clothing_id
                    FROM clothing
                    WHERE user_id = %s AND deleted_at IS NOT NULL AND deleted_at > %s
                    """,
                    (user_id, updated_since, )
                )
                
                deleted_rows = cursor.fetchall()
                
                for row in deleted_rows:
                    row = helper.ensure_dict(row)
                    deleted_ids.append(row.get("clothing_id", ""))
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving updated and deleted clothes for user {user_id}: {e}")
            logger.error(traceback.format_exc())
            raise e

        return updated_clothes, deleted_ids

    def create_clothing(self, user_id: str, name: str, category: ClothingCategory, sub_category: ClothingSubCategory, image_id: str, color: str, seasons: list[Season], tags: list[ClothingTags], description: Optional[str] = None) -> Clothing:
        color_regex = r"^#([A-Fa-f0-9]{6})$"
        if isinstance(color, str) and not re_match(color_regex, color):
            raise ValidationError

        if not os.path.exists(os.path.join("app", "static", "temp", image_id + ".webp")):
            raise ValidationError("The provided image file does not exist.")
        
        if len(name) < 3:
            raise ValidationError
        
        if len(name) > 50:
            raise ValidationError
            
        if isinstance(description, str) and len(description) > 255:
            raise ValidationError

        clothing_id = str(uuid.uuid4())

        clothing = Clothing(clothing_id, True, name, category, sub_category, color, datetime.now(timezone.utc), user_id, image_id, seasons, tags, description)

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO clothing(clothing_id, is_public, name, category, sub_category, image_id, user_id, color, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);", (clothing.clothing_id, clothing.is_public, clothing.name, clothing.category.name, clothing.sub_category.name, clothing.image_id, clothing.user_id, clothing.color, clothing.description))
                for season in clothing.seasons:
                    cursor.execute("INSERT INTO clothing_seasons(clothing_id, season) VALUES (%s, %s);", (clothing.clothing_id, season.name))
                for tag in clothing.tags:
                    cursor.execute("INSERT INTO clothing_tags(clothing_id, tag) VALUES (%s, %s);", (clothing.clothing_id, tag.name))
                conn.commit()

                image_manager.move_preview_image_to_permanent(image_id)
        except IntegrityError as e:
            raise ConflictError
        except Exception as e:
            logger.error(f"An unexpected error occurred while adding a new clothing to the database: {e}")
            logger.error(traceback.format_exc())
            raise e

        return clothing

    def get_clothing_by_id(self, user_id: str, clothing_id: Optional[str]) -> Clothing:
        if not isinstance(clothing_id, str) or not clothing_id.strip():
            raise ClothingIDMissingError("The clothing ID is missing.")
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM clothing WHERE clothing_id = %s AND user_id = %s AND deleted_at IS NULL;", (clothing_id, user_id,))
                clothing = cursor.fetchone()
                
                if clothing is None:
                    raise ClothingNotFoundError("The provided ID does not match any clothing in the database.")
                
                cursor.execute("SELECT season FROM clothing_seasons WHERE clothing_id = %s;", (clothing_id,))
                seasons = cursor.fetchall()
                
                cursor.execute("SELECT tag FROM clothing_tags WHERE clothing_id = %s;", (clothing_id,))
                tags = cursor.fetchall()
                
                clothing = Clothing.from_dict(clothing, [Season[season.get("season")] for season in seasons], [ClothingTags[tag.get("tag")] for tag in tags])
        except ClothingNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving clothing by ID: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        return clothing

    def get_list_of_clothing_by_user_id(self, user_id: str, category: Optional[ClothingCategory] = None, seasons: Optional[list[Season]] = None, tags: Optional[list[ClothingTags]] = None, limit: int = 50, offset: int = 0, only_public: bool = True) -> list[Clothing]:
        clothes_list: list[Clothing] = []
        
        where_clauses: list[str] = ["c.user_id = %s", "deleted_at IS NULL"]
        params: list[str | bool | int] = [user_id]
        
        if only_public:
            where_clauses.append("is_public = %s")
            params.append(True)
            
        if category:
            where_clauses.append("category = %s")
            params.append(category)
        
        if seasons:
            placeholder = ', '.join(["%s"] * len(seasons))
            where_clauses.append(f"EXISTS (SELECT 1 FROM clothing_seasons cs WHERE cs.clothing_id = c.clothing_id AND cs.season IN ({placeholder}))")
            params.extend(seasons)
            
        if tags:
            placeholder = ', '.join(["%s"] * len(tags))
            where_clauses.append(f"EXISTS (SELECT 1 FROM clothing_tags ct WHERE ct.clothing_id = c.clothing_id AND ct.tag IN ({placeholder}))")
            params.extend(tags)
        
        params.extend([limit, offset])
        
        with Database.getConnection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = f"SELECT c.* FROM clothing c WHERE { ' AND '.join(where_clauses)} ORDER BY c.created_at DESC LIMIT %s OFFSET %s;"
            cursor.execute(query, tuple(params))
            clothes = cursor.fetchall()
            
            if not clothes:
                return []
            
            clothing_ids: list[str] = []
            for clothing_dict in clothes:
                if not isinstance(clothing_dict, dict):
                    raise ValueError("Expected clothing_dict to be dict")
                
                clothing_id = clothing_dict.get("clothing_id")
                
                if not isinstance(clothing_id, str):
                    raise ValueError("Expected clothing_id to be string")
                
                clothing_ids.append(clothing_id)

            seasons_by_clothing: dict[str, list[Season]] = {}
            placeholder = ', '.join(["%s"]  * len(clothing_ids))
            cursor.execute(f"SELECT clothing_id, season FROM clothing_seasons WHERE clothing_id IN ({placeholder})", tuple(clothing_ids))
            clothing_seasons = cursor.fetchall()
            
            if not clothing_seasons:
                raise ValueError("Expected clothing_seasons to not be empty")
            
            for seasons_dict in clothing_seasons:
                if not isinstance(seasons_dict, dict):
                    raise ValueError("Expected seasons_dict to be dict")
                
                clothing_id = seasons_dict.get("clothing_id")
                clothing_season = seasons_dict.get("season")
                
                if not isinstance(clothing_id, str):
                    raise ValueError("Expected clothing_id to be string")
                
                if not isinstance(clothing_season, str):
                    raise ValueError("Expected clothing_season to be string")
                
                seasons_by_clothing.setdefault(clothing_id, []).append(Season[clothing_season])
                
            tags_by_clothing: dict[str, list[ClothingTags]] = {}
            placeholder = ', '.join(["%s"]  * len(clothing_ids))
            cursor.execute(f"SELECT clothing_id, tag FROM clothing_tags WHERE clothing_id IN ({placeholder})", tuple(clothing_ids))
            clothing_tags = cursor.fetchall()
            
            if not clothing_tags:
                raise ValueError("Expected clothing_tags to not be empty")
            
            for tags_dict in clothing_tags:
                if not isinstance(tags_dict, dict):
                    raise ValueError("Expected tags_dict to be dict")
                
                clothing_id = tags_dict.get("clothing_id")
                clothing_tag = tags_dict.get("tag")
                
                if not isinstance(clothing_id, str):
                    raise ValueError("Expected clothing_id to be string")
                
                if not isinstance(clothing_tag, str):
                    raise ValueError("Expected clothing_tag to be string")
                
                tags_by_clothing.setdefault(clothing_id, []).append(ClothingTags[clothing_tag])
                
            for clothing_id, clothing_dict in zip(clothing_ids, clothes):
                if not isinstance(clothing_dict, dict):
                    raise ValueError("Expected clothing_dict to be dict")
                
                clothing = Clothing.from_dict(clothing_dict, seasons=seasons_by_clothing[clothing_id], tags=tags_by_clothing[clothing_id])
                clothes_list.append(clothing)
        
        return clothes_list
    
    def update_clothing(self, user_id: str, clothing_id: str, name: Optional[str] = None, category: Optional[str] = None, description: Optional[str] = None, color: Optional[str] = None, seasons: Optional[list[str]] = None, tags: Optional[list[str]] = None, image_id: Optional[str] = None) -> Clothing:
        fields = []
        values = []

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT clothing_id, name, created_at, user_id, description, category, color, image_id  FROM clothing WHERE clothing_id = %s AND user_id = %s AND deleted_at IS NULL;", (clothing_id, user_id))
                result = cursor.fetchone()

                if result is None:
                    raise ClothingNotFoundError("The provided ID does not match any clothing in the database for the current user.")

                if isinstance(name, str):
                    if len(name) < 3:
                        raise ClothingNameTooShortError("The provided name is too short, it has to be at least 3 characters long.")
                    
                    if len(name) > 50:
                        raise ClothingNameTooLongError("The provided name is too long, it has to be at most 50 characters long.")
                    
                    if name != result[1]:
                        fields.append("name = %s")
                        values.append(name)
                        
                color_regex = r"^#([A-Fa-f0-9]{6})$"
                if isinstance(color, str):
                    if not re_match(color_regex, color):
                        raise ClothingColorMissingError("The color is missing or invalid. It should be a hex color code (e.g., #FFFFFF).")
                    
                    fields.append("color = %s")
                    values.append(color)

                if isinstance(image_id, str):
                    if not os.path.exists(os.path.join("app", "static", "temp", image_id + ".webp")):
                        raise ClothingImageMissingError("The provided image file does not exist.")
                    
                    image_manager.delete_clothing_image(image_id=image_id)
                    fields.append("image_id = %s")
                    values.append(image_id)
                    image_manager.move_preview_image_to_permanent(image_id)

                if isinstance(category, str):
                    if category.upper() not in ClothingCategory.__members__:
                        raise ClothingCategoryMissingError("The provided category is not valid. It should be one of the following: " + ", ".join(ClothingCategory.__members__.keys()))
                    
                    fields.append("category = %s")
                    values.append(category.upper())

                if description is not None and description != result[4]:
                    if len(description) > 255:
                        raise ClothingDescriptionTooLongError("The provided description is too long.")
                    
                    fields.append("description = %s")
                    values.append(description)

                if fields:
                    cursor.execute(f"UPDATE clothing SET {', '.join(fields)} WHERE clothing_id = %s;", (*values, clothing_id))

                cursor.execute("SELECT season FROM clothing_seasons WHERE clothing_id = %s;", (clothing_id,))
                existing_seasons: list[str] = [season[0] for season in cursor.fetchall()]

                if seasons is not None and seasons != existing_seasons:
                    new_seasons = [season for season in seasons if season not in existing_seasons]
                    old_seasons = [season for season in existing_seasons if season not in seasons]
                    
                    if old_seasons:
                        placeholders = ", ".join(["%s"] * len(old_seasons))
                        cursor.execute(f"DELETE FROM clothing_seasons WHERE clothing_id = %s AND season IN ({placeholders});", (clothing_id, *old_seasons))

                    if new_seasons:
                        for season in new_seasons:
                            if season.strip().upper() not in Season.__members__:
                                raise SeasonsInvalidError(f"The provided season ({season}) is not valid.")

                            cursor.execute("INSERT INTO clothing_seasons(clothing_id, season) VALUES (%s, %s);", (clothing_id, season.strip().upper()))

                cursor.execute("SELECT tag FROM clothing_tags WHERE clothing_id = %s;", (clothing_id,))
                existing_tags: list[str] = [tag[0] for tag in cursor.fetchall()]

                if tags is not None and tags != existing_tags:
                    new_tags = [tag for tag in tags if tag not in existing_tags]
                    old_tags = [tag for tag in existing_tags if tag not in tags]
                    
                    if old_tags:
                        placeholders = ", ".join(["%s"] * len(old_tags))
                        cursor.execute(f"DELETE FROM clothing_tags WHERE clothing_id = %s AND tag IN ({placeholders});", (clothing_id, *old_tags))

                    if new_tags:
                        for tag in new_tags:
                            if tag.strip().upper() not in ClothingTags.__members__:
                                raise ClothingTagsInvalidError(f"The provided tag ({tag}) is not valid.")

                            cursor.execute("INSERT INTO clothing_tags(clothing_id, tag) VALUES (%s, %s);", (clothing_id, tag.strip().upper()))
                            
                conn.commit()
        except (ClothingValidationError, ClothingNotFoundError) as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating clothing with ID {clothing_id}: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        return self.get_clothing_by_id(user_id, clothing_id)
    
    def get_image_id_by_clothing_id(self, user_id: str, clothing_id: str) -> str:
        """
        Returns: image_id
        """
        clothing = self.get_clothing_by_id(user_id, clothing_id)
        return clothing.image_id
    
    def soft_delete_clothing_by_id(self, user_id: str, clothing_id: str) -> None:
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT image_id FROM clothing WHERE clothing_id = %s AND user_id = %s AND deleted_at IS NULL;", (clothing_id, user_id,))
                result = cursor.fetchone()
                
                if result is None:
                    raise ClothingNotFoundError
                
                image_id, = result
                
                cursor.execute("SELECT outfit_id, COUNT(*) as item_count FROM outfit_clothing WHERE outfit_id IN ( SELECT outfit_id FROM outfit_clothing WHERE clothing_id = %s) GROUP BY outfit_id", (clothing_id, ))
                affected_outfits = cursor.fetchall()
                
                cursor.execute("UPDATE clothing SET deleted_at = NOW() WHERE clothing_id = %s AND user_id = %s AND deleted_at IS NULL;", (clothing_id, user_id, ))
                
                cursor.execute("DELETE FROM outfit_clothing WHERE clothing_id = %s;", (clothing_id, ))
                
                for outfit_id, item_count in affected_outfits:
                    if cast(int, item_count) <= 2:
                        cursor.execute("UPDATE outfits SET deleted_at = NOW() WHERE outfit_id = %s", (cast(str, outfit_id), ))
                        
                conn.commit()
                
                image_manager.delete_clothing_image(cast(str, image_id))
            except ClothingNotFoundError:
                raise
            except Exception as e:
                conn.rollback()
                logger.error(f"Unexpected error while soft deleting clothing {clothing_id}: {e}")
                raise
            finally:
                cursor.close()
            
clothing_manager = ClothingManager()
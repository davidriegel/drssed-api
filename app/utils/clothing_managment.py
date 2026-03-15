__all__ = ["clothing_manager"]

import traceback
import uuid
from re import match as re_match
from datetime import datetime
from app.utils.database import Database
from app.utils.exceptions import ClothingNotFoundError, ClothingImageInvalidError, ClothingNameMissingError, ClothingCategoryMissingError, ClothingColorMissingError, ClothingImageMissingError, ClothingNameTooShortError, ClothingNameTooLongError, ClothingDescriptionTooLongError, ClothingIDMissingError, ClothingSeasonsInvalidError, ClothingTagsInvalidError, ClothingValidationError
from typing import Optional
from mysql.connector.errors import IntegrityError
from app.models.clothing import Clothing, ClothingCategory, ClothingSeason, ClothingTags
from app.utils.logging import get_logger
from app.utils.helpers import helper
from app.utils.image_managment import image_manager
import os

logger = get_logger()

class ClothingManager:

    def ensure_table_exists(self) -> None:
        with Database.getConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS clothing(
                            clothing_id VARCHAR(36) PRIMARY KEY,
                            is_public BOOLEAN DEFAULT TRUE,
                            name VARCHAR(50) NOT NULL,
                            category VARCHAR(50) NOT NULL,
                            image_id VARCHAR(36) UNIQUE NOT NULL,
                            user_id VARCHAR(36) NOT NULL,
                            color CHAR(7) NOT NULL,
                            description VARCHAR(255) DEFAULT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                            deleted_at TIMESTAMP DEFAULT NULL,
                            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                            );
                            """)
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS clothing_seasons(
                            clothing_id VARCHAR(36) NOT NULL,
                            season ENUM('SPRING', 'SUMMER', 'AUTUMN', 'WINTER') NOT NULL,
                            FOREIGN KEY (clothing_id) REFERENCES clothing(clothing_id) ON DELETE CASCADE
                            );
                            """)
            cursor.execute("""
                            CREATE TABLE IF NOT EXISTS clothing_tags(
                            clothing_id VARCHAR(36) NOT NULL,
                            tag VARCHAR(50) NOT NULL,
                            FOREIGN KEY (clothing_id) REFERENCES clothing(clothing_id) ON DELETE CASCADE
                            );
                            """)
            conn.commit()

    def _delete_unused_image(self, filename: str) -> None:
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM clothing WHERE image_id = %s;", (filename,))
                if cursor.fetchone() is not None:
                    return
            
            os.remove(filename + ".webp")
        except FileNotFoundError:
            pass
        except PermissionError:
            logger.error(f"Permission denied while deleting an image: {filename}")
            logger.error(traceback.format_exc())
            pass
        except Exception as e:
            logger.error(f"An unexpected error occured while deleting an image: {e}")
            logger.error(traceback.format_exc())
            raise e
        
    def sync_clothes(self, user_id: str, updated_since: datetime) -> tuple[list[Clothing], list[str]]:
        updated_clothes: list[Clothing] = []
        deleted_ids: list[str] = []
        
        statement = """
            SELECT clothing_id, is_public, name, category, image_id, user_id, color, description, created_at, updated_at
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
                        ClothingSeason[helper.ensure_dict(season).get("season", "")]
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

    def create_clothing(self, user_id: str, name: str, category: str, image_id: str, color: Optional[str], seasons: Optional[list] = None, tags: Optional[list] = None, description: Optional[str] = None) -> Clothing:
        if not isinstance(name, str) or not name.strip():
            raise ClothingNameMissingError("The name is missing.")
        
        if not isinstance(category, str) or not category.strip():
            raise ClothingCategoryMissingError("The category is missing.")
        
        if not isinstance(image_id, str) or not image_id.strip():
            raise ClothingImageMissingError("The image filename is missing.")
        
        color_regex = r"^#([A-Fa-f0-9]{6})$"
        if isinstance(color, str) and not re_match(color_regex, color):
            raise ClothingColorMissingError("The color is missing or invalid. It should be a hex color code (e.g., #FFFFFF).")

        if not os.path.exists(os.path.join("app", "static", "temp", image_id + ".webp")):
            raise ClothingImageMissingError("The provided image file does not exist.")
        
        if category.upper() not in ClothingCategory.__members__:
            raise ClothingCategoryMissingError("The provided category is not valid. It should be one of the following: " + ", ".join(ClothingCategory.__members__.keys()))
        
        if len(name) < 3:
            raise ClothingNameTooShortError("The provided name is too short, it has to be at least 3 characters long.")
        
        if len(name) > 50:
            raise ClothingNameTooLongError("The provided name is too long, it has to be at most 50 characters long.")
            
        if isinstance(description, str) and len(description) > 255:
            raise ClothingDescriptionTooLongError("The provided description is too long, it has to be at most 255 characters long.")

        if isinstance(seasons, list) and all(isinstance(season, str) for season in seasons):
            for season in seasons:
                if str(season).upper() not in ClothingSeason.__members__:
                    raise ValueError(f"The provided season ({season}) is not valid. It should be one of the following: " + ", ".join(ClothingSeason.__members__.keys()))
        
            seasons = [ClothingSeason[season.upper()] for season in seasons]
        
        if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
            for tag in tags:
                if str(tag).upper() not in ClothingTags.__members__:
                    raise ValueError(f"The provided tag ({tag}) is not valid. It should be one of the following: " + ", ".join(ClothingTags.__members__.keys()))
        
            tags = [ClothingTags[tag.upper()] for tag in tags]

        clothing_id = str(uuid.uuid4())

        clothing = Clothing(clothing_id, True, name, ClothingCategory[category.upper()], color, datetime.now(), user_id, image_id, seasons, tags, description)

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO clothing(clothing_id, is_public, name, category, image_id, user_id, color, description) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);", (clothing.clothing_id, clothing.is_public, clothing.name, clothing.category.name, clothing.image_id, clothing.user_id, clothing.color, clothing.description))
                for season in clothing.seasons:
                    cursor.execute("INSERT INTO clothing_seasons(clothing_id, season) VALUES (%s, %s);", (clothing.clothing_id, season.name))
                for tag in clothing.tags:
                    cursor.execute("INSERT INTO clothing_tags(clothing_id, tag) VALUES (%s, %s);", (clothing.clothing_id, tag.name))
                conn.commit()

                image_manager.move_preview_image_to_permanent(image_id)
        except IntegrityError as e:
            raise ClothingImageInvalidError("The provided image is already used by another clothing.")
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
                cursor.execute("SELECT clothing_id, is_public, name, category, color, created_at, image_id, user_id, description FROM clothing WHERE clothing_id = %s AND user_id = %s;", (clothing_id, user_id,))
                clothing = cursor.fetchone()
                
                if clothing is None:
                    raise ClothingNotFoundError("The provided ID does not match any clothing in the database.")
                
                cursor.execute("SELECT season FROM clothing_seasons WHERE clothing_id = %s;", (clothing_id,))
                seasons = cursor.fetchall()
                
                cursor.execute("SELECT tag FROM clothing_tags WHERE clothing_id = %s;", (clothing_id,))
                tags = cursor.fetchall()
                
                clothing = Clothing.from_dict(clothing, [ClothingSeason[season.get("season")] for season in seasons], [ClothingTags[tag.get("tag")] for tag in tags])
        except ClothingNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving clothing by ID: {e}")
            logger.error(traceback.format_exc())
            raise e
        
        return clothing

    def get_list_of_clothing_by_user_id(self, user_id: Optional[str], category: Optional[str], limit: int = 1000, offset: int = 0, include_private: bool = False) -> list[Clothing]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ClothingIDMissingError("The provided user ID is missing or invalid.")

        clothes_list: list[Clothing] = []
        
        conditions: list[str] = ["user_id = %s"]
        params: list = [user_id]
        
        if not include_private:
            conditions.append("is_public = %s")
            params.append(True)
            
        if isinstance(category, str):
            if category.upper() not in ClothingCategory.__members__:
                raise ClothingCategoryMissingError("The provided category is not valid. It should be one of the following: " + ", ".join(ClothingCategory.__members__.keys()))
            
            conditions.append("category = %s")
            params.append(category)
            
        where_clause = " AND ".join(conditions)
            
        statement = f"""
            SELECT clothing_id, is_public, name, category, color, created_at, user_id, image_id, description
            FROM clothing
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s
            OFFSET %s;
        """
        
        params.extend([limit, offset])
        
        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(statement, tuple(params))
                clothes = cursor.fetchall()

                for clothing in clothes:
                    clothing_id = clothing.get("clothing_id")
                    cursor.execute("SELECT season FROM clothing_seasons WHERE clothing_id = %s;", (clothing_id,))
                    seasons = cursor.fetchall()
                
                    cursor.execute("SELECT tag FROM clothing_tags WHERE clothing_id = %s;", (clothing_id,))
                    tags = cursor.fetchall()

                    clothing = Clothing.from_dict(clothing, [ClothingSeason[season.get("season")] for season in seasons], [ClothingTags[tag.get("tag")] for tag in tags])
                    clothes_list.append(clothing)
        except Exception as e:
            logger.error(f"An unexpected error occurred while retrieving clothes for user {user_id}: {e}")
            logger.error(f"{traceback.format_exc()}")
            raise e
        
        return clothes_list
    
    def update_clothing(self, user_id: str, clothing_id: str, name: Optional[str] = None, category: Optional[str] = None, description: Optional[str] = None, color: Optional[str] = None, seasons: Optional[list[str]] = None, tags: Optional[list[str]] = None, image_id: Optional[str] = None) -> Clothing:
        fields = []
        values = []

        try:
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT clothing_id, name, created_at, user_id, description, category, color, image_id  FROM clothing WHERE clothing_id = %s AND user_id = %s;", (clothing_id, user_id))
                result = cursor.fetchone()

                if result is None:
                    raise ClothingNotFoundError("The provided ID does not match any clothing in the database for the current user.")

                if isinstance(name, str):
                    if len(name) < 3:
                        raise ClothingNameTooShortError("The provided name is too short, it has to be at least 3 characters long.")
                    
                    if len(name) > 50:
                        raise ClothingNameTooLongError("The provided name is too long, it has to be at most 50 characters long.")
                    
                    if name != result[2]:
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
                    
                    self._delete_unused_image(image_id)
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
                            if season.strip().upper() not in ClothingSeason.__members__:
                                raise ClothingSeasonsInvalidError(f"The provided season ({season}) is not valid.")

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
        
    
    def delete_clothing_by_id(self, user_id: str, clothing_id: str) -> None:
        if not isinstance(clothing_id, str) or not clothing_id.strip():
            raise ClothingIDMissingError("The clothing ID is missing.")
        
        try:    
            with Database.getConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT image_id FROM clothing WHERE clothing_id = %s AND user_id = %s;", (clothing_id, user_id,))
                image_id = cursor.fetchone()
                
                if image_id is None:
                    raise ClothingNotFoundError("The provided clothing ID does not match any clothing in the database.")
                
                cursor.execute("DELETE FROM clothing_tags WHERE clothing_id = %s;", (clothing_id,))
                cursor.execute("DELETE FROM clothing_seasons WHERE clothing_id = %s;", (clothing_id,))
                cursor.execute("DELETE FROM clothing WHERE clothing_id = %s AND user_id = %s;", (clothing_id, user_id,))
                conn.commit()
                
            self._delete_unused_image(image_id[0])
        except ClothingNotFoundError as e:
            raise e
        except Exception as e:
            logger.error(f"An unexpected error occurred while deleting clothing by ID: {e}")
            logger.error(traceback.format_exc())
            raise e
            
clothing_manager = ClothingManager()
from datetime import datetime

from app.core.database import get_session
from app.persistence.schemas.cleanup import FileReference
from app.persistence.schemas.clothing import (
    AffectedOutfitRow,
    ClothingIdRow,
    ClothingIdSeasonRow,
    ClothingIdTagRow,
    ClothingImageIdRow,
    ClothingRow,
    ClothingSeasonRow,
    ClothingTagRow,
)
from app.models.clothing import ClothingSubCategory


# Cleanup helpers

def get_image_ids_for_user(session, user_id: str) -> list[FileReference]:
    """Returns all clothing image IDs owned by a user."""
    return session.select(
        """
        SELECT image_id AS file_id
        FROM clothing
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
        schema_type=FileReference,
    )


def get_all_referenced_image_ids(session) -> list[FileReference]:
    """Returns all clothing image IDs currently referenced (across all users)."""
    return session.select(
        """
        SELECT image_id AS file_id
        FROM clothing
        """,
        {},
        schema_type=FileReference,
    )


# Reads

def get_by_id(user_id: str, clothing_id: str) -> ClothingRow | None:
    """Fetches a single clothing row for a given user."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT clothing_id, is_public, name, category, sub_category, color, warmth_level, description, created_at, user_id, image_id
            FROM clothing
            WHERE clothing_id = :clothing_id AND user_id = :user_id AND deleted_at IS NULL
            """,
            {"clothing_id": clothing_id, "user_id": user_id},
            schema_type=ClothingRow,
        )


def get_seasons_by_clothing_id(clothing_id: str) -> list[ClothingSeasonRow]:
    """Fetches season names attached to a clothing item."""
    with get_session() as session:
        return session.select(
            "SELECT season FROM clothing_seasons WHERE clothing_id = :clothing_id",
            {"clothing_id": clothing_id},
            schema_type=ClothingSeasonRow,
        )


def get_tags_by_clothing_id(clothing_id: str) -> list[ClothingTagRow]:
    """Fetches tag names attached to a clothing item."""
    with get_session() as session:
        return session.select(
            "SELECT tag FROM clothing_tags WHERE clothing_id = :clothing_id",
            {"clothing_id": clothing_id},
            schema_type=ClothingTagRow,
        )


def get_updated_since(user_id: str, updated_since: datetime) -> list[ClothingRow]:
    """Fetches clothes updated since the given timestamp for sync."""
    with get_session() as session:
        return session.select(
            """
            SELECT clothing_id, is_public, name, category, sub_category, color, warmth_level, description, created_at, user_id, image_id
            FROM clothing
            WHERE user_id = :user_id AND updated_at > :updated_since AND deleted_at IS NULL
            ORDER BY updated_at ASC
            """,
            {"user_id": user_id, "updated_since": updated_since},
            schema_type=ClothingRow,
        )


def get_deleted_ids_since(user_id: str, updated_since: datetime) -> list[ClothingIdRow]:
    """Fetches clothing IDs soft-deleted since the given timestamp for sync."""
    with get_session() as session:
        return session.select(
            """
            SELECT clothing_id
            FROM clothing
            WHERE user_id = :user_id AND deleted_at IS NOT NULL AND deleted_at > :updated_since
            """,
            {"user_id": user_id, "updated_since": updated_since},
            schema_type=ClothingIdRow,
        )


def list_for_user(
    user_id: str,
    only_public: bool,
    category: str | None,
    seasons: list[str] | None,
    tags: list[str] | None,
    limit: int,
    offset: int,
) -> list[ClothingRow]:
    """Lists clothes for a user, optionally filtered by category/seasons/tags."""
    where_clauses = ["c.user_id = :user_id", "c.deleted_at IS NULL"]
    params: dict = {"user_id": user_id}

    if only_public:
        where_clauses.append("c.is_public = :is_public")
        params["is_public"] = True

    if category:
        where_clauses.append("c.category = :category")
        params["category"] = category

    if seasons:
        placeholders = []
        for i, season in enumerate(seasons):
            key = f"season_{i}"
            placeholders.append(f":{key}")
            params[key] = season
        where_clauses.append(
            f"EXISTS (SELECT 1 FROM clothing_seasons cs WHERE cs.clothing_id = c.clothing_id AND cs.season IN ({', '.join(placeholders)}))"
        )

    if tags:
        placeholders = []
        for i, tag in enumerate(tags):
            key = f"tag_{i}"
            placeholders.append(f":{key}")
            params[key] = tag
        where_clauses.append(
            f"EXISTS (SELECT 1 FROM clothing_tags ct WHERE ct.clothing_id = c.clothing_id AND ct.tag IN ({', '.join(placeholders)}))"
        )

    params["limit"] = limit
    params["offset"] = offset

    sql = f"""
        SELECT c.clothing_id, c.is_public, c.name, c.category, c.sub_category, c.color, c.warmth_level, c.description, c.created_at, c.user_id, c.image_id
        FROM clothing c
        WHERE {' AND '.join(where_clauses)}
        ORDER BY c.created_at DESC
        LIMIT :limit OFFSET :offset
    """

    with get_session() as session:
        return session.select(sql, params, schema_type=ClothingRow)


def get_seasons_by_clothing_ids(clothing_ids: list[str]) -> list[ClothingIdSeasonRow]:
    """Batched fetch of seasons for many clothing items."""
    if not clothing_ids:
        return []
    placeholders = []
    params: dict = {}
    for i, cid in enumerate(clothing_ids):
        key = f"cid_{i}"
        placeholders.append(f":{key}")
        params[key] = cid
    sql = f"SELECT clothing_id, season FROM clothing_seasons WHERE clothing_id IN ({', '.join(placeholders)})"
    with get_session() as session:
        return session.select(sql, params, schema_type=ClothingIdSeasonRow)


def get_tags_by_clothing_ids(clothing_ids: list[str]) -> list[ClothingIdTagRow]:
    """Batched fetch of tags for many clothing items."""
    if not clothing_ids:
        return []
    placeholders = []
    params: dict = {}
    for i, cid in enumerate(clothing_ids):
        key = f"cid_{i}"
        placeholders.append(f":{key}")
        params[key] = cid
    sql = f"SELECT clothing_id, tag FROM clothing_tags WHERE clothing_id IN ({', '.join(placeholders)})"
    with get_session() as session:
        return session.select(sql, params, schema_type=ClothingIdTagRow)


# Writes (session-parameter — meant for use inside a transaction)

def create(
    session,
    clothing_id: str,
    is_public: bool,
    name: str,
    category: str,
    sub_category: str,
    image_id: str,
    user_id: str,
    color: str,
    warmth_level: int,
    description: str | None,
) -> None:
    """Inserts a new clothing row."""
    session.execute(
        """
        INSERT INTO clothing (clothing_id, is_public, name, category, sub_category, image_id, user_id, color, warmth_level, description)
        VALUES (:clothing_id, :is_public, :name, :category, :sub_category, :image_id, :user_id, :color, :warmth_level, :description)
        """,
        {
            "clothing_id": clothing_id,
            "is_public": is_public,
            "name": name,
            "category": category,
            "sub_category": sub_category,
            "image_id": image_id,
            "user_id": user_id,
            "color": color,
            "warmth_level": warmth_level,
            "description": description,
        },
    )


def add_seasons(session, clothing_id: str, seasons: list[str]) -> None:
    """Inserts season rows for a clothing item."""
    for season in seasons:
        session.execute(
            "INSERT INTO clothing_seasons (clothing_id, season) VALUES (:clothing_id, :season)",
            {"clothing_id": clothing_id, "season": season},
        )


def add_tags(session, clothing_id: str, tags: list[str]) -> None:
    """Inserts tag rows for a clothing item."""
    for tag in tags:
        session.execute(
            "INSERT INTO clothing_tags (clothing_id, tag) VALUES (:clothing_id, :tag)",
            {"clothing_id": clothing_id, "tag": tag},
        )


def remove_seasons(session, clothing_id: str, seasons: list[str]) -> None:
    """Removes specific season rows from a clothing item."""
    if not seasons:
        return
    placeholders = []
    params: dict = {"clothing_id": clothing_id}
    for i, season in enumerate(seasons):
        key = f"season_{i}"
        placeholders.append(f":{key}")
        params[key] = season
    sql = (
        f"DELETE FROM clothing_seasons WHERE clothing_id = :clothing_id AND season IN ({', '.join(placeholders)})"
    )
    session.execute(sql, params)


def remove_tags(session, clothing_id: str, tags: list[str]) -> None:
    """Removes specific tag rows from a clothing item."""
    if not tags:
        return
    placeholders = []
    params: dict = {"clothing_id": clothing_id}
    for i, tag in enumerate(tags):
        key = f"tag_{i}"
        placeholders.append(f":{key}")
        params[key] = tag
    sql = (
        f"DELETE FROM clothing_tags WHERE clothing_id = :clothing_id AND tag IN ({', '.join(placeholders)})"
    )
    session.execute(sql, params)


def get_basic_for_update(session, user_id: str, clothing_id: str) -> ClothingRow | None:
    """Fetches the current clothing row for comparison during update."""
    return session.select_one_or_none(
        """
        SELECT clothing_id, is_public, name, category, sub_category, color, warmth_level, description, created_at, user_id, image_id
        FROM clothing
        WHERE clothing_id = :clothing_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"clothing_id": clothing_id, "user_id": user_id},
        schema_type=ClothingRow,
    )


def get_seasons_in_session(session, clothing_id: str) -> list[ClothingSeasonRow]:
    """Fetches season names attached to a clothing item using an existing session."""
    return session.select(
        "SELECT season FROM clothing_seasons WHERE clothing_id = :clothing_id",
        {"clothing_id": clothing_id},
        schema_type=ClothingSeasonRow,
    )


def get_tags_in_session(session, clothing_id: str) -> list[ClothingTagRow]:
    """Fetches tag names attached to a clothing item using an existing session."""
    return session.select(
        "SELECT tag FROM clothing_tags WHERE clothing_id = :clothing_id",
        {"clothing_id": clothing_id},
        schema_type=ClothingTagRow,
    )


def update_fields(session, clothing_id: str, fields: dict) -> None:
    """Updates a subset of mutable fields on a clothing row."""
    if not fields:
        return

    allowed_fields = {"name", "color", "warmth_level", "image_id", "sub_category", "description"}
    set_clauses = []
    params: dict = {"clothing_id": clothing_id}

    for key, value in fields.items():
        if key not in allowed_fields:
            raise ValueError(f"Unknown clothing field: {key}")

        if key == "sub_category":
            if not isinstance(value, str) and not value.upper() in ClothingSubCategory.__members__:
                raise ValueError(f"Invalid sub category: {value}")

            category = ClothingSubCategory.__members__[value.upper()].category

            set_clauses.append(f"category = :category")
            params["category"] = category

        set_clauses.append(f"{key} = :{key}")
        params[key] = value

    sql = f"UPDATE clothing SET {', '.join(set_clauses)} WHERE clothing_id = :clothing_id"
    session.execute(sql, params)


def get_image_id(session, user_id: str, clothing_id: str) -> ClothingImageIdRow | None:
    """Fetches just the image_id for a clothing item owned by the user."""
    return session.select_one_or_none(
        """
        SELECT image_id
        FROM clothing
        WHERE clothing_id = :clothing_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"clothing_id": clothing_id, "user_id": user_id},
        schema_type=ClothingImageIdRow,
    )


def get_outfits_affected_by_clothing(session, clothing_id: str) -> list[AffectedOutfitRow]:
    """Returns outfit IDs containing a given clothing item along with each outfit's total item count."""
    return session.select(
        """
        SELECT outfit_id, COUNT(*) AS item_count
        FROM outfit_clothing
        WHERE outfit_id IN (SELECT outfit_id FROM outfit_clothing WHERE clothing_id = :clothing_id)
        GROUP BY outfit_id
        """,
        {"clothing_id": clothing_id},
        schema_type=AffectedOutfitRow,
    )


def soft_delete(session, user_id: str, clothing_id: str) -> None:
    """Marks a clothing item as deleted."""
    session.execute(
        """
        UPDATE clothing
        SET deleted_at = NOW()
        WHERE clothing_id = :clothing_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"clothing_id": clothing_id, "user_id": user_id},
    )


def exists_for_user(session, user_id: str, clothing_id: str) -> bool:
    """Checks that a clothing item exists and is owned by the given user (active or not)."""
    row = session.select_one_or_none(
        "SELECT clothing_id FROM clothing WHERE clothing_id = :clothing_id AND user_id = :user_id",
        {"clothing_id": clothing_id, "user_id": user_id},
        schema_type=ClothingIdRow,
    )
    return row is not None


def exists_active_for_user(session, user_id: str, clothing_id: str) -> bool:
    """Checks that a clothing item exists, is owned by the user, and is not soft-deleted."""
    row = session.select_one_or_none(
        """
        SELECT clothing_id FROM clothing
        WHERE clothing_id = :clothing_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"clothing_id": clothing_id, "user_id": user_id},
        schema_type=ClothingIdRow,
    )
    return row is not None

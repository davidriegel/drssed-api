from datetime import datetime

from app.core.database import get_session
from app.persistence.schemas.cleanup import FileReference
from app.persistence.schemas.outfit import (
    OutfitClothingRow,
    OutfitCountRow,
    OutfitIdRow,
    OutfitRow,
    OutfitSeasonRow,
    OutfitTagRow,
)


# Cleanup helpers

def get_outfit_ids_for_user(session, user_id: str) -> list[FileReference]:
    """Returns all outfit IDs owned by a user (used as collage filenames)."""
    return session.select(
        """
        SELECT outfit_id AS file_id
        FROM outfits
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
        schema_type=FileReference,
    )


def get_all_outfit_ids(session) -> list[FileReference]:
    """Returns all outfit IDs (used as collage filenames)."""
    return session.select(
        """
        SELECT outfit_id AS file_id
        FROM outfits
        """,
        {},
        schema_type=FileReference,
    )


# Reads

def get_by_id_for_user(user_id: str, outfit_id: str) -> OutfitRow | None:
    """Fetches a single active outfit row owned by the given user."""
    with get_session() as session:
        return session.select_one_or_none(
            """
            SELECT outfit_id, is_public, is_favorite, name, created_at, updated_at, user_id
            FROM outfits
            WHERE outfit_id = :outfit_id AND user_id = :user_id AND deleted_at IS NULL
            """,
            {"outfit_id": outfit_id, "user_id": user_id},
            schema_type=OutfitRow,
        )


def get_seasons_by_outfit_id(outfit_id: str) -> list[OutfitSeasonRow]:
    """Fetches season names attached to an outfit."""
    with get_session() as session:
        return session.select(
            "SELECT season FROM outfit_seasons WHERE outfit_id = :outfit_id",
            {"outfit_id": outfit_id},
            schema_type=OutfitSeasonRow,
        )


def get_tags_by_outfit_id(outfit_id: str) -> list[OutfitTagRow]:
    """Fetches tag names attached to an outfit."""
    with get_session() as session:
        return session.select(
            "SELECT tag FROM outfit_tags WHERE outfit_id = :outfit_id",
            {"outfit_id": outfit_id},
            schema_type=OutfitTagRow,
        )


def get_clothing_canvas(outfit_id: str) -> list[OutfitClothingRow]:
    """Fetches the canvas placement rows for an outfit, ordered by z-index."""
    with get_session() as session:
        return session.select(
            """
            SELECT clothing_id, position_x, position_y, z_index, scale, rotation
            FROM outfit_clothing
            WHERE outfit_id = :outfit_id
            ORDER BY z_index
            """,
            {"outfit_id": outfit_id},
            schema_type=OutfitClothingRow,
        )


def get_updated_since(user_id: str, updated_since: datetime) -> list[OutfitRow]:
    """Fetches outfits updated since the given timestamp for sync."""
    with get_session() as session:
        return session.select(
            """
            SELECT outfit_id, is_public, is_favorite, name, created_at, updated_at, user_id
            FROM outfits
            WHERE user_id = :user_id AND updated_at > :updated_since AND deleted_at IS NULL
            ORDER BY updated_at ASC
            """,
            {"user_id": user_id, "updated_since": updated_since},
            schema_type=OutfitRow,
        )


def get_deleted_ids_since(user_id: str, updated_since: datetime) -> list[OutfitIdRow]:
    """Fetches outfit IDs soft-deleted since the given timestamp for sync."""
    with get_session() as session:
        return session.select(
            """
            SELECT outfit_id
            FROM outfits
            WHERE user_id = :user_id AND deleted_at IS NOT NULL AND deleted_at > :updated_since
            """,
            {"user_id": user_id, "updated_since": updated_since},
            schema_type=OutfitIdRow,
        )


def list_for_user(
    user_id: str,
    include_private: bool,
    limit: int,
    offset: int,
) -> tuple[list[OutfitRow], int]:
    """Lists outfits for a user, returning the page rows plus total count."""
    conditions = ["user_id = :user_id", "deleted_at IS NULL"]
    params: dict = {"user_id": user_id}

    if not include_private:
        conditions.append("is_public = :is_public")
        params["is_public"] = True

    where_clause = " AND ".join(conditions)

    with get_session() as session:
        count_row = session.select_one_or_none(
            f"SELECT COUNT(*) AS total FROM outfits WHERE {where_clause}",
            params,
            schema_type=OutfitCountRow,
        )
        total = count_row.total if count_row else 0

        list_params = {**params, "limit": limit, "offset": offset}
        rows = session.select(
            f"""
            SELECT outfit_id, is_public, is_favorite, name, created_at, updated_at, user_id
            FROM outfits
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """,
            list_params,
            schema_type=OutfitRow,
        )

    return rows, total


# Writes (session-parameter — meant for use inside a transaction)

def create(
    session,
    outfit_id: str,
    is_public: bool,
    is_favorite: bool,
    name: str,
    user_id: str
) -> None:
    """Inserts a new outfit row."""
    session.execute(
        """
        INSERT INTO outfits (outfit_id, is_public, is_favorite, name, user_id)
        VALUES (:outfit_id, :is_public, :is_favorite, :name, :user_id)
        """,
        {
            "outfit_id": outfit_id,
            "is_public": is_public,
            "is_favorite": is_favorite,
            "name": name,
            "user_id": user_id
        },
    )


def add_seasons(session, outfit_id: str, seasons: list[str]) -> None:
    """Inserts season rows for an outfit."""
    for season in seasons:
        session.execute(
            "INSERT INTO outfit_seasons (outfit_id, season) VALUES (:outfit_id, :season)",
            {"outfit_id": outfit_id, "season": season},
        )


def add_tags(session, outfit_id: str, tags: list[str]) -> None:
    """Inserts tag rows for an outfit."""
    for tag in tags:
        session.execute(
            "INSERT INTO outfit_tags (outfit_id, tag) VALUES (:outfit_id, :tag)",
            {"outfit_id": outfit_id, "tag": tag},
        )


def add_clothing_placements(
    session,
    outfit_id: str,
    placements: list[dict],
) -> None:
    """Inserts canvas placement rows for an outfit.

    Each placement dict must have: clothing_id, x, y, z, scale, rotation.
    """
    for placement in placements:
        session.execute(
            """
            INSERT INTO outfit_clothing (outfit_id, clothing_id, position_x, position_y, z_index, scale, rotation)
            VALUES (:outfit_id, :clothing_id, :position_x, :position_y, :z_index, :scale, :rotation)
            """,
            {
                "outfit_id": outfit_id,
                "clothing_id": placement["clothing_id"],
                "position_x": placement["x"],
                "position_y": placement["y"],
                "z_index": placement["z"],
                "scale": placement["scale"],
                "rotation": placement["rotation"],
            },
        )


def remove_seasons(session, outfit_id: str, seasons: list[str]) -> None:
    """Removes specific season rows from an outfit."""
    if not seasons:
        return
    placeholders = []
    params: dict = {"outfit_id": outfit_id}
    for i, season in enumerate(seasons):
        key = f"season_{i}"
        placeholders.append(f":{key}")
        params[key] = season
    sql = (
        f"DELETE FROM outfit_seasons WHERE outfit_id = :outfit_id AND season IN ({', '.join(placeholders)})"
    )
    session.execute(sql, params)


def remove_tags(session, outfit_id: str, tags: list[str]) -> None:
    """Removes specific tag rows from an outfit."""
    if not tags:
        return
    placeholders = []
    params: dict = {"outfit_id": outfit_id}
    for i, tag in enumerate(tags):
        key = f"tag_{i}"
        placeholders.append(f":{key}")
        params[key] = tag
    sql = (
        f"DELETE FROM outfit_tags WHERE outfit_id = :outfit_id AND tag IN ({', '.join(placeholders)})"
    )
    session.execute(sql, params)


def clear_clothing_placements(session, outfit_id: str) -> None:
    """Removes all clothing placement rows for an outfit."""
    session.execute(
        "DELETE FROM outfit_clothing WHERE outfit_id = :outfit_id",
        {"outfit_id": outfit_id},
    )


def remove_clothing_from_outfits(session, clothing_id: str) -> None:
    """Removes a clothing item from every outfit it appears in."""
    session.execute(
        "DELETE FROM outfit_clothing WHERE clothing_id = :clothing_id",
        {"clothing_id": clothing_id},
    )


def get_basic_for_patch(session, user_id: str, outfit_id: str) -> OutfitRow | None:
    """Fetches the current outfit row for comparison during patch."""
    return session.select_one_or_none(
        """
        SELECT outfit_id, is_public, is_favorite, name, created_at, updated_at, user_id
        FROM outfits
        WHERE outfit_id = :outfit_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"outfit_id": outfit_id, "user_id": user_id},
        schema_type=OutfitRow,
    )


def get_seasons_in_session(session, outfit_id: str) -> list[OutfitSeasonRow]:
    """Fetches season names attached to an outfit using an existing session."""
    return session.select(
        "SELECT season FROM outfit_seasons WHERE outfit_id = :outfit_id",
        {"outfit_id": outfit_id},
        schema_type=OutfitSeasonRow,
    )


def get_tags_in_session(session, outfit_id: str) -> list[OutfitTagRow]:
    """Fetches tag names attached to an outfit using an existing session."""
    return session.select(
        "SELECT tag FROM outfit_tags WHERE outfit_id = :outfit_id",
        {"outfit_id": outfit_id},
        schema_type=OutfitTagRow,
    )


def update_fields(session, outfit_id: str, fields: dict) -> None:
    """Updates a subset of mutable fields on an outfit row."""
    if not fields:
        return

    allowed_fields = {"name", "is_public", "is_favorite"}
    set_clauses = []
    params: dict = {"outfit_id": outfit_id}

    for key, value in fields.items():
        if key not in allowed_fields:
            raise ValueError(f"Unknown outfit field: {key}")
        set_clauses.append(f"{key} = :{key}")
        params[key] = value

    sql = f"UPDATE outfits SET {', '.join(set_clauses)} WHERE outfit_id = :outfit_id"
    session.execute(sql, params)


def soft_delete_by_id(session, outfit_id: str) -> None:
    """Marks an outfit as deleted (no user check — used in cascading deletes)."""
    session.execute(
        """
        UPDATE outfits
        SET deleted_at = NOW()
        WHERE outfit_id = :outfit_id AND deleted_at IS NULL
        """,
        {"outfit_id": outfit_id},
    )


def soft_delete_for_user(session, user_id: str, outfit_id: str) -> int:
    """Marks an outfit as deleted for a given user. Returns affected row count."""
    result = session.execute(
        """
        UPDATE outfits
        SET deleted_at = NOW()
        WHERE outfit_id = :outfit_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"outfit_id": outfit_id, "user_id": user_id},
    )
    return getattr(result, "rowcount", 0)

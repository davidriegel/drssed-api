from app.persistence.schemas.cleanup import FileReference


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
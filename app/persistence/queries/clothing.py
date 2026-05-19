from app.persistence.schemas.cleanup import FileReference


def get_image_ids_for_user(session, user_id: str) -> list[FileReference]:
    """Returns all clothing image IDs owned by a user."""
    return session.select(
        """
        SELECT image_id AS file_id
        FROM clothing
        WHERE user_id = :user_id AND image_id IS NOT NULL
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
        WHERE image_id IS NOT NULL
        """,
        {},
        schema_type=FileReference,
    )
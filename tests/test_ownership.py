import uuid

from tests.conftest import needs_database

pytestmark = needs_database


def _create_outfit(session, user_id: str) -> str:
    outfit_id = str(uuid.uuid4())
    session.execute(
        "INSERT INTO outfits (outfit_id, user_id, name) VALUES (:o, :u, 'Outfit')",
        {"o": outfit_id, "u": user_id},
    )
    return outfit_id


def _create_clothing(session, user_id: str, deleted: bool = False) -> str:
    clothing_id = str(uuid.uuid4())
    session.execute(
        f"""
        INSERT INTO clothing (clothing_id, user_id, name, category, sub_category,
                              image_id, warmth_level, color{", deleted_at" if deleted else ""})
        VALUES (:c, :u, 'Item', 'TOP', 'SWEATER', :i, 3, '#FFFFFF'{", NOW()" if deleted else ""})
        """,
        {"c": clothing_id, "u": user_id, "i": str(uuid.uuid4())},
    )
    return clothing_id


def test_soft_delete_rejects_a_foreign_outfit(user_ids):
    from app.core.database import get_session
    from app.persistence.queries import outfit as outfit_queries

    owner, stranger = user_ids

    with get_session() as session:
        outfit_id = _create_outfit(session, owner)

    with get_session() as session:
        assert (
            outfit_queries.soft_delete_for_user(session, stranger, outfit_id) is False
        )

    with get_session() as session:
        assert outfit_queries.soft_delete_for_user(session, owner, outfit_id) is True

    with get_session() as session:
        assert outfit_queries.soft_delete_for_user(session, owner, outfit_id) is False


def test_scene_lookup_skips_foreign_and_deleted_items(user_ids):
    from app.core.database import get_session
    from app.persistence.queries import clothing as clothing_queries

    owner, stranger = user_ids

    with get_session() as session:
        own = _create_clothing(session, owner)
        gone = _create_clothing(session, owner, deleted=True)
        foreign = _create_clothing(session, stranger)

    with get_session() as session:
        found = {
            row.clothing_id
            for row in clothing_queries.get_active_image_ids_for_user(
                session, owner, [own, gone, foreign]
            )
        }

    assert found == {own}

import uuid

import pytest

from tests.conftest import needs_database

pytestmark = needs_database


def test_seasons_round_trip_through_the_python_enum(user_ids):
    from app.core.database import get_session
    from app.models.season import Season
    from app.persistence.queries import clothing as clothing_queries

    owner, _ = user_ids
    clothing_id = str(uuid.uuid4())

    with get_session() as session:
        session.execute(
            """
            INSERT INTO clothing (clothing_id, user_id, name, category, sub_category,
                                  image_id, warmth_level, color)
            VALUES (:c, :u, 'Item', 'TOP', 'SWEATER', :i, 3, '#FFFFFF')
            """,
            {"c": clothing_id, "u": owner, "i": str(uuid.uuid4())},
        )
        clothing_queries.add_seasons(session, clothing_id, ["SPRING", "WINTER"])

    stored = {
        row.season for row in clothing_queries.get_seasons_by_clothing_id(clothing_id)
    }

    assert stored == {"SPRING", "WINTER"}
    assert {Season[name] for name in stored} == {Season.SPRING, Season.WINTER}


def test_duplicate_username_is_rejected_by_the_database():
    from sqlspec.exceptions import UniqueViolationError

    from app.core.database import get_session
    from app.persistence.queries import user as user_queries
    from app.persistence.schemas.user import UserCreate

    username = f"dup{uuid.uuid4().hex[:8]}"
    first, second = str(uuid.uuid4()), str(uuid.uuid4())

    try:
        user_queries.create(
            UserCreate(user_id=first, is_guest=False, username=username)
        )

        with pytest.raises(UniqueViolationError):
            user_queries.create(
                UserCreate(user_id=second, is_guest=False, username=username)
            )
    finally:
        with get_session() as session:
            session.execute(
                "DELETE FROM users WHERE user_id IN (:a, :b)", {"a": first, "b": second}
            )


def test_new_users_get_a_last_active_timestamp():
    from app.core.database import get_session
    from app.persistence.queries import user as user_queries
    from app.persistence.schemas.user import UserCreate

    user_id = str(uuid.uuid4())

    try:
        user_queries.create(UserCreate(user_id=user_id, is_guest=True))
        profile = user_queries.get_profile_by_id(user_id)

        assert profile is not None
        assert profile.last_active_at is not None
    finally:
        with get_session() as session:
            session.execute("DELETE FROM users WHERE user_id = :u", {"u": user_id})


def test_guest_without_email_is_not_found_instead_of_crashing():
    from app.core.database import get_session
    from app.persistence.queries import user as user_queries
    from app.persistence.schemas.user import UserCreate

    user_id = str(uuid.uuid4())

    try:
        user_queries.create(UserCreate(user_id=user_id, is_guest=True))
        status = user_queries.get_email_verification_status(user_id)

        assert status is not None
        assert status.email is None
    finally:
        with get_session() as session:
            session.execute("DELETE FROM users WHERE user_id = :u", {"u": user_id})

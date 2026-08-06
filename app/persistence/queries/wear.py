from datetime import date, datetime, timedelta

from app.core.database import get_session
from app.persistence.schemas.clothing import ClothingIdRow
from app.persistence.schemas.wear import (
    WearBucketRow,
    WearClothingCountRow,
    WearClothingRow,
    WearCountRow,
    WearDateRow,
    WearIdRow,
    WearOutfitCountRow,
    WearRow,
    WearSummaryRow,
    WearWeekdayRow,
    WearWithOutfitRow,
)

WEAR_COLUMNS = """
    w.wear_id, w.user_id, w.outfit_id, w.worn_on, w.feels_like, w.temperature,
    w.weather, w.occasion, w.rating, w.note, w.created_at, w.updated_at
"""


def _range_conditions(
    date_from: date | None, date_to: date | None
) -> tuple[list[str], dict]:
    """Builds the shared 'worn_on within range' conditions.

    Both bounds are inclusive days, so date_to is compared against the start of
    the following day.
    """
    conditions: list[str] = []
    params: dict = {}

    if date_from is not None:
        conditions.append("w.worn_on >= :date_from")
        params["date_from"] = datetime.combine(date_from, datetime.min.time())

    if date_to is not None:
        conditions.append("w.worn_on < :date_to")
        params["date_to"] = datetime.combine(
            date_to + timedelta(days=1), datetime.min.time()
        )

    return conditions, params


# Reads


def get_by_id_for_user(user_id: str, wear_id: str) -> WearWithOutfitRow | None:
    """Fetches a single wear entry owned by the given user, including the outfit name."""
    with get_session() as session:
        return session.select_one_or_none(
            f"""
            SELECT {WEAR_COLUMNS}, o.name AS outfit_name
            FROM outfit_wears w
            JOIN outfits o ON o.outfit_id = w.outfit_id
            WHERE w.wear_id = :wear_id AND w.user_id = :user_id AND w.deleted_at IS NULL
            """,
            {"wear_id": wear_id, "user_id": user_id},
            schema_type=WearWithOutfitRow,
        )


def get_clothing_ids_by_wear_ids(wear_ids: list[str]) -> list[WearClothingRow]:
    """Batched fetch of the clothing snapshot for many wear entries."""
    if not wear_ids:
        return []

    placeholders = []
    params: dict = {}
    for i, wear_id in enumerate(wear_ids):
        key = f"wear_{i}"
        placeholders.append(f":{key}")
        params[key] = wear_id

    sql = f"""
        SELECT wear_id, clothing_id
        FROM outfit_wear_clothing
        WHERE wear_id IN ({", ".join(placeholders)})
    """

    with get_session() as session:
        return session.select(sql, params, schema_type=WearClothingRow)


def list_for_user(
    user_id: str,
    date_from: date | None,
    date_to: date | None,
    outfit_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[WearWithOutfitRow], int]:
    """Lists wear entries for a user, returning the page rows plus total count."""
    conditions = ["w.user_id = :user_id", "w.deleted_at IS NULL"]
    params: dict = {"user_id": user_id}

    range_conditions, range_params = _range_conditions(date_from, date_to)
    conditions.extend(range_conditions)
    params.update(range_params)

    if outfit_id:
        conditions.append("w.outfit_id = :outfit_id")
        params["outfit_id"] = outfit_id

    where_clause = " AND ".join(conditions)

    with get_session() as session:
        count_row = session.select_one_or_none(
            f"SELECT COUNT(*) AS total FROM outfit_wears w WHERE {where_clause}",
            params,
            schema_type=WearCountRow,
        )
        total = count_row.total if count_row else 0

        rows = session.select(
            f"""
            SELECT {WEAR_COLUMNS}, o.name AS outfit_name
            FROM outfit_wears w
            JOIN outfits o ON o.outfit_id = w.outfit_id
            WHERE {where_clause}
            ORDER BY w.worn_on DESC
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": limit, "offset": offset},
            schema_type=WearWithOutfitRow,
        )

    return rows, total


def get_updated_since(user_id: str, updated_since: datetime) -> list[WearWithOutfitRow]:
    """Fetches wear entries updated since the given timestamp for sync."""
    with get_session() as session:
        return session.select(
            f"""
            SELECT {WEAR_COLUMNS}, o.name AS outfit_name
            FROM outfit_wears w
            JOIN outfits o ON o.outfit_id = w.outfit_id
            WHERE w.user_id = :user_id AND w.updated_at > :updated_since AND w.deleted_at IS NULL
            ORDER BY w.updated_at ASC
            """,
            {"user_id": user_id, "updated_since": updated_since},
            schema_type=WearWithOutfitRow,
        )


def get_deleted_ids_since(user_id: str, updated_since: datetime) -> list[WearIdRow]:
    """Fetches wear IDs soft-deleted since the given timestamp for sync."""
    with get_session() as session:
        return session.select(
            """
            SELECT wear_id
            FROM outfit_wears
            WHERE user_id = :user_id AND deleted_at IS NOT NULL AND deleted_at > :updated_since
            """,
            {"user_id": user_id, "updated_since": updated_since},
            schema_type=WearIdRow,
        )


# Stats


def get_summary(
    user_id: str, date_from: date | None, date_to: date | None
) -> WearSummaryRow | None:
    """Fetches the headline wear totals for a user within an optional date range."""
    conditions = ["w.user_id = :user_id", "w.deleted_at IS NULL"]
    params: dict = {"user_id": user_id}

    range_conditions, range_params = _range_conditions(date_from, date_to)
    conditions.extend(range_conditions)
    params.update(range_params)

    with get_session() as session:
        return session.select_one_or_none(
            f"""
            SELECT
                COUNT(*) AS total_wears,
                COUNT(DISTINCT w.outfit_id) AS distinct_outfits,
                COUNT(DISTINCT DATE(w.worn_on)) AS days_logged,
                AVG(w.rating) AS average_rating,
                MAX(w.worn_on) AS last_worn_on
            FROM outfit_wears w
            WHERE {" AND ".join(conditions)}
            """,
            params,
            schema_type=WearSummaryRow,
        )


def get_worn_dates(
    user_id: str, date_from: date | None, date_to: date | None
) -> list[WearDateRow]:
    """Fetches the distinct days a user logged a wear on, newest first."""
    conditions = ["w.user_id = :user_id", "w.deleted_at IS NULL"]
    params: dict = {"user_id": user_id}

    range_conditions, range_params = _range_conditions(date_from, date_to)
    conditions.extend(range_conditions)
    params.update(range_params)

    with get_session() as session:
        return session.select(
            f"""
            SELECT DISTINCT DATE(w.worn_on) AS worn_date
            FROM outfit_wears w
            WHERE {" AND ".join(conditions)}
            ORDER BY worn_date DESC
            """,
            params,
            schema_type=WearDateRow,
        )


def get_top_outfits(
    user_id: str, date_from: date | None, date_to: date | None, limit: int
) -> list[WearOutfitCountRow]:
    """Fetches the most frequently worn outfits of a user."""
    conditions = ["w.user_id = :user_id", "w.deleted_at IS NULL"]
    params: dict = {"user_id": user_id, "limit": limit}

    range_conditions, range_params = _range_conditions(date_from, date_to)
    conditions.extend(range_conditions)
    params.update(range_params)

    with get_session() as session:
        return session.select(
            f"""
            SELECT w.outfit_id, o.name, COUNT(*) AS wear_count, MAX(w.worn_on) AS last_worn_on
            FROM outfit_wears w
            JOIN outfits o ON o.outfit_id = w.outfit_id
            WHERE {" AND ".join(conditions)}
            GROUP BY w.outfit_id, o.name
            ORDER BY wear_count DESC, last_worn_on DESC
            LIMIT :limit
            """,
            params,
            schema_type=WearOutfitCountRow,
        )


def get_counts_by_weekday(
    user_id: str, date_from: date | None, date_to: date | None
) -> list[WearWeekdayRow]:
    """Counts wears per weekday (0 = Monday ... 6 = Sunday)."""
    conditions = ["w.user_id = :user_id", "w.deleted_at IS NULL"]
    params: dict = {"user_id": user_id}

    range_conditions, range_params = _range_conditions(date_from, date_to)
    conditions.extend(range_conditions)
    params.update(range_params)

    with get_session() as session:
        return session.select(
            f"""
            SELECT WEEKDAY(w.worn_on) AS weekday, COUNT(*) AS wear_count
            FROM outfit_wears w
            WHERE {" AND ".join(conditions)}
            GROUP BY weekday
            """,
            params,
            schema_type=WearWeekdayRow,
        )


def get_counts_by_column(
    user_id: str, column: str, date_from: date | None, date_to: date | None
) -> list[WearBucketRow]:
    """Counts wears grouped by a single low-cardinality wear column."""
    allowed_columns = {"weather", "occasion"}
    if column not in allowed_columns:
        raise ValueError(f"Cannot group wears by column: {column}")

    conditions = [
        "w.user_id = :user_id",
        "w.deleted_at IS NULL",
        f"w.{column} IS NOT NULL",
    ]
    params: dict = {"user_id": user_id}

    range_conditions, range_params = _range_conditions(date_from, date_to)
    conditions.extend(range_conditions)
    params.update(range_params)

    with get_session() as session:
        return session.select(
            f"""
            SELECT w.{column} AS bucket, COUNT(*) AS wear_count
            FROM outfit_wears w
            WHERE {" AND ".join(conditions)}
            GROUP BY bucket
            ORDER BY wear_count DESC
            """,
            params,
            schema_type=WearBucketRow,
        )


def get_clothing_wear_counts(
    user_id: str,
    least_worn_first: bool,
    limit: int,
    offset: int,
) -> tuple[list[WearClothingCountRow], int]:
    """Counts wears per clothing item, including items that were never worn."""
    order_clause = (
        "wear_count ASC, c.created_at ASC"
        if least_worn_first
        else "wear_count DESC, last_worn_on DESC"
    )
    params: dict = {"user_id": user_id}

    with get_session() as session:
        count_row = session.select_one_or_none(
            """
            SELECT COUNT(*) AS total
            FROM clothing c
            WHERE c.user_id = :user_id AND c.deleted_at IS NULL
            """,
            params,
            schema_type=WearCountRow,
        )
        total = count_row.total if count_row else 0

        rows = session.select(
            f"""
            SELECT
                c.clothing_id, c.name, c.category, c.sub_category, c.image_id,
                COUNT(wc.wear_id) AS wear_count,
                MAX(w.worn_on) AS last_worn_on
            FROM clothing c
            LEFT JOIN outfit_wear_clothing wc ON wc.clothing_id = c.clothing_id
            LEFT JOIN outfit_wears w ON w.wear_id = wc.wear_id AND w.deleted_at IS NULL
            WHERE c.user_id = :user_id AND c.deleted_at IS NULL
            GROUP BY c.clothing_id, c.name, c.category, c.sub_category, c.image_id, c.created_at
            ORDER BY {order_clause}
            LIMIT :limit OFFSET :offset
            """,
            {**params, "limit": limit, "offset": offset},
            schema_type=WearClothingCountRow,
        )

    return rows, total


# Writes (session-parameter — meant for use inside a transaction)


def create(
    session,
    wear_id: str,
    user_id: str,
    outfit_id: str,
    worn_on: datetime,
    feels_like: float | None,
    temperature: float | None,
    weather: str | None,
    occasion: str | None,
    rating: int | None,
    note: str | None,
) -> None:
    """Inserts a new wear entry."""
    session.execute(
        """
        INSERT INTO outfit_wears (
            wear_id, user_id, outfit_id, worn_on, feels_like, temperature,
            weather, occasion, rating, note
        )
        VALUES (
            :wear_id, :user_id, :outfit_id, :worn_on, :feels_like, :temperature,
            :weather, :occasion, :rating, :note
        )
        """,
        {
            "wear_id": wear_id,
            "user_id": user_id,
            "outfit_id": outfit_id,
            "worn_on": worn_on,
            "feels_like": feels_like,
            "temperature": temperature,
            "weather": weather,
            "occasion": occasion,
            "rating": rating,
            "note": note,
        },
    )


def add_clothing_snapshot(session, wear_id: str, clothing_ids: list[str]) -> None:
    """Stores which clothing items were part of the outfit at the time of wearing."""
    for clothing_id in clothing_ids:
        session.execute(
            """
            INSERT INTO outfit_wear_clothing (wear_id, clothing_id)
            VALUES (:wear_id, :clothing_id)
            """,
            {"wear_id": wear_id, "clothing_id": clothing_id},
        )


def get_outfit_clothing_ids(session, outfit_id: str) -> list[ClothingIdRow]:
    """Fetches the clothing IDs currently placed on an outfit."""
    return session.select(
        """
        SELECT clothing_id
        FROM outfit_clothing
        WHERE outfit_id = :outfit_id
        """,
        {"outfit_id": outfit_id},
        schema_type=ClothingIdRow,
    )


def get_by_id_in_session(session, user_id: str, wear_id: str) -> WearRow | None:
    """Fetches the current wear row for comparison during patch or delete."""
    return session.select_one_or_none(
        f"""
        SELECT {WEAR_COLUMNS}
        FROM outfit_wears w
        WHERE w.wear_id = :wear_id AND w.user_id = :user_id AND w.deleted_at IS NULL
        """,
        {"wear_id": wear_id, "user_id": user_id},
        schema_type=WearRow,
    )


def exists_for_outfit_on_day(
    session, user_id: str, outfit_id: str, worn_date: date
) -> bool:
    """Checks whether the same outfit is already logged for that day."""
    row = session.select_one_or_none(
        """
        SELECT wear_id
        FROM outfit_wears
        WHERE user_id = :user_id
          AND outfit_id = :outfit_id
          AND active_worn_date = :worn_date
        """,
        {"user_id": user_id, "outfit_id": outfit_id, "worn_date": worn_date},
        schema_type=WearIdRow,
    )
    return row is not None


def update_fields(session, wear_id: str, fields: dict) -> None:
    """Updates a subset of mutable fields on a wear entry."""
    if not fields:
        return

    allowed_fields = {
        "worn_on",
        "feels_like",
        "temperature",
        "weather",
        "occasion",
        "rating",
        "note",
    }
    set_clauses = []
    params: dict = {"wear_id": wear_id}

    for key, value in fields.items():
        if key not in allowed_fields:
            raise ValueError(f"Unknown wear field: {key}")
        set_clauses.append(f"{key} = :{key}")
        params[key] = value

    sql = f"UPDATE outfit_wears SET {', '.join(set_clauses)} WHERE wear_id = :wear_id"
    session.execute(sql, params)


def soft_delete_for_user(session, user_id: str, wear_id: str) -> bool:
    """Marks a wear entry as deleted for a given user. Returns whether a row matched."""
    result = session.execute(
        """
        UPDATE outfit_wears
        SET deleted_at = NOW()
        WHERE wear_id = :wear_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"wear_id": wear_id, "user_id": user_id},
    )

    return result.rows_affected > 0


def soft_delete_for_outfit(session, user_id: str, outfit_id: str) -> bool:
    """Marks a wear entry as deleted for a given user. Returns success or failure."""
    result = session.execute(
        """
        UPDATE outfit_wears SET deleted_at = NOW()
        WHERE outfit_id = :outfit_id AND user_id = :user_id AND deleted_at IS NULL
        """,
        {"outfit_id": outfit_id, "user_id": user_id},
    )

    return result.is_success()

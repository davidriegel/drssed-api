from app.core.database import get_session
from app.persistence.schemas.recommendation import RecommendationCandidateRow

# Reads


def _season_placeholders(seasons: list[str]) -> tuple[str, dict]:
    """Builds the placeholder list and params for a 'season IN (...)' filter."""
    placeholders = []
    params: dict = {}

    for i, season in enumerate(seasons):
        key = f"season_{i}"
        placeholders.append(f":{key}")
        params[key] = season

    return ", ".join(placeholders), params


def get_candidates(
    user_id: str,
    target: int,
    tolerance: int | None,
    cooldown_days: int,
    limit: int,
    seasons: list[str] | None = None,
) -> list[RecommendationCandidateRow]:
    """Fetches outfits of a user whose warmth level suits the target warmth.

    The warmth level of an outfit is the maximum warmth of the clothing items
    currently placed on it. A tolerance of None drops the warmth filter and
    orders by how close an outfit is to the target instead, a cooldown of 0
    days drops the 'recently worn' exclusion.

    `seasons` ranks rather than filters: an outfit the user labelled for one of
    them comes first, an unlabelled outfit stays neutral behind it, and one
    labelled for a different time of year comes last. Filtering on it would
    throw away candidates the warmth match already vouched for.
    """
    conditions = [
        "o.user_id = :user_id",
        "o.deleted_at IS NULL",
        "c.deleted_at IS NULL",
    ]
    params: dict = {"user_id": user_id, "target": target, "limit": limit}

    if cooldown_days > 0:
        conditions.append(
            """NOT EXISTS (
                SELECT 1 FROM outfit_wears w
                WHERE w.outfit_id = o.outfit_id
                  AND w.user_id = :user_id
                  AND w.deleted_at IS NULL
                  AND w.worn_on >= (CURRENT_DATE - INTERVAL :cooldown_days DAY)
            )"""
        )
        params["cooldown_days"] = cooldown_days

    if tolerance is not None:
        having_clause = "HAVING ABS(MAX(c.warmth_level) - :target) <= :tolerance"
        warmth_order = "RAND()"
        params["tolerance"] = tolerance
    else:
        having_clause = ""
        warmth_order = "ABS(MAX(c.warmth_level) - :target), RAND()"

    # 2 = labelled for the time of year, 1 = not labelled at all, 0 = labelled for another.
    if seasons:
        placeholders, season_params = _season_placeholders(seasons)
        params.update(season_params)
        season_rank = f"""
            CASE
                WHEN SUM(os.season IN ({placeholders})) > 0 THEN 2
                WHEN COUNT(os.season) = 0 THEN 1
                ELSE 0
            END DESC,
        """
    else:
        season_rank = ""

    with get_session() as session:
        return session.select(
            f"""
            SELECT o.outfit_id, MAX(c.warmth_level) AS warmth_level
            FROM outfits o
            JOIN outfit_clothing oc ON oc.outfit_id = o.outfit_id
            JOIN clothing c ON c.clothing_id = oc.clothing_id
            LEFT JOIN outfit_seasons os ON os.outfit_id = o.outfit_id
            WHERE {" AND ".join(conditions)}
            GROUP BY o.outfit_id
            {having_clause}
            ORDER BY {season_rank} {warmth_order}
            LIMIT :limit
            """,
            params,
            schema_type=RecommendationCandidateRow,
        )

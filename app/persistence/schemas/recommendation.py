from pydantic import BaseModel, ConfigDict


class RecommendationCandidateRow(BaseModel):
    """An outfit that matches the requested warmth, with its own warmth level."""

    model_config = ConfigDict(frozen=True)

    outfit_id: str
    warmth_level: int

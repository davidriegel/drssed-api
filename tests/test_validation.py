import pytest

from app.models.season import Season
from app.persistence.queries import clothing as clothing_queries
from app.services.recommendation import plausible_seasons, target_warmth
from app.services.wear import _parse_rating, _parse_temperature, _parse_worn_on
from app.utils.exceptions import WearRatingInvalidError, WearTemperatureInvalidError


@pytest.mark.parametrize("value", [123, None, ["SWEATER"], "BANANE"])
def test_update_fields_rejects_invalid_sub_categories(value):
    with pytest.raises(ValueError):
        clothing_queries.update_fields(None, "some-id", {"sub_category": value})


def test_update_fields_rejects_unknown_columns():
    with pytest.raises(ValueError):
        clothing_queries.update_fields(None, "some-id", {"user_id": "somebody-else"})


@pytest.mark.parametrize("value", [True, "20", 200.0, -200.0])
def test_temperature_rejects_non_numeric_and_out_of_range(value):
    with pytest.raises(WearTemperatureInvalidError):
        _parse_temperature(value)


def test_temperature_treats_none_as_not_provided():
    assert _parse_temperature(None) is None


@pytest.mark.parametrize("value", [0, 6, True, "5"])
def test_rating_rejects_values_outside_one_to_five(value):
    with pytest.raises(WearRatingInvalidError):
        _parse_rating(value)


def test_worn_on_rejects_a_date_too_far_in_the_future():
    from app.utils.exceptions import WearWornOnInFutureError

    with pytest.raises(WearWornOnInFutureError):
        _parse_worn_on("2999-01-01")


def test_warmth_scale_is_monotonic_in_temperature():
    warmths = [target_warmth(t) for t in (25, 18, 10, 3, -10)]

    assert warmths == sorted(warmths)
    assert set(warmths) <= {1, 2, 3, 4, 5}


@pytest.mark.parametrize("feels_like", [-20, 0, 8, 15, 25])
def test_plausible_seasons_are_always_valid_season_names(feels_like):
    for name in plausible_seasons(feels_like):
        assert Season(name)

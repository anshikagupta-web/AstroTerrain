import pytest
from pydantic import ValidationError

from app.schemas.search import AnalogSearchRequest, AnalogSiteResult


def test_constraints_are_optional():
    req = AnalogSearchRequest.model_validate(
        {
            "target_planet": "mars",
            "target_site_id": "mars_jezero",
            "weights": {"topography": 0.4, "geochemistry": 0.4, "climate": 0.2},
        }
    )
    assert req.constraints is None


def test_coordinates_are_bounded():
    with pytest.raises(ValidationError):
        AnalogSiteResult.model_validate(
            {
                "site_id": "test",
                "name": "test",
                "country": "test",
                "coordinates": {"lat": 91, "lng": 0},
                "similarity_score": 50,
                "breakdown": {"topography_match": 50, "geochemistry_match": 50, "climate_match": 50},
                "metadata": {"elevation_m": 0, "primary_rock": "test", "accessibility_rating": "test"},
            }
        )

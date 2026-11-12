import pytest
from pydantic import ValidationError
from app.schemas.search import AnalogSearchRequest, SearchWeights

def test_default_search_request_is_valid():
    req = AnalogSearchRequest(target_planet="moon", target_site_id="shackleton-crater")
    assert req.weights.topography == .4
    assert req.constraints.limit == 20

def test_zero_weights_are_rejected():
    with pytest.raises(ValidationError):
        SearchWeights(topography=0, geochemistry=0, climate=0)

def test_unknown_planet_is_rejected():
    with pytest.raises(ValidationError):
        AnalogSearchRequest(target_planet="venus", target_site_id="x")

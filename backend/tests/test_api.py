"""Contract tests use fake repositories: no Docker/PostGIS needed to run pytest."""

import pytest
from fastapi.testclient import TestClient

from app.db.repository import TargetRecord, get_repository
from app.main import app
from app.schemas.search import AnalogSiteResult
from app.services.scoring import get_scoring_engine


class FakeRepository:
    def __init__(self, has_tiles=False):
        self.has_tiles = has_tiles

    async def get_target(self, target_id):
        targets = {
            "moon_shackleton": TargetRecord("moon_shackleton", "Shackleton Crater", "moon"),
            "mars_jezero": TargetRecord("mars_jezero", "Jezero Crater", "mars"),
        }
        return targets.get(target_id)

    async def has_earth_tiles(self):
        return self.has_tiles

    async def list_targets(self):
        return [{"id": "moon_shackleton", "name": "Shackleton Crater", "body": "moon"}]

    async def earth_geojson(self, limit):
        return {"type": "FeatureCollection", "features": []}


class TestFixtureScorer:
    """This is TEST DATA only. It is not a real geographic/scientific match."""

    async def score(self, request, target, repository):
        return [
            AnalogSiteResult.model_validate(
                {
                    "site_id": "fixture_site",
                    "name": "Synthetic Test Site",
                    "country": "Testland",
                    "coordinates": {"lat": 12.5, "lng": 42.0},
                    "similarity_score": 75.5,
                    "breakdown": {
                        "topography_match": 90,
                        "geochemistry_match": 70,
                        "climate_match": 50,
                    },
                    "metadata": {
                        "elevation_m": 1200,
                        "primary_rock": "synthetic",
                        "accessibility_rating": "synthetic",
                    },
                }
            )
        ]


@pytest.fixture(autouse=True)
def clear_dependencies():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    app.dependency_overrides[get_repository] = lambda: FakeRepository()
    with TestClient(app) as c:
        yield c


def payload(**changes):
    request = {
        "target_planet": "moon",
        "target_site_id": "moon_shackleton",
        "weights": {"topography": 0.4, "geochemistry": 0.4, "climate": 0.2},
        "constraints": {"subterranean_only": False, "min_similarity": 50.0},
    }
    request.update(changes)
    return request


def test_liveness(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_target_list(client):
    response = client.get("/api/v1/targets")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "moon_shackleton"


def test_empty_search_returns_exact_contract(client):
    response = client.post("/api/v1/analogs/search", json=payload())
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "target_site_name": "Shackleton Crater",
        "results_count": 0,
        "analogs": [],
    }


def test_missing_target_returns_404(client):
    response = client.post("/api/v1/analogs/search", json=payload(target_site_id="unknown"))
    assert response.status_code == 404


def test_wrong_planet_returns_400(client):
    response = client.post("/api/v1/analogs/search", json=payload(target_planet="mars"))
    assert response.status_code == 400


@pytest.mark.parametrize(
    "bad_weights",
    [
        {"topography": -0.1, "geochemistry": 0.4, "climate": 0.2},
        {"topography": 0, "geochemistry": 0, "climate": 0},
        {"topography": 1.2, "geochemistry": 0, "climate": 0},
    ],
)
def test_invalid_weights_return_422(client, bad_weights):
    response = client.post("/api/v1/analogs/search", json=payload(weights=bad_weights))
    assert response.status_code == 422


def test_invalid_planet_returns_422(client):
    response = client.post("/api/v1/analogs/search", json=payload(target_planet="venus"))
    assert response.status_code == 422


def test_subterranean_filter_is_not_silently_ignored(client):
    response = client.post(
        "/api/v1/analogs/search",
        json=payload(constraints={"subterranean_only": True, "min_similarity": 50}),
    )
    assert response.status_code == 501


def test_unconfigured_scoring_returns_503_with_tiles(client):
    app.dependency_overrides[get_repository] = lambda: FakeRepository(has_tiles=True)
    response = client.post("/api/v1/analogs/search", json=payload())
    assert response.status_code == 503


def test_injected_scorer_produces_valid_payload(client):
    app.dependency_overrides[get_repository] = lambda: FakeRepository(has_tiles=True)
    app.dependency_overrides[get_scoring_engine] = lambda: TestFixtureScorer()
    response = client.post("/api/v1/analogs/search", json=payload())
    assert response.status_code == 200
    result = response.json()
    assert result["results_count"] == 1
    assert result["analogs"][0]["coordinates"] == {"lat": 12.5, "lng": 42.0}
    assert result["analogs"][0]["breakdown"]["geochemistry_match"] == 70.0
    assert result["analogs"][0]["metadata"]["primary_rock"] == "synthetic"


def test_similarity_constraint_filters_results(client):
    app.dependency_overrides[get_repository] = lambda: FakeRepository(has_tiles=True)
    app.dependency_overrides[get_scoring_engine] = lambda: TestFixtureScorer()
    response = client.post(
        "/api/v1/analogs/search", json=payload(constraints={"min_similarity": 80})
    )
    assert response.status_code == 200
    assert response.json()["results_count"] == 0


def test_geojson_feature_collection(client):
    response = client.get("/api/v1/analogs/geojson?limit=20")
    assert response.status_code == 200
    assert response.json() == {"type": "FeatureCollection", "features": []}


def test_geojson_limit_validation(client):
    assert client.get("/api/v1/analogs/geojson?limit=5001").status_code == 422


def test_frontend_cors(client):
    response = client.options(
        "/api/v1/analogs/search",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db


def fake_db():
    yield None


app.dependency_overrides[get_db] = fake_db
client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "AstroTerrain API"


def test_search_rejects_invalid_planet():
    response = client.post(
        "/api/v1/analogs/search",
        json={"target_planet": "venus", "target_site_id": "x"},
    )
    assert response.status_code == 422

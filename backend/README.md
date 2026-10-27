# AstroTerrain — Module 3 Backend Starter

**Milestone 1:** FastAPI + Dockerized PostgreSQL 15 / PostGIS 3.3 + versioned and validated REST APIs.

This is a separate starter you can put into the shared repository under a backend directory, or run independently. It is **not** a finished satellite ingestion or ML implementation.

## Prerequisites

- Windows PowerShell, macOS Terminal, or Linux shell
- Docker Desktop with Docker Compose (Docker Desktop must be running)
- Optional for running tests outside Docker: Python 3.11+

## Easiest way to run (Windows PowerShell)

Open PowerShell *inside this extracted folder* and run:

```powershell
Copy-Item .env.example .env
# Optional: edit .env to change local-only credentials

docker compose up --build -d
docker compose ps
```

Visit:

- Swagger UI: http://localhost:8000/docs
- HTTP check: http://localhost:8000/health
- Database/PostGIS check: http://localhost:8000/health/db
- Planetary targets: http://localhost:8000/api/v1/targets
- Earth GeoJSON: http://localhost:8000/api/v1/analogs/geojson

Expected `/health/db` shape: `{"status":"ok","postgis_version":"..."}`.

Expected `/api/v1/targets` includes `moon_shackleton` and `mars_jezero`.

**Important:** the first database startup creates the tables and the named target records automatically. All target measurements are null until backed by actual sources, and NO Earth tile scores are manufactured.

## Try the POST endpoint on Windows PowerShell

```powershell
$body = @{
    target_planet = "moon"
    target_site_id = "moon_shackleton"
    weights = @{
        topography = 0.4
        geochemistry = 0.4
        climate = 0.2
    }
    constraints = @{
        subterranean_only = $false
        min_similarity = 50.0
    }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/analogs/search" `
    -Method Post -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 8
```

For the brand-new database, the exact expected response is:

```json
{
  "status": "success",
  "target_site_name": "Shackleton Crater",
  "results_count": 0,
  "analogs": []
}
```

This is a **successful contract test, not a real analog search result**. Earth tiles have not been imported and Module 4 has not been wired up yet. If Earth tiles exist but Module 4 is disconnected, the search responds `503` instead of making up scores.

## Endpoints

| HTTP method | Path | Purpose |
|---|---|---|
| GET | `/health` | API liveness |
| GET | `/health/db` | Check PostgreSQL and PostGIS |
| GET | `/api/v1/targets` | Discover seeded reference target IDs |
| GET | `/api/v1/analogs/geojson?limit=250` | Earth-only GeoJSON `FeatureCollection` (limit 1-5000) |
| POST | `/api/v1/analogs/search` | Module 1 -> Module 4 -> Module 2 integration contract |

`/api/v1/analogs/search` accepts the exact agreed request and response field names. Inputs are validated with Pydantic v2. Unknown targets return `404`, planet/ID mismatch `400`, invalid JSON body values `422`, disconnected scorer with populated candidate tiles `503`, and unimplemented subterranean-only mode `501` (rather than silently dropping a requested constraint).

### Request example

```json
{
  "target_planet": "moon",
  "target_site_id": "moon_shackleton",
  "weights": {
    "topography": 0.4,
    "geochemistry": 0.4,
    "climate": 0.2
  },
  "constraints": {
    "subterranean_only": false,
    "min_similarity": 50.0
  }
}
```

Weight values are each between 0 and 1 inclusive, and at least one weight must be positive. Sum exactly 1 is *not required*; Module 4 can normalize weights. Similarity scores use a 0–100 scale. `constraints` may be omitted entirely; default minimum threshold in the search route is 50.

### What Module 4 must implement

Implement `ScoringEngine.score(request, target, repository) -> list[AnalogSiteResult]` from `app/services/scoring.py`. Change dependency factory `get_scoring_engine` to return the real implementation (or override the dependency in composition). All analogs must meet `AnalogSiteResult`, including `coordinates: {lat, lng}` and all three `breakdown` fields. The API filters by `min_similarity`, sorts descending, and returns correct `results_count`.

The scoring engine should query validated Earth feature rows via the repository. Actual feature extraction, candidate queries, and geospatial data provenance are in the *next milestones*, not silently simulated now. An example fake engine is used **only in tests**.

### What Module 2 receives

- `GET /api/v1/analogs/geojson`: valid Earth-only GeoJSON FeatureCollection; each feature has Earth `Point` geometry `[longitude, latitude]` (standard GeoJSON order).
- `POST /api/v1/analogs/search`: `analogs[i].coordinates` uses the team's desired `{lat, lng}` keys (different representation, same Earth WGS84 positions).

**Scientific coordinate caveat:** `GEOMETRY(Point,4326)` is an Earth WGS84 coordinate system. Do not populate `planetary_targets.location` with lunar or Martian lon/lat as if it were Earth. The seeded targets intentionally set it to `NULL`. Planetary spatial locations need explicit celestial-body coordinates/CRS in a later schema evolution.

## Run unit and API contract tests (Windows PowerShell)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

You can also run with any installed Python 3.11+ by replacing `py -3.11` appropriately. These tests use dependency injection with fake repositories and **do not require Docker**. For live database integration, run the Compose stack and manually hit `/health/db` and `/api/v1/targets`.

## Useful Docker commands

```powershell
docker compose logs -f web       # API logs
docker compose logs -f db        # Database logs
docker compose ps                # Container status
docker compose down              # Stop containers; keep DB data
```

Only if you intentionally want to **erase all local database data**:

```powershell
docker compose down -v
```

`database/init/*.sql` files run **only when the Postgres volume is first created**. SQL edits after that need proper migrations (planned future work). Avoid `down -v` when your dataset matters.

## Directory structure

```text
app/
  main.py                    # FastAPI, CORS, router registration
  core/config.py             # Pydantic environment settings
  db/session.py              # SQLAlchemy async connection/session
  db/models.py               # ORM models for supplied SQL tables
  db/repository.py           # Parameterized DB queries, GeoJSON
  schemas/search.py          # Team's stable Pydantic contracts
  services/scoring.py        # Module 4 scorer interface, no fake runtime engine
  api/routes/health.py       # Health checks
  api/routes/targets.py      # Target discovery
  api/routes/analogs.py      # Search gateway + GeoJSON

database/init/
  001_schema.sql             # PostGIS extension, tables and GiST index
  002_seed_targets.sql       # Reference target names, no invented measurements

tests/                       # API and schema tests
```

## Shared repository integration

If your team already has a frontend in the repository root, place this entire starter inside a `backend/` folder instead of overwriting their files. In that arrangement Docker bind mounts and build paths still work **when Compose is run from inside `backend/`**:

```powershell
cd backend
docker compose up --build -d
```

A frontend on `http://localhost:3000` or `http://localhost:5173` can use `http://localhost:8000`. Do not commit `.env`, and change development credentials before any nonlocal deployment.

## Next work after Milestone 1

1. Verify live PostGIS data connection and the GiST index.
2. Build ingestion commands for real SRTM DEM and optical satellite assets with source/provenance metadata.
3. Add validated `EarthTileFeature` extraction and geographically indexed candidate queries for Module 4.
4. Add a supported planetary coordinate representation instead of reusing Earth's EPSG:4326 for Moon/Mars coordinates.
5. Wire real Module 4 scorer and add Docker-backed integration tests.

# AstroTerrain — Module 3 Backend

Development starter: FastAPI + Pydantic v2 + PostgreSQL 15/PostGIS 3.3, SQLAlchemy 2, Psycopg 3, and a deterministic analog-scoring baseline.

> **Demo-data warning:** SQL seed records are synthetic values for software testing only. They are not validated planetary science, measurements, or mission-site recommendations. Replace them with validated project data before scientific interpretation.

## Folder map

```text
backend/
├── app/api/routes/       # HTTP endpoints
├── app/core/             # settings
├── app/db/               # SQLAlchemy session and PostGIS queries
├── app/schemas/          # Pydantic request/response models
├── app/services/         # similarity scoring
├── database/init/        # SQL schema and demo seed data
├── tests/                # unit/API smoke tests
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements*.txt
```

## Windows setup (PowerShell)

From VS Code terminal:

```powershell
cd path\to\AstroTerrain\backend
Copy-Item .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
```

Docker Desktop must be installed and running before the Docker commands. First build may take several minutes because the geospatial Python packages are installed.

Open:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health
- Targets: http://localhost:8000/api/v1/targets

Check PostGIS:

```powershell
docker compose exec db psql -U astroterrain -d astroterrain -c "SELECT PostGIS_Full_Version();"
```

## Test the analog search (PowerShell)

```powershell
$body = @{
    target_planet = "moon"
    target_site_id = "shackleton-crater"
    weights = @{ topography = 0.40; geochemistry = 0.35; climate = 0.25 }
    constraints = @{ subterranean_only = $false; min_similarity = 0; limit = 10 }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/analogs/search" -ContentType "application/json" -Body $body
```

Try Mars with `target_planet = "mars"` and `target_site_id = "jezero-crater"`.

Run tests:

```powershell
docker compose exec api pytest -q
```

Stop containers but keep database data:

```powershell
docker compose down
```

**Destructive reset** — deletes the local Postgres volume and its data:

```powershell
docker compose down -v
```

Do not use the destructive reset after importing real data you need to keep.

## API contract

`POST /api/v1/analogs/search`

```json
{
  "target_planet": "moon",
  "target_site_id": "shackleton-crater",
  "weights": {"topography": 0.4, "geochemistry": 0.35, "climate": 0.25},
  "constraints": {"subterranean_only": false, "min_similarity": 50, "limit": 20}
}
```

Response fields: `status`, `target_site_name`, `results_count`, and `analogs[]` with `site_id`, `name`, `country`, `coordinates {lat,lng}`, `similarity_score`, `breakdown {topography_match,geochemistry_match,climate_match}`, and `metadata {elevation_m,primary_rock,accessibility_rating}`.

Other endpoints:
- `GET /api/v1/health`
- `GET /api/v1/targets`
- `GET /api/v1/targets?planet=moon`
- `GET /api/v1/targets/{site_id}?planet=moon`

## Scoring baseline

- Topography: slope similarity.
- Geochemistry: compares common numeric keys in planetary `regolith_composition` and Earth-analog `spectral_signature`. The current raster pipeline stores NDVI statistics in `spectral_signature`; NDVI is not mineralogical composition. Until compatible mineralogical features are supplied by both datasets, this score uses the available rock-type fallback or a neutral score.
- Climate: overlap of target and Earth-analog temperature intervals.
- Final score: normalized weighted average. Weights do not need to sum to 1, but cannot all be zero.

This is a transparent starter heuristic, not a validated scientific model. The ML module can replace `app/services/scoring.py` while preserving the API schema.

## Database

- `planetary_targets`: Moon/Mars target profiles.
- `earth_analog_tiles`: Earth-side candidate tiles.
- Geometry is `geometry(Point, 4326)` with GiST indexes.
- SQL init scripts run only when Postgres creates a fresh, empty data volume. Editing seed SQL later will not re-run it automatically.

## GIS dependencies

The API Docker image installs GeoPandas, Rasterio, Shapely, PyProj, and GDAL system utilities (`gdalinfo`, `gdal_translate`, etc.). Reusable raster sampling and vector-to-GeoJSON helpers are in `app/services/geospatial.py`. The Python `osgeo.gdal` binding is not pinned because it must match the OS-level GDAL version; Rasterio provides Python raster I/O in this starter. Add a matching Python GDAL binding later only if the pipeline needs `from osgeo import gdal`.

## Official links

- Docker Desktop: https://www.docker.com/products/docker-desktop/
- Docker Windows install: https://docs.docker.com/desktop/setup/install/windows-install/
- Microsoft WSL install: https://learn.microsoft.com/en-us/windows/wsl/install
- FastAPI: https://fastapi.tiangolo.com/
- Pydantic: https://docs.pydantic.dev/latest/
- SQLAlchemy: https://docs.sqlalchemy.org/en/20/
- Psycopg 3: https://www.psycopg.org/psycopg3/docs/
- PostGIS: https://postgis.net/documentation/
- PostGIS Docker image: https://hub.docker.com/r/postgis/postgis
- GeoPandas: https://geopandas.org/en/stable/
- Rasterio: https://rasterio.readthedocs.io/en/stable/
- Shapely: https://shapely.readthedocs.io/en/stable/
- PyProj: https://pyproj4.github.io/pyproj/stable/

**Image version note:** Compose defaults to `postgis/postgis:15-3.3` to match the original team specification. Docker Hub still lists the tag, but it is old (last pushed several years ago). If it cannot be pulled or the team approves an upgrade, set `POSTGIS_IMAGE=postgis/postgis:15-3.7` in `.env` and confirm the version change with the team.


---

## Team Integration Guide

### 1. Backend Connection

Local development base URL:

`http://localhost:8000`

Interactive API documentation:

`http://localhost:8000/docs`

All versioned endpoints use `/api/v1`.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | API and database health |
| GET | `/api/v1/targets` | List planetary targets |
| GET | `/api/v1/targets?planet=moon` | Filter targets by planet |
| GET | `/api/v1/targets/{site_id}?planet=moon` | Retrieve a target |
| POST | `/api/v1/analogs/search` | Search Earth analogs |

### 2. Frontend Integration

CORS allows `http://localhost:3000` by default. Configure `CORS_ORIGINS` if the frontend uses another development origin.

The analog search request accepts:

- `target_planet`: `moon` or `mars`
- `target_site_id`: planetary target identifier
- `weights`: topography, geochemistry and climate weights
- `constraints`: subterranean filter, minimum similarity and result limit

Each analog result includes:

- `site_id`, `name`, `country`
- `coordinates.lat`, `coordinates.lng`
- `similarity_score`
- `breakdown.topography_match`
- `breakdown.geochemistry_match`
- `breakdown.climate_match`
- `metadata.elevation_m`
- `metadata.primary_rock`
- `metadata.accessibility_rating`

Weights must be between 0 and 1, with at least one positive weight. The result limit must be between 1 and 100.

Invalid request data returns HTTP 422. A target that does not exist returns HTTP 404.


### 3. ML Engine Integration

The baseline scoring implementation is in `app/services/scoring.py`.

The API calls:

```python
score_analog(target, candidate, weights)
```

Expected return structure:

```python
{
    "similarity_score": 75.0,
    "breakdown": {
        "topography_match": 80.0,
        "geochemistry_match": 70.0,
        "climate_match": 75.0
    }
}
```

The values above are illustrative.

The ML module can replace the baseline scoring implementation while preserving this structure and returning scores from 0 to 100.

Coordinate changes to model inputs, scoring interfaces and response schemas with the backend lead before merging.

**Scientific limitation:** The current pipeline stores NDVI statistics in `spectral_signature`. NDVI is not mineralogical composition. A reliable mineralogical comparison requires compatible mineralogical or spectral features from both planetary targets and Earth analogs.

### 4. 3D Globe Integration

Database geometries use PostGIS `geometry(Point, 4326)`.

The API returns coordinates as:

```json
{
  "lat": 36.1,
  "lng": -117.0
}
```

GeoJSON requires longitude first and latitude second:

```javascript
const feature = {
  type: "Feature",
  geometry: {
    type: "Point",
    coordinates: [
      analog.coordinates.lng,
      analog.coordinates.lat
    ]
  },
  properties: {
    site_id: analog.site_id,
    name: analog.name,
    similarity_score: analog.similarity_score
  }
};
```

The globe module can use these coordinates to position Earth-analog markers.

The backend currently provides point coordinates, not dedicated terrain tiles, raster overlays or 3D mesh endpoints.

### 5. Raster Data Ingestion

Processing modules:

- `app/services/ingestion.py`
- `app/services/geospatial.py`
- `app/services/pipeline.py`

The `ingest_raster_analog()` function accepts a DEM GeoTIFF, red-band GeoTIFF, NIR-band GeoTIFF and site metadata.

It calculates elevation statistics, terrain slope and NDVI, then inserts or updates an Earth-analog record in PostGIS.

**Input requirements:**

- DEM must have a valid CRS and usable dimensions.
- Red and NIR rasters must have matching CRS, dimensions and transforms.
- Red and NIR values must be compatible reflectance values.
- DEM elevation values are currently assumed to be in metres.

The ingestion function is a Python service, not a public HTTP upload endpoint. Raster files must be accessible to the Python process inside the API container.

Example usage:

```python
from app.db.session import get_session_factory
from app.services.pipeline import ingest_raster_analog

db = get_session_factory()()

try:
    result = ingest_raster_analog(
        db=db,
        dem_path="/data/dem.tif",
        red_path="/data/red.tif",
        nir_path="/data/nir.tif",
        site_id="earth-site-001",
        site_name="Example Analog Site",
        country="Example Country",
        primary_rock="Basalt",
        data_source="team_dataset"
    )
    print(result)
finally:
    db.close()
```

The `/data` paths are illustrative. Files must first be made accessible inside the container.

Automatic NASA/ESA dataset downloading is not implemented in the current pipeline.

### 6. Database Integration

Main tables:

- `planetary_targets`: Moon and Mars target profiles.
- `earth_analog_tiles`: Earth analog locations and processed attributes.

Both use EPSG:4326 point geometries and spatial GiST indexes.

Database operations are organized in `app/db/repository.py`. Connection configuration is managed through `DATABASE_URL`.

Coordinate changes to shared tables and schemas with the backend lead before merging.

### 7. Integration Workflow

1. Start the backend using Docker Compose.
2. Verify `/api/v1/health`.
3. Inspect endpoints at `/docs`.
4. Connect the frontend to target and analog-search endpoints.
5. Connect the globe using returned coordinates.
6. Coordinate the ML scoring interface.
7. Import compatible Earth-analog datasets.
8. Run backend tests after integration changes.

Run tests with:

```powershell
docker compose exec api python -m pytest -v
```

### 8. Current Implementation Limitations

- Seeded records are synthetic demo data, not validated scientific observations.
- DEM and NDVI processing has been tested using synthetic raster files.
- Automatic NASA/ESA dataset discovery and downloading is not implemented.
- Similarity scoring is a deterministic baseline, not a validated scientific model.
- Mineralogical spectral comparison requires additional compatible features.
- Raster ingestion is currently a Python service, not a public upload endpoint.
- Terrain mesh generation and visualization-tile endpoints are not implemented.

These limitations should be considered when interpreting results and integrating scientific datasets.
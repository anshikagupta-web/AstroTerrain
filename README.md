
# AstroTerrain

**A planetary terrain analog exploration platform for Earth, the Moon, and Mars.**

AstroTerrain brings together planetary target data, Earth-side terrain and climate datasets, geospatial storage, similarity scoring, and an interactive 3D exploration interface. The project is designed to help explore locations on Earth whose available terrain and environmental characteristics can be compared with selected lunar and Martian sites.

> **Scientific integrity:** AstroTerrain is an exploration and research prototype. Candidate locations and similarity scores are not validated scientific analog determinations, mission-site recommendations, or proof of environmental equivalence.

---

## Project overview

Planetary exploration often relies on terrestrial analog environments to study terrain, geology, and environmental conditions. AstroTerrain provides a common platform for organizing relevant datasets and exploring comparisons between planetary targets and Earth locations.

The project is organized into four major components:

1. **Frontend** — an interactive interface for selecting planetary targets and exploring Earth-side candidate locations.
2. **Backend** — a FastAPI service, PostGIS database, geospatial processing utilities, and analog-search API.
3. **ML Engine** — reusable preprocessing, feature comparison, candidate ranking, explainability, and reporting modules.
4. **Scientific Data** — collected Earth, lunar, and Martian datasets with source metadata and integrity checks.

## Architecture

```text
                    ASTROTERRAIN
                         |
          +--------------+--------------+
          |              |              |
       Frontend       Backend        ML Engine
      React/Vite      FastAPI        Python package
      Three.js           |               |
          |              |               |
          +------ REST API --------------+
                         |
                  PostgreSQL
                    + PostGIS
                         |
                Scientific Datasets
                 Earth / Moon / Mars
````

The frontend communicates with the backend through versioned HTTP endpoints. The backend manages target and analog records, performs baseline feature scoring, and uses PostGIS for spatial data. The ML Engine provides a separate set of reusable comparison and ranking components.

Module integration and deployment configuration may vary as development continues.

## **Technology stack**

| Component             | Technologies                                                               |
| --------------------- | -------------------------------------------------------------------------- |
| Frontend              | React 18, TypeScript, JavaScript, Vite 6                                   |
| 3D visualization      | Three.js                                                                   |
| Backend API           | Python, FastAPI, Pydantic v2                                               |
| Database              | PostgreSQL 15, PostGIS 3.3                                                 |
| Database access       | SQLAlchemy 2, Psycopg 3                                                    |
| Geospatial processing | GeoPandas, Rasterio, Shapely, PyProj                                       |
| ML Engine             | Python, NumPy and project-defined comparison modules                       |
| Infrastructure        | Docker, Docker Compose                                                     |
| Scientific data       | Copernicus, NASA POWER, LOLA, Diviner, M3, MOLA, CRISM and THEMIS products |

## **Repository structure**

```
AstroTerrain/
|
+-- backend/
|   +-- app/
|   |   +-- api/routes/       # Health, targets and analog-search routes
|   |   +-- core/             # Application configuration
|   |   +-- db/               # Database session and repository
|   |   +-- schemas/          # API request and response models
|   |   +-- services/         # Scoring, ingestion and geospatial utilities
|   +-- database/init/        # Database initialization scripts
|   +-- tests/                # Backend tests
|   +-- Dockerfile
|   +-- docker-compose.yml
|   +-- requirements.txt
|
+-- frontend/
|   +-- src/
|   |   +-- App.tsx           # Main application and dashboard
|   |   +-- Globe.jsx         # Planet and Earth visualization
|   |   +-- api.js            # Backend API client
|   |   +-- index.css         # Application styling
|   +-- package.json
|
+-- ml-engine/
|   +-- ml_engine/
|   |   +-- comparison/       # Climate, topography and geochemistry
|   |   +-- preprocessing/    # Validation, missing values and normalization
|   |   +-- ranking/          # Candidate ranking
|   |   +-- explainability/   # Comparison explanations
|   |   +-- reporting/        # Site reports
|   |   +-- models/           # Shared model schemas
|   |   +-- adapter.py        # Integration adapter
|   +-- examples/
|   +-- tests/
|   +-- pyproject.toml
|   +-- requirements.txt
|
+-- data/
|   +-- earth/
|   |   +-- copernicus_glo90/
|   |   +-- nasa_power/
|   +-- lunar/
|   |   +-- lola_875s_20m/
|   |   +-- diviner/
|   |   +-- m3_index/
|   +-- mars/
|   |   +-- mola/
|   |   +-- crism/
|   |   +-- themis/
|   +-- README.md
|   +-- SHA256SUMS.txt
|
+-- .gitattributes
+-- README.md
```

## **Frontend**

The React application provides the primary exploration interface.

Current interface components include:

- A landing screen with Moon and Mars target selection.
- Planetary target information and backend health status.
- An interactive Earth globe with candidate location markers.
- A dashboard for exploring analog-search results.
- Similarity, topography, mineralogy and climate display-layer controls.
- Candidate detail panels and comparative reports.
- GeoJSON and JSON report exports.
- Backend connection and error-state handling.

The frontend uses Three.js for its globe and planetary visualization components.

**Integration note:** A display-layer control does not necessarily indicate that a corresponding independent scientific raster layer or calibrated visualization service is available. Layer availability depends on the underlying data and integration.

### **Run the frontend**

```
cd frontend
npm install
npm run dev
```

Vite prints the local development URL in the terminal. The backend CORS configuration currently includes `http://localhost:3000` and `http://localhost:5173`.

## **Backend**

The backend is built with FastAPI and uses PostgreSQL with PostGIS for storing and querying spatial records.

Its responsibilities include:

- Serving planetary target information.
- Accepting analog-search requests.
- Retrieving candidate records.
- Comparing available terrain, geochemistry and climate features.
- Returning similarity results and feature-availability information.
- Providing geospatial processing and raster-ingestion utilities.

### **Run with Docker Compose**

Requirements:

- Docker Desktop
- Docker Compose
- A running Docker engine

From the repository root:

```
cd backend
Copy-Item .env.example .env
docker compose config
docker compose up --build -d
docker compose ps
```

The API is available at:

- API base: `http://localhost:8000`
- Interactive API documentation: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/api/v1/health`

Check the database's PostGIS installation:

```
docker compose exec db psql -U astroterrain -d astroterrain -c "SELECT PostGIS_Full_Version();"
```

Stop the services while retaining the database volume:

```
docker compose down
```

> Avoid `docker compose down -v` if you need to preserve the local database contents. The `-v` option deletes the Compose-managed database volume.

The Compose configuration mounts the repository's `data/` directory into the API container at `/app/data` as read-only.

### **API endpoints**

All versioned endpoints use `/api/v1`.

| Method | Endpoint                                | Purpose                            |
| ------ | --------------------------------------- | ---------------------------------- |
| GET    | `/api/v1/health`                        | API and database health            |
| GET    | `/api/v1/targets`                       | List planetary targets             |
| GET    | `/api/v1/targets?planet=moon`           | Filter targets by planet           |
| GET    | `/api/v1/targets/{site_id}?planet=moon` | Retrieve a specific target         |
| POST   | `/api/v1/analogs/search`                | Search for Earth analog candidates |

### **Analog search request**

Example request:

```
{
  "target_planet": "moon",
  "target_site_id": "shackleton-crater",
  "weights": {
    "topography": 0.4,
    "geochemistry": 0.35,
    "climate": 0.25
  },
  "constraints": {
    "subterranean_only": false,
    "min_similarity": 0,
    "limit": 20
  }
}
```

PowerShell example:

```
$body = @{
    target_planet = "moon"
    target_site_id = "shackleton-crater"
    weights = @{
        topography = 0.40
        geochemistry = 0.35
        climate = 0.25
    }
    constraints = @{
        subterranean_only = $false
        min_similarity = 0
        limit = 20
    }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod `
    -Method Post `
    -Uri "http://localhost:8000/api/v1/analogs/search" `
    -ContentType "application/json" `
    -Body $body
```

Use `target_planet = "mars"` and an available Martian target identifier to search against a Mars target.

### **Feature-aware similarity scoring**

The backend scoring service compares three feature categories:

- **Topography:** compares available slope measurements.
- **Geochemistry:** compares common numeric composition or spectral-signature keys, with a rock-type fallback when available.
- **Climate:** compares temperature intervals only when the measurement types match.

A key design principle is that unavailable data should not be mistaken for a valid similarity score.

The scoring service therefore:

- Represents unavailable feature comparisons as `null`.
- Calculates the final weighted score using only available, positively weighted features.
- Returns the contributing `available_features`.
- Reports `feature_coverage`, indicating the proportion of configured weight represented by available features.
- Rejects configurations in which every similarity weight is zero.

This improves transparency when datasets have incomplete or incompatible measurements.

The scoring implementation is a deterministic baseline. It is not a scientifically validated planetary analog model.

## **ML Engine**

The ML Engine is maintained as a separate Python package under `ml-engine/`.

Its current package structure includes:

| Module            | Responsibility                                               |
| ----------------- | ------------------------------------------------------------ |
| `preprocessing/`  | Feature validation, missing-value handling and normalization |
| `comparison/`     | Climate, topography and geochemistry comparisons             |
| `ranking/`        | Candidate ranking                                            |
| `explainability/` | Explanations for comparison results                          |
| `reporting/`      | Site-level report generation                                 |
| `models/`         | Shared data schemas                                          |
| `adapter.py`      | Adapter for integration with other project components        |
| `examples/`       | Example workflows                                            |
| `tests/`          | Module and integration tests                                 |

The ML Engine is intended to provide reusable comparison and ranking functionality. Its presence as a package does not by itself mean that every ML workflow is already connected to the live frontend and backend.

### **Install and test**

From the repository root:

```
cd ml-engine
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest tests -v
```

If PowerShell blocks virtual-environment activation, use the Python executable inside `.venv` directly or adjust the local execution policy according to your environment.

## **Scientific dataset collection**

Real scientific datasets are organized under `data/`. Original product files and available labels, headers, XML files and catalog metadata are retained wherever available.

### **Earth**

**Copernicus GLO-90**

- Four regional Digital Elevation Model GeoTIFF tiles.
- Used for elevation and terrain context.
- Stored in `data/earth/copernicus_glo90/`.

**NASA POWER**

- Four regional daily climate CSV files.
- Regions: Hawaii, Svalbard, Atacama and Antarctica.
- Parameters: T2M, T2M_MAX and T2M_MIN.
- Period: 1 January 2020 to 31 December 2025.
- 2,192 daily observations per regional file.
- Missing-value sentinel: `-999`.
- Stored in `data/earth/nasa_power/`.

These regions are candidate locations for exploration, not scientifically validated analog matches.

### **Moon**

**Lunar Orbiter Laser Altimeter (LOLA)**

- Polar elevation raster.
- 7,584 × 7,584 samples.
- 32-bit floating point.
- 20 m/pixel map scale.
- Polar stereographic projection.
- Original PDS label and supporting metadata retained.
- Stored in `data/lunar/lola_875s_20m/`.

**Diviner**

- Maximum and minimum TBOL anomaly point datasets.
- These represent brightness-temperature anomalies, not absolute surface temperatures.
- Stored in `data/lunar/diviner/`.

**Moon Mineralogy Mapper (M3)**

- L2 product index and associated information files.
- The collected files are index products, not the actual reflectance image products.
- Stored in `data/lunar/m3_index/`.

### **Mars**

**Mars Orbiter Laser Altimeter (MOLA)**

- Global elevation raster.
- Original labels, headers and supporting metadata retained.
- Stored in `data/mars/mola/`.

**Compact Reconnaissance Imaging Spectrometer for Mars (CRISM)**

- Product inventories and search metadata.
- Includes the downloaded mineral-summary product `t1250_mrrsu_20n078_0327_4`.
- Dimensions: 1,636 lines × 1,538 samples × 60 bands.
- Sample format: PC_REAL, 32-bit.
- Map projection: Equirectangular.
- Label-reported centre: 20.0° N, 77.5° E.
- Stored in `data/mars/crism/`.

The CRISM file is a mineral-summary product. Its footprint and band metadata must be checked before making claims about specific locations or mineral abundances.

**THEMIS**

- Daytime PNG image retained for visual context.
- It is not a calibrated numeric thermal raster.
- Stored in `data/mars/themis/`.

For the detailed dataset inventory and integrity information, see [`data/README.md`](https://data/README.md?utm_source=chatgpt.com).

## **Scientific limitations and responsible interpretation**

The current project dataset and processing pipeline have important limitations:

- Earth candidate locations have not been scientifically validated as planetary analogs.
- No NDVI result is claimed because aligned red/NIR reflectance rasters are not available.
- Diviner anomaly values must not be interpreted as absolute surface temperatures.
- M3 index files are not substitutes for M3 reflectance products.
- The CRISM mineral-summary product requires footprint and band verification before location-specific interpretation.
- THEMIS PNG imagery is for visual context, not calibrated numeric thermal analysis.
- No unsupported mineral percentages or compositions should be inferred from the collected files.
- The baseline similarity score depends on the availability and compatibility of input features.
- The current backend exposes point coordinates; it does not provide dedicated terrain tiles, raster overlays or 3D mesh endpoints.
- Raster ingestion is implemented as a Python service, not as a public file-upload API.
- Automatic NASA/ESA dataset discovery and downloading is not implemented as part of the current backend workflow.

Results should be treated as exploratory comparisons until the required measurements, processing, validation and scientific review are completed.

## **Data integrity and Git LFS**

Large scientific raster files are tracked using Git Large File Storage (Git LFS).

Install Git LFS before cloning or pulling the complete dataset:

```
git lfs install
```

Clone the repository:

```
git clone https://github.com/anshikagupta-web/AstroTerrain.git
cd AstroTerrain
git lfs pull
```

To retrieve the team's backend branch and its large files:

```
git fetch origin
git checkout feature/backend
git pull origin feature/backend
git lfs pull
```

The repository includes:

- `.gitattributes` — Git LFS tracking rules.
- `data/SHA256SUMS.txt` — SHA-256 checksums for collected files.

To verify dataset integrity from the repository root:

```
Get-FileHash .\data\earth\copernicus_glo90\* -Algorithm SHA256
```

For a complete checksum verification, compare the generated hashes against `data/SHA256SUMS.txt`. Recreate the checksum manifest whenever dataset files are added or modified.

## **Development and collaboration**

The project is divided into independently maintainable modules:

- Frontend development and API integration.
- Backend APIs, database operations and geospatial processing.
- ML feature processing, comparison and ranking.
- Planetary and Earth scientific data collection, validation and provenance.

When changing shared interfaces, coordinate updates to API schemas, database models, scoring outputs and frontend types with the relevant module contributors.

Recommended development workflow:

1. Pull the latest intended project branch.
2. Install Git LFS and retrieve the scientific datasets.
3. Start the backend and verify its health endpoint.
4. Start the frontend and verify API connectivity.
5. Run the relevant module tests after making changes.
6. Coordinate interface changes before merging shared-module work.

## **Project status**

AstroTerrain currently contains:

- A React-based planetary exploration interface.
- A FastAPI backend with target and analog-search endpoints.
- A PostgreSQL/PostGIS database setup.
- A deterministic, feature-aware baseline scoring service.
- Geospatial processing and raster-ingestion utilities.
- A separate ML Engine package with preprocessing, comparison, ranking, explainability and reporting modules.
- A repository collection of Earth, lunar and Martian scientific datasets.
- Git LFS configuration and dataset checksum documentation.

Further work includes validating scientific analog candidates, expanding compatible mineralogical and environmental datasets, completing module integration, and developing additional geospatial visualization services.

## **Project context**

Developed as a planetary exploration and Earth-analog research prototype for the **NASA Space Apps Challenge 2026**.

**Repository:** [anshikagupta-web/AstroTerrain](https://github.com/anshikagupta-web/AstroTerrain?utm_source=chatgpt.com)


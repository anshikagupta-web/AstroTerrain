# AstroTerrain ML Engine — Module 4
## Spatial Machine Learning Engine & Technical Report Generator

**Project:** AstroTerrain (NASA Space Apps Challenge 2026)  
**Module Owner:** Ananya (Module 4 — Machine Learning & Spatial Similarity)  
**Collaborating Developers:**
* **Module 1 (Frontend & UI/UX):** Manan
* **Module 2 (3D GIS & Globe):** Pranjil
* **Module 3 (Backend & Database):** Anshika
* **Module 4 (Spatial ML & Reporting):** Ananya (THIS MODULE)

**Status:** Fully Integrated with Real Datasets & Backend API, 100% Verified  
**Test Suite:** 174/174 Tests Passing (ML Engine) + 8/8 Tests Passing (Backend Integration & Schemas) = **182 Tests Passing Total**

---

## 1. Executive Summary & Module Role

AstroTerrain is a planetary-site comparison platform that identifies terrestrial analogues for lunar and Martian exploration sites. The system evaluates Earth candidates against extraterrestrial targets (e.g., Shackleton Crater at the Lunar South Pole, Marius Hills skylight, Jezero Crater delta on Mars, and Pavonis Mons pit craters) across three scientific dimensions:

1. **Topography:** Datum-invariant geometric slope derived from Digital Elevation Models (LOLA, MOLA, Copernicus GLO-90).
2. **Geochemistry:** Mineralogical composition vectors and geological rock classifications.
3. **Climate:** Thermal envelope and continuous temperature interval overlap analysis (NASA POWER, Diviner, MEDA).

Module 4 provides the complete spatial machine learning, ranking, explainability, and reporting engine:
* Ingestion, unit standardization, and strict physical range validation.
* Real scientific dataset integration (NASA POWER CSVs, Copernicus DEM, LOLA, MOLA, Diviner thermal anomalies).
* Multi-criteria similarity scoring with continuous mathematical functions and asymptotic behavior.
* Dynamic weight renormalization when measurements are unavailable (strictly no arbitrary score imputation).
* Deterministic candidate ranking with stable tie-breaking (`(-similarity_score, site_id)`).
* Transparent, template-driven explainability without hallucinating LLMs.
* Automated mission site reports (structured models, plain-text rendering, optional PDF).
* Full drop-in backend API integration with FastAPI (`backend/app/api/routes/analogs.py`).

---

## 2. Real Scientific Datasets & Data Provenance

Module 4 connects directly to verified scientific datasets located in the repository's `data/` directory:

### A. Terrestrial Datasets (`data/earth/`)
1. **Copernicus DEM GLO-90 (ESA):**
   * High-resolution 90m global digital elevation model.
   * Point elevation and geometric slope extracted at 4 candidate coordinates:
     * **Hawaii Volcanic Field (Mauna Kea/Loa):** Lat 19.5° N, Lng -155.5° E | Elevation: 3,210.3 m | Slope: 8.36°
     * **Svalbard Arctic Terrain (Spitsbergen):** Lat 78.0° N, Lng 16.0° E | Elevation: 34.9 m | Slope: 1.31°
     * **Atacama Desert Hyper-Arid Core (Yungay):** Lat -23.5° N, Lng -68.2° E | Elevation: 2,300.7 m | Slope: 0.02°
     * **McMurdo Dry Valleys (Beacon Valley, Antarctica):** Lat -77.5° N, Lng 161.0° E | Elevation: 1,505.7 m | Slope: 9.42°
2. **NASA POWER Daily Meteorological Observations:**
   * 6-year continuous daily meteorological time series (2020–2025 inclusive; 2,192 daily records per site).
   * Parameters ingested: $T_{2M}$ (daily mean), $T_{2M,\min}$ (daily minimum), $T_{2M,\max}$ (daily maximum).
   * Verified statistics:
     * **Hawaii:** Mean 18.45°C | Observed range: [10.34°C, 27.28°C]
     * **Svalbard:** Mean -5.82°C | Observed range: [-30.40°C, 11.44°C]
     * **Atacama:** Mean 15.25°C | Observed range: [-2.73°C, 35.20°C]
     * **Antarctica:** Mean -29.38°C | Observed range: [-54.33°C, -7.39°C]

### B. Lunar Datasets (`data/lunar/`)
1. **LRO LOLA (Lunar Orbiter Laser Altimeter):**
   * Polar DEM at 20m/pixel referenced to the LOLA 1,737.4 km mean radius sphere.
   * **Shackleton Crater:** Rim elevation -1,200m to floor -4,000m | Average wall slope: 12.5°.
   * **Marius Hills Pit Crater:** Skylight wall slope: 28.0° | Floor elevation: -250m.
2. **LRO Diviner Lunar Radiometer Experiment:**
   * Spatial bolometric brightness-temperature anomaly grids (`diviner_tbol_max_anom.xyz`, `diviner_tbol_min_anom.xyz`).
   * South Pole coordinates (-0.25° lon, -89.75° lat): Maximum anomaly = +28.27 K, Minimum anomaly = +2.91 K.
   * **Scientific Constraint:** Values are brightness-temperature departures ($\Delta T_{\text{bol}}$ in Kelvin) relative to a diurnal thermal model, NOT absolute surface temperatures. They are isolated in scientific metadata and excluded from direct temperature matching.
3. **Chandrayaan-1 $M^3$ (Moon Mineralogy Mapper):**
   * Catalogue index products (`m3_shackleton_pds_index.csv`).
   * Contains PDS metadata records; calibrated reflectance spectral cubes are not present. Mineral composition is strictly marked unavailable to prevent fabrication.

### C. Martian Datasets (`data/mars/`)
1. **MGS MOLA (Mars Orbiter Laser Altimeter):**
   * Topography referenced to the 610.5 Pa areoid datum.
   * **Jezero Crater Delta:** Delta fan slope 6.0° | Elevation: -2,500m.
   * **Pavonis Mons Flank Pit:** Collapsed pit wall slope: 22.0° | Elevation: +4,200m.
2. **Mars 2020 MEDA (Mars Environmental Dynamics Analyzer):**
   * Ground surface temperature envelope at Jezero crater floor: [-85°C, +10°C].
3. **MRO CRISM (Compact Reconnaissance Imaging Spectrometer for Mars):**
   * Product `t1250_mrrsu_20n078_0327_4` inspected. Footprint center is at (20.0° N, 77.5° E), north of the Jezero crater floor center (18.38° N, 77.58° E), and is an uncalibrated LFS pointer. Mineral composition is marked unavailable.
4. **2001 Mars Odyssey THEMIS:**
   * Daytime mosaic `themis_day_N00_060.png` is an 8-bit uncalibrated visual rendering. Retained for visual context only; strictly not treated as numerical temperature data.

---

## 3. Mathematical & Scientific Methodology

### A. Topography: Datum-Invariant Slope-Only Scoring
Terrestrial and planetary elevations cannot be directly compared because they are referenced to fundamentally incompatible datums:
* **Earth:** Referenced to the **Earth Geoid** (mean sea level approximated by WGS84).
* **Moon:** Referenced to a rigid **1,737.4 km sphere** (LOLA laser altimetry).
* **Mars:** Referenced to the **610.5 Pa Areoid** (triple point of water gravitational equipotential).

A terrestrial mountain at +3,200m above sea level shares no physical zero-reference with a Martian crater at -2,500m relative to the areoid. Assigning weight to raw elevation difference distorts cross-planetary comparisons.

**Module 4 Solution:**
* **Absolute Elevation Excluded from Active Scoring:** Weight is set to 0.0 (`DEFAULT_ELEVATION_WEIGHT = 0.0`). Elevation is preserved as validation metadata and in diagnostic reports.
* **Geometric Slope Angle:** Scale- and datum-invariant metric. A 12° slope on the Moon represents the identical gravitational incline as a 12° slope on Earth.
* **Calibrated Gaussian Slope Similarity:**
  $$S_{\text{topo}} = 100.0 \times \exp\left( -\frac{(\theta_{\text{target}} - \theta_{\text{candidate}})^2}{2\sigma_{\text{slope}}^2} \right)$$
  where $\sigma_{\text{slope}} = 5.0^\circ$ is the initial configurable calibration parameter.
* **Missing Slope Handling:** When slope is missing from either profile, the topography dimension is marked `UNAVAILABLE` (assigned 0.0 in breakdown and dynamic weight renormalization triggered). It is never imputed as 0° or replaced with an arbitrary fallback.

### B. Geochemistry & Mineralogy
* **Direct Cosine Similarity Mapping (0–100):** Mineral composition vectors contain non-negative concentrations ($v_i \ge 0$). Cosine similarity naturally spans $[0.0, 1.0]$:
  $$S_{\text{mineral}} = \cos(\theta) \times 100.0 = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} \times 100.0$$
  Orthogonal vectors (disjoint minerals) score exactly **0.0%**; identical vectors score **100.0%**.
* **Categorical Rock Classification (Fallback):**
  - Exact rock type match (e.g. basalt to basalt): $90.0$
  - Same geological family (e.g. basalt to basaltic sediment): $60.0$
  - Different geological family: $20.0$
* **NDVI Safeguard:** NDVI measures terrestrial chlorophyll reflectance. The ML Engine strictly rejects NDVI as a proxy for mineralogy, emits a diagnostic warning, and marks the mineral dimension unavailable.

### C. Climate: Continuous Interval Overlap & Physical Comparability Safeguard
Compares planetary temperature range $[T_{\min}, T_{\max}]$ with candidate $[C_{\min}, C_{\max}]$:
* **Physical Measurement Type Safeguard:** Earth NASA POWER data measures **2-metre atmospheric air temperature ($T_{2M}$)**, whereas Mars MEDA and Moon Diviner observe **ground-surface skin radiation temperatures ($T_{\text{ground}}$ / $T_{\text{bol}}$)** or spatial microclimate extremes. Directly comparing 2-metre air temperature against ground-surface radiation temperature without a planetary boundary layer conversion model is unphysical. When measurement types are incompatible (e.g. `air_2m` vs `ground_surface`), climate similarity is strictly marked `UNAVAILABLE` and the active weights are redistributed across the remaining valid dimensions.
* **Overlapping Ranges (when compatible):**
  $$S = 35.0 + 65.0 \times \frac{\text{Overlap}}{\text{Union}} \quad \in [35.0, 100.0]$$
* **Non-Overlapping Ranges (with gap):**
  $$S = 35.0 \times \exp\left( -\frac{\text{Gap}^2}{2\sigma_{\text{gap}}^2} \right) \quad \in [0.0, 35.0)$$
  where $\sigma_{\text{gap}} = 30.0^\circ\text{C}$.
* **Continuity Property:** At exact boundary contact ($\text{Gap} = 0, \text{Overlap} = 0$), both formulas yield exactly $35.0$. The metric is continuous and strictly monotonic.

### D. Planet-Aware Validation & Normalization Envelopes
Strict physical bounds prevent sensor errors or out-of-range values from entering profiles:
* **Earth:** Elevation `[-12,000m, 30,000m]`, Temperature `[-100°C, 70°C]`
* **Moon:** Elevation `[-12,000m, 15,000m]`, Temperature `[-250°C, 150°C]` (cryogenic PSRs to illuminated subsolar point)
* **Mars:** Elevation `[-10,000m, 25,000m]`, Temperature `[-150°C, 40°C]` (polar cap to equatorial summer surface)

### E. Multi-Criteria Aggregation & Dynamic Renormalization
For requested weights $w_{\text{topo}}, w_{\text{geo}}, w_{\text{clim}} \ge 0$:
1. Let $\mathcal{A}$ be the set of dimensions where $S_i$ was computed and $w_i > 0$.
2. If $\mathcal{A} = \emptyset$, return `overall_score = None`, `insufficient_data = True`.
3. Renormalize weights: $w_i^{\text{eff}} = \frac{w_i}{\sum_{j \in \mathcal{A}} w_j}$.
4. Overall similarity: $S = \sum_{i \in \mathcal{A}} w_i^{\text{eff}} \times S_i$.
5. If any dimension is missing, `is_complete = False` and the unavailable dimension is listed in `unavailable_dimensions`.

### F. Deterministic Candidate Ranking
* Primary key: `similarity_score` descending.
* Tie-breaking key: `site_id` ascending (alphabetical).
* Guaranteed stable, repeatable ranking across distributed queries.

---

## 4. Backend & API Integration

The ML Engine connects directly to FastAPI via `backend/app/api/routes/analogs.py`.

### A. Contract Conformance
Backend endpoint: `POST /api/v1/analogs/search`

Request schema:
```json
{
  "target_planet": "mars",
  "target_site_id": "mars-jezero-real",
  "weights": {
    "topography": 0.35,
    "geochemistry": 0.30,
    "climate": 0.35
  },
  "constraints": {
    "min_similarity": 20.0,
    "limit": 10
  }
}
```

Response schema (`AnalogSearchResponse`):
```json
{
  "target_site_name": "Jezero Crater Delta (Mars 2020 Landing Site)",
  "results_count": 4,
  "analogs": [
    {
      "site_id": "real-analog-hawaii",
      "name": "Hawaii Volcanic Field (Mauna Kea/Loa)",
      "country": "United States",
      "coordinates": {"lat": 19.5, "lng": -155.5},
      "similarity_score": 75.84,
      "breakdown": {
        "topography_match": 89.42,
        "geochemistry_match": 60.0,
        "climate_match": 0.0
      },
      "metadata": {
        "elevation_m": 3210.327,
        "primary_rock": "basalt",
        "accessibility_rating": "Excellent",
        "data_source": "copernicus_glo90_nasa_power",
        "unavailable_dimensions": ["climate"],
        "warnings": [
          "Notice: Target and candidate elevations are referenced to distinct planetary datums...",
          "Geochemistry score is based solely on literature-derived categorical rock classification...",
          "Climate comparison unavailable: Physical measurement type mismatch: Target provides 'ground_surface' while Candidate provides 'air_2m'..."
        ],
        "is_complete": false
      },
      "ml_engine_metadata": {
        "insufficient_data": false,
        "is_complete": false,
        "dimensions_computed": 2,
        "dimensions_unavailable": 1,
        "unavailable_dimensions": ["climate"],
        "effective_weights": {"topography": 0.5385, "geochemistry": 0.4615, "climate": 0.0},
        "warnings": [...]
      }
    }
  ]
}
```

### B. Frontend Compatibility
* Existing required fields (`site_id`, `name`, `country`, `coordinates`, `similarity_score`, `breakdown`, `metadata`) are 100% preserved.
* Added optional fields (`unavailable_dimensions`, `warnings`, `is_complete`, `ml_engine_metadata`) provide rich diagnostic metadata without altering existing frontend parser expectations.

---

## 5. Directory Structure

```text
ml-engine/
|-- ml_engine/                      # Core Python package
|   |-- __init__.py                 # Public API exports
|   |-- adapter.py                  # Backend drop-in adapter (score_analog, accessibility_rating)
|   |-- data_loader.py              # Scientific data loader (NASA POWER, Diviner XYZ, real profiles)
|   |-- comparison/                 # Scientific similarity engines
|   |   |-- __init__.py
|   |   |-- climate.py              # Continuous interval overlap temperature engine
|   |   |-- geochemistry.py         # Direct mineral cosine mapping & rock classification
|   |   |-- similarity.py           # Multi-criteria weighted aggregation & weight renormalization
|   |   `-- topography.py           # Datum-invariant Gaussian slope-only topography engine
|   |-- explainability/             # Explainability generator
|   |   |-- __init__.py
|   |   `-- explanations.py         # Diagnostic summaries, warnings, and limitations
|   |-- models/                     # Domain schemas
|   |   |-- __init__.py
|   |   `-- schemas.py              # PlanetaryTarget, EarthCandidate, SimilarityResult, SiteReport
|   |-- preprocessing/              # Validation and normalization
|   |   |-- __init__.py
|   |   |-- feature_validation.py   # Strict physical range validation & profile construction
|   |   |-- missing_values.py       # Missing-dimension audits
|   |   `-- normalization.py        # Planet-aware normalization bounds (Earth/Moon/Mars)
|   |-- ranking/                    # Deterministic candidate ranking
|   |   |-- __init__.py
|   |   `-- candidate_ranking.py    # (-similarity_score, site_id) sorting
|   `-- reporting/                  # Site report generator
|       |-- __init__.py
|       `-- site_reports.py         # Structured SiteReport models and plain-text layout
|-- examples/
|   |-- evaluate_real_datasets.py   # Real scientific evaluation script (4 candidates vs 4 targets)
|   `-- synthetic_demo.py           # Synthetic demonstration script
|-- tests/
|   |-- test_adapter.py             # Adapter contract & error handling tests (16 tests)
|   |-- test_backend_integration.py # Full backend schema & SQL fixture tests (19 tests)
|   |-- test_explainability.py      # Summary generation & warning propagation tests (8 tests)
|   |-- test_preprocessing.py       # Planet-specific bounds & normalization tests (36 tests)
|   |-- test_ranking.py             # Deterministic sorting & threshold tests (8 tests)
|   |-- test_reporting.py           # SiteReport generation & text rendering tests (6 tests)
|   |-- test_scientific_data.py     # Real dataset ingestion, constraints, route tests (21 tests)
|   `-- test_similarity.py          # Topography, direct cosine, climate tests (60 tests)
|-- conftest.py                     # Pytest path configuration
|-- pyproject.toml                  # Standard package configuration
|-- requirements.txt                # Dependencies
`-- README.md                       # Comprehensive technical documentation
```

---

## 6. Verification & Test Results

The combined test suite contains **182 automated unit and integration tests** in pytest:

| Test Module | Test Count | Scope & Verification |
| :--- | :---: | :--- |
| `ml-engine/tests/test_adapter.py` | 16 | Adapter contract, float scores, error handling, missing dimensions |
| `ml-engine/tests/test_backend_integration.py` | 19 | Backend Pydantic serialization, SQL seed parity, Anshika fixes |
| `ml-engine/tests/test_explainability.py` | 8 | Rule-based summaries, limitation generation, warning propagation |
| `ml-engine/tests/test_preprocessing.py` | 36 | Planet-aware envelopes, strict range checks, normalization |
| `ml-engine/tests/test_ranking.py` | 8 | Score sorting, deterministic tie-breaking, limit, threshold |
| `ml-engine/tests/test_reporting.py` | 6 | SiteReport generation, plain-text layout, source attribution |
| `ml-engine/tests/test_scientific_data.py` | 21 | NASA POWER parsing, Diviner XYZ query, real profiles, route simulation |
| `ml-engine/tests/test_similarity.py` | 60 | Slope-only Gaussian topography, direct mineral cosine, climate continuity |
| `backend/tests/test_schemas.py` | 3 | Search request validation, zero weights rejection, planet validation |
| `backend/tests/test_scoring.py` | 5 | Topography match, geochemistry match, climate match, accessibility |
| **Total Test Suite** | **182** | **100% PASSING (2.27s)** |

---

## 7. Exact Commands to Run

### Run Complete Combined Test Suite
```bash
python -m pytest backend/tests/test_schemas.py backend/tests/test_scoring.py ml-engine/tests -v
```

### Run Real Dataset Evaluation
```bash
python ml-engine/examples/evaluate_real_datasets.py
```

### Run Synthetic Demonstration Script
```bash
python ml-engine/examples/synthetic_demo.py
```

# AstroTerrain ML Engine -- Module 4
## Spatial Machine Learning Engine & Technical Report Generator

**Project:** AstroTerrain (NASA Space Apps Challenge 2026)  
**Module Owner:** Ananya (Module 4 -- Machine Learning & Spatial Similarity)  
**Collaborating Developers:**
* **Module 1 (Frontend & UI/UX):** Manan
* **Module 2 (3D GIS & Globe):** Pranjil
* **Module 3 (Backend & Database):** Anshika
* **Module 4 (Spatial ML & Reporting):** Ananya (THIS MODULE)

**Status:** Pre-Real-Data Architecture Complete, Fully Tested, Integration-Ready  
**Test Suite:** 128/128 Tests Passing (ML Engine) + 8/8 Tests Passing (Backend Scoring & Schemas)

---

## 1. Executive Summary & Module Role

AstroTerrain is a planetary-site comparison platform that identifies terrestrial analogues for lunar and Martian exploration sites. The system evaluates Earth candidates against extraterrestrial targets (e.g., Shackleton Crater at the Lunar South Pole, Jezero Crater on Mars, and Martian lava-tube environments) across three scientific dimensions:

1. **Topography:** Elevation and slope derived from Digital Elevation Models (DEMs).
2. **Geochemistry:** Mineralogical composition vectors and geological rock classifications.
3. **Climate:** Thermal envelope and temperature range overlap analysis.

Module 4 is responsible for the complete comparison and explainability pipeline:
* Preprocessing, unit standardization, and data-quality validation.
* Multi-criteria similarity scoring with mathematical continuity and monotonicity.
* Dynamic weight renormalization when measurements are unavailable (no arbitrary score imputation).
* Deterministic candidate ranking and tie-breaking.
* Transparent, template-driven explainability without hallucinating LLMs.
* Automated mission site reports (structured data, plain-text rendering, optional PDF).
* Full drop-in compatibility with the backend (Module 3 -- Anshika).

---

## 2. Resolutions for Backend Integration (Anshika's 5 Items)

In review with backend engineer Anshika, five critical integration items were identified and fully resolved:

### Item 1: Package Structure & Namespace Separation
* **Issue:** `ml-engine` previously used an internal top-level directory named `app/`, colliding with the backend's `backend/app/` package when both were placed in Python's search path.
* **Resolution:** Renamed `ml-engine/app` to `ml-engine/ml_engine`. Added `pyproject.toml` and standard package configuration. The backend and ML Engine can now be imported simultaneously in the same Python process without namespace collisions or import hacks.

### Item 2: Removal of Artificial 50-Point Fallback
* **Issue:** Unavailable comparison dimensions previously defaulted to a 50.0 score in `adapter.py`, allowing candidates with missing data to artificially achieve 50% match scores and pollute search results.
* **Resolution:** Completely removed `_UNAVAILABLE_FALLBACK = 50.0`. When a dimension is unavailable due to missing data, its match score in the breakdown is set to `0.0`. If no positively-weighted dimensions can be computed, `similarity_score` is set to `0.0` and `insufficient_data = True` is flagged in `ml_engine_metadata`. Candidates with insufficient data are excluded when `min_score` is applied.

### Item 3: Direct 0-100 Mineral Cosine Similarity Mapping
* **Issue:** Mineral composition vectors contain non-negative concentrations ($v_i \ge 0$), meaning cosine similarity naturally ranges in $[0.0, 1.0]$. The previous formula mapped $\cos(\theta) \in [-1, 1]$ to $[0, 100]$ via $(\cos\theta + 1)/2 \times 100$, causing orthogonal (completely disjoint) mineral compositions to score 50% match.
* **Resolution:** Replaced the bipolar mapping with direct linear mapping:
  $$S_{\text{mineral}} = \cos(\theta) \times 100.0$$
  Orthogonal vectors (no shared minerals) now score exactly **0.0%**, while identical mineral vectors score **100.0%**.

### Item 4: Strict Physical Measurement Validation
* **Issue:** Out-of-range sensor readings were flagged but previously returned raw values into profiles, allowing unphysical measurements to enter calculations.
* **Resolution:** `_get_valid_float` strictly requires `quality == DataQuality.VALID`. Out-of-range measurements are set to `None` in the profile and excluded from scoring calculations. An optional `strict: bool = True` parameter is available to immediately raise `ValueError` on unphysical inputs. Planet-specific bounds differentiate lunar extreme vacuum conditions from Martian atmosphere.

### Item 5: End-to-End Complete Repository Integration Tests
* **Issue:** Integration tests were previously mocked or run in isolation.
* **Resolution:** Created `test_backend_integration.py` which runs from the complete AstroTerrain repository. It directly imports backend Pydantic schemas (`SimilarityBreakdown`, `AnalogMetadata`, `AnalogResult`, `AnalogSearchResponse`), feeds real database seed fixtures (`002_seed_demo_data.sql`), verifies mathematical continuity of climate matching, tests deterministic ranking, and confirms zero namespace collision between `app` and `ml_engine`.

---

## 3. Scientific Review: Topography Weighting & Elevation Datum Compatibility

### The Planetary Elevation Datum Problem
Terrestrial and planetary elevations cannot be directly compared as equivalent physical altitudes because they are referenced to fundamentally different datums:
* **Earth:** Elevations are referenced to the **Earth Geoid** (mean sea level approximated by WGS84 ellipsoid).
* **Moon:** Elevations are referenced to a fixed reference sphere of **radius 1,737.4 km** (derived from LRO LOLA laser altimetry).
* **Mars:** Elevations are referenced to the **MOLA Aeroid** (defined by the gravity potential where atmospheric pressure equals the triple point of water, 610.5 Pa, or an equivalent 3,396.0 km reference radius).

Because an Earth mountain at +2,500m above sea level shares no physical zero-reference with a Martian crater at -2,500m relative to the MOLA aeroid, comparing raw absolute elevations produces arbitrary comparisons unless anchored to local morphological relief.

### The Topographic Solution: Slope-Dominant Weighting
Geometric slope (terrain gradient in degrees) is scale- and datum-invariant: a 12 deg slope on Moon represents the exact same gravitational incline as a 12 deg slope on Earth.

Therefore, Module 4 adopts a calibrated 70/30 topographic weighting:
* **Slope Weight:** **70%** (`DEFAULT_SLOPE_WEIGHT = 0.70`) -- Primary transferable morphological metric.
* **Elevation Weight:** **30%** (`DEFAULT_ELEVATION_WEIGHT = 0.30`) -- Secondary metric, serving as a coarse proxy for terrestrial high-altitude / cold desert conditions.
* **Diagnostic Notice:** Whenever elevation is evaluated, the ML Engine automatically attaches a scientific datum warning into the calculation metadata:
  > *"Notice: Target and candidate elevations are referenced to distinct planetary datums (e.g. lunar 1737.4 km sphere vs Earth geoid). Geometric slope angle is the primary transferable topographic metric."*

---

## 4. Directory Structure

```text
ml-engine/
|-- ml_engine/                    # Core Python package (renamed from app/)
|   |-- __init__.py               # Package metadata and public API exports
|   |-- adapter.py                # Drop-in integration adapter for backend scoring
|   |-- comparison/               # Core similarity engines
|   |   |-- __init__.py
|   |   |-- climate.py            # Continuous interval-overlap temperature engine
|   |   |-- geochemistry.py       # Direct mineral cosine similarity (0-100) & rock-type engine
|   |   |-- similarity.py         # Multi-criteria weighted aggregation & weight renormalization
|   |   `-- topography.py         # 70/30 Slope-dominant calibrated Gaussian topography engine
|   |-- explainability/           # Structured explanation generator
|   |   |-- __init__.py
|   |   `-- explanations.py       # Rule-based diagnostic summaries & warnings
|   |-- models/                   # Pydantic v2 domain schemas
|   |   |-- __init__.py
|   |   `-- schemas.py            # PlanetaryTarget, EarthCandidate, SimilarityResult, SiteReport
|   |-- preprocessing/            # Ingestion, validation, and normalization
|   |   |-- __init__.py
|   |   |-- feature_validation.py # Strict range checks, planet-specific bounds, type validation
|   |   |-- missing_values.py     # Missing-feature audits (no silent zero/heuristic imputation)
|   |   `-- normalization.py      # Fixed physical-bound feature normalizers
|   |-- ranking/                  # Candidate ranking engine
|   |   |-- __init__.py
|   |   `-- candidate_ranking.py  # Deterministic score-descending & site_id sorting
|   `-- reporting/                # Automated mission report generation
|       |-- __init__.py
|       `-- site_reports.py       # Structured SiteReport models, text, and PDF renderer
|-- examples/
|   `-- synthetic_demo.py         # End-to-end runnable demonstration script
|-- tests/
|   |-- test_adapter.py           # Backend adapter contract & error handling tests
|   |-- test_backend_integration.py # Full backend integration tests (schemas, SQL seeds, Anshika fixes)
|   |-- test_explainability.py    # Diagnostic summary and warning propagation tests
|   |-- test_preprocessing.py     # Range validation, physical bounds, normalization tests
|   |-- test_ranking.py           # Deterministic sorting, limit, and threshold tests
|   |-- test_reporting.py         # Site report generation and text rendering tests
|   `-- test_similarity.py        # Mathematical continuity, weights, direct cosine tests
|-- conftest.py                   # Pytest path configuration
|-- pyproject.toml                # Standard build configuration & package definition
|-- requirements.txt              # Production and test dependencies
|-- .gitignore                    # Build and cache exclusion rules
`-- README.md                     # Comprehensive technical documentation
```

---

## 5. Mathematical & Scientific Methodology

### A. Critical Scientific Safeguards

#### 1. NDVI is NOT Geochemistry
* **Scientific Reality:** NDVI (Normalized Difference Vegetation Index) measures chlorophyll reflectance and vegetation density on Earth. The Moon and Mars have zero vegetation.
* **Engine Policy:** If candidate `spectral_signature` contains only NDVI keys (`mean_ndvi`, `min_ndvi`, `max_ndvi`, `valid_pixels`), the ML Engine **strictly rejects** using it as geochemistry. It issues an explicit data-quality warning and falls back to categorical rock matching (or marks the dimension `UNAVAILABLE`).

#### 2. No Silent Data Imputation
* **Scientific Reality:** Fabricating missing environmental measurements introduces false scientific claims.
* **Engine Policy:** When a dimension lacks required data, its status is set to `UNAVAILABLE`. It is excluded from the numerator and denominator, and weights are dynamically renormalized over computable dimensions.

#### 3. Moon vs. Mars Physical Differentiation
The engine validates targets against distinct planetary physical envelopes:
* **Moon:** Elevation [-12,000m to +15,000m], Temperature [-250 deg C to +150 deg C] (vacuum thermal regime).
* **Mars:** Elevation [-10,000m to +25,000m], Temperature [-150 deg C to +40 deg C] (thin atmosphere).

---

### B. Comparison Engines

#### 1. Topography Similarity
Calculated via Gaussian exponential-decay functions:
$$\text{Sim}(a, b, \sigma) = 100 \times \exp\left( -\frac{(a - b)^2}{2\sigma^2} \right)$$
* **Slope Difference:** $\sigma = 5.0^{\circ}$ (70% weight) -- Primary transferable metric.
* **Elevation Difference:** $\sigma = 2000.0\text{ m}$ (30% weight) -- Secondary metric.

#### 2. Geochemistry & Mineralogy Similarity
* **Mineral Composition Vectors:** Evaluated using linear-algebra cosine similarity across the combined mineral space:
  $$\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|} = \frac{\sum_{k} u_k v_k}{\sqrt{\sum_k u_k^2} \sqrt{\sum_k v_k^2}}$$
  Mapped directly to percentage:
  $$S_{\text{mineral}} = \cos(\theta) \times 100.0$$
* **Categorical Rock Classification:** Fallback when quantitative mineral percentages are absent:
  - Exact rock type match (e.g., basalt to basalt): $90.0$
  - Same geological family (e.g., basalt to basaltic sediment): $60.0$
  - Different geological family: $20.0$

#### 3. Climate Similarity (Continuous Interval Overlap)
Compares planetary temperature range $[T_{\min}, T_{\max}]$ with candidate $[C_{\min}, C_{\max}]$:
* **Overlapping Ranges:**
  $$S = 35.0 + 65.0 \times \frac{\text{Overlap}}{\text{Union}} \quad \in [35.0, 100.0]$$
* **Non-Overlapping Ranges (with gap):**
  $$S = 35.0 \times \exp\left( -\frac{\text{Gap}^2}{2\sigma_{\text{gap}}^2} \right) \quad \in [0.0, 35.0)$$
  where $\sigma_{\text{gap}} = 30.0^{\circ}\text{C}$.
* **Boundary Property:** At exact boundary contact ($\text{Gap} = 0, \text{Overlap} = 0$), both formulas yield exactly $35.0$. The metric is strictly monotonic and continuous everywhere.

---

### C. Multi-Criteria Aggregation & Dynamic Renormalization

For requested weights $w_{\text{topo}}, w_{\text{geo}}, w_{\text{clim}} \ge 0$:
1. Let $\mathcal{A}$ be the set of dimensions where $S_i$ was successfully computed and $w_i > 0$.
2. If $\mathcal{A} = \emptyset$, return `overall_score = None`.
3. Compute total active weight: $W_{\text{active}} = \sum_{i \in \mathcal{A}} w_i$.
4. Effective weight for each dimension: $w_i^{\text{eff}} = \frac{w_i}{W_{\text{active}}}$.
5. Overall similarity:
   $$S = \sum_{i \in \mathcal{A}} w_i^{\text{eff}} \times S_i$$
6. If any requested dimension was unavailable, the result is flagged as `is_complete = False` and diagnostic warnings document the renormalized weights.

---

### D. Deterministic Candidate Ranking

Given a list of candidates:
1. Each candidate is evaluated against the target.
2. If `min_score` threshold is specified: candidates with `overall_score < min_score` or `overall_score is None` are filtered out.
3. If `min_score is None`: scored candidates appear first, followed by unscored candidates.
4. Primary sorting key: `overall_score` descending.
5. Deterministic tie-breaking key: `candidate_site_id` ascending.
6. Result limit $k$ is applied to the sorted list.
7. Sequential ranks $1, 2, \dots, N$ are assigned.

---

## 6. Backend Integration Guide (Module 3 -- Anshika)

The ML Engine provides a 100% contract-compliant drop-in replacement for `backend/app/services/scoring.py`.

### A. Contract Conformance
Backend expects:
```python
score_analog(target: Mapping[str, Any], analog: Mapping[str, Any], weights: Mapping[str, float]) -> dict[str, Any]
```

Returns:
```python
{
    "similarity_score": 72.05,
    "breakdown": {
        "topography_match": 67.13,
        "geochemistry_match": 90.0,
        "climate_match": 54.78
    },
    "ml_engine_metadata": {
        "insufficient_data": False,
        "is_complete": True,
        "dimensions_computed": 3,
        "dimensions_unavailable": 0,
        "unavailable_dimensions": [],
        "warnings": [...],
        "explanation": {...}
    }
}
```

* All scores are guaranteed to be finite floats bounded within $[0.0, 100.0]$.
* Preserves all three breakdown keys (`topography_match`, `geochemistry_match`, `climate_match`).
* Returns `0.0` for unavailable dimensions (no artificial 50.0 fallback).
* Extra key `ml_engine_metadata` is non-breaking and available for frontend explainability or logging.
* For complete interface parity, `adapter.py` also exports:
  * `accessibility_rating(score) -> str`
  * `topography_match(target, analog) -> float`
  * `geochemistry_match(target, analog) -> float`
  * `climate_match(target, analog) -> float`

### B. Integration Checklist for Anshika
- [x] Package conflict resolved (`ml_engine` vs `app`).
- [x] Artificial 50.0 fallback removed.
- [x] Direct 0-100 cosine mapping active.
- [x] Strict physical range validation active.
- [x] Integration tests pass with real backend Pydantic models.
- [ ] In `backend/app/api/routes/analogs.py`: update import to use `ml_engine.adapter.score_analog`.

---

## 7. Verification & Test Results

The ML Engine includes a test suite with **128 automated unit and integration tests** in pytest:

| Test File | Tests | Coverage / Verification |
| :--- | :---: | :--- |
| `test_adapter.py` | 16 | Backend contract, 0.0 uncomputed dimensions, weights, error handling |
| `test_backend_integration.py` | 19 | Live backend Pydantic models, SQL seed data, Anshika 5 issues |
| `test_explainability.py` | 8 | Summary generation, categorization, warning propagation |
| `test_preprocessing.py` | 36 | Strict physical bounds, Moon/Mars differentiation, normalization |
| `test_ranking.py` | 8 | Score sorting, deterministic tie-breaking, limit, threshold |
| `test_reporting.py` | 6 | SiteReport generation, plain-text layout, source attribution |
| `test_similarity.py` | 35 | Topography Gaussian, direct mineral cosine (0-100), interval overlap |
| **Total ML Engine Tests** | **128** | **100% passing (0.38s)** |

Additionally, existing backend unit tests pass without errors:
* `backend/tests/test_scoring.py`: 5 passed
* `backend/tests/test_schemas.py`: 3 passed

---

## 8. Exact Commands to Run

### Run Complete ML Engine Test Suite
```bash
python -m pytest AstroTerrain-main/ml-engine/tests -v
```

### Run Backend Unit Tests
```bash
python -m pytest AstroTerrain-main/backend/tests/test_scoring.py AstroTerrain-main/backend/tests/test_schemas.py -v
```

### Run Synthetic Demonstration Script
```bash
cd AstroTerrain-main
python ml-engine/examples/synthetic_demo.py
```

---

## 9. Real NASA/ESA Dataset Ingestion Roadmap

When real planetary remote-sensing datasets arrive from NASA and ESA, follow this roadmap to transition from synthetic fixtures to production observations:

1. **Target DEM Rasters (LOLA / MOLA):**
   * Lunar South Pole / Shackleton Crater: Ingest LRO LOLA DEM (20m/pixel). Extract slope and roughness.
   * Mars Jezero Crater: Ingest Mars Reconnaissance Orbiter / Mars Express HRSC DEM (50m/pixel).
2. **Target Mineralogy (CRISM / M3):**
   * Ingest mineral percentage maps from Mars CRISM or Chandrayaan-1 $M^3$ imaging spectrometers. Populate `regolith_composition` with validated mineral keys (`basalt_pct`, `olivine_pct`, `pyroxene_pct`, `plagioclase_pct`, `iron_oxide_pct`).
3. **Earth Candidate Hyperspectral Data (USGS / NASA EMIT / AVIRIS):**
   * Replace NDVI vegetation summaries with true surface mineral reflection spectra in `spectral_signature`.
4. **Gaussian Dispersion Calibration ($\sigma$):**
   * Re-tune `SLOPE_SIGMA_DEG` (currently 5.0 deg) and `ELEVATION_SIGMA_M` (currently 2000.0m) using ground-truth analogue site pairs established by planetary geology literature.
5. **Microclimate Datasets (ERA5-Land):**
   * Replace coarse annual min/max with diurnal cycle and thermal inertia parameters.

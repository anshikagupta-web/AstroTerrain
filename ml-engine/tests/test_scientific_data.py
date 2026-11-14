"""Tests for Scientific Data Ingestion, Profiling, Constraints, and Backend Integration.

Verifies:
1. NASA POWER CSV parsing and meteorological statistics calculation.
2. Diviner bolometric thermal anomaly spatial grid lookup and interpretation constraints.
3. Real Earth candidate records and real planetary target profiles.
4. Database-to-ML feature mapping and strict/lenient physical validation.
5. Scientific constraints: datum exclusion, slope-only topography, NDVI non-equivalence,
   Diviner brightness-temperature anomaly isolation.
6. Backend route integration simulation and deterministic candidate ranking.
7. Out-of-range sensor readings, invalid units, and missing dimension resilience.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
import pytest

# Ensure ml_engine and backend are on path
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ML_ENGINE_ROOT = _REPO_ROOT / "ml-engine"
_BACKEND_ROOT = _REPO_ROOT / "backend"

if str(_ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ENGINE_ROOT))
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from ml_engine.adapter import score_analog, accessibility_rating
from ml_engine.data_loader import (
    get_data_dir,
    get_real_earth_candidates,
    get_real_planetary_targets,
    load_nasa_power_climate,
    query_diviner_anomaly,
)
from ml_engine.models.schemas import (
    DimensionStatus,
    EarthCandidate,
    Planet,
    PlanetaryTarget,
)
from ml_engine.preprocessing.feature_validation import (
    validate_candidate_features,
    validate_target_features,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity
from app.schemas.search import (
    AnalogMetadata,
    AnalogResult,
    AnalogSearchRequest,
    AnalogSearchResponse,
    SearchConstraints,
    SearchWeights,
    SimilarityBreakdown,
)
from app.schemas.common import Coordinates


# ===========================================================================
# 1. NASA POWER CSV Climate Ingestion Tests
# ===========================================================================

class TestNASAPowerIngestion:
    """Verify parsing of real NASA POWER daily meteorological datasets."""

    @pytest.fixture
    def data_dir(self) -> Path:
        return get_data_dir()

    def test_hawaii_climate_data(self, data_dir: Path):
        csv_path = data_dir / "earth" / "nasa_power" / "hawaii_temperature.csv"
        assert csv_path.exists(), f"Missing {csv_path}"
        stats = load_nasa_power_climate(csv_path)

        assert stats["valid_days_count"] == 2192  # 6 years (2020-2025 inclusive)
        assert 15.0 < stats["mean_temp_c"] < 22.0
        assert stats["observed_min_temp_c"] == 10.34
        assert stats["observed_max_temp_c"] == 27.28
        assert stats["temp_range_c"] == (10.34, 27.28)

    def test_svalbard_climate_data(self, data_dir: Path):
        csv_path = data_dir / "earth" / "nasa_power" / "svalbard_temperature.csv"
        assert csv_path.exists(), f"Missing {csv_path}"
        stats = load_nasa_power_climate(csv_path)

        assert stats["valid_days_count"] == 2192
        assert -10.0 < stats["mean_temp_c"] < 0.0
        assert stats["observed_min_temp_c"] == -30.40
        assert stats["observed_max_temp_c"] == 11.44

    def test_atacama_climate_data(self, data_dir: Path):
        csv_path = data_dir / "earth" / "nasa_power" / "atacama_temperature.csv"
        assert csv_path.exists(), f"Missing {csv_path}"
        stats = load_nasa_power_climate(csv_path)

        assert stats["valid_days_count"] == 2192
        assert 10.0 < stats["mean_temp_c"] < 20.0
        assert stats["observed_min_temp_c"] == -2.73
        assert stats["observed_max_temp_c"] == 35.20

    def test_antarctica_climate_data(self, data_dir: Path):
        csv_path = data_dir / "earth" / "nasa_power" / "antarctica_temperature.csv"
        assert csv_path.exists(), f"Missing {csv_path}"
        stats = load_nasa_power_climate(csv_path)

        assert stats["valid_days_count"] == 2192
        assert -35.0 < stats["mean_temp_c"] < -20.0
        assert stats["observed_min_temp_c"] == -54.33
        assert stats["observed_max_temp_c"] == -7.39

    def test_missing_csv_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_nasa_power_climate("non_existent_file.csv")

    def test_malformed_csv_raises_value_error(self, tmp_path: Path):
        bad_file = tmp_path / "bad.csv"
        bad_file.write_text("No header delimiter\nT2M,T2M_MIN,T2M_MAX\n1,2,3", encoding="utf-8")
        with pytest.raises(ValueError, match="missing '-END HEADER-'"):
            load_nasa_power_climate(bad_file)


# ===========================================================================
# 2. Diviner Bolometric Thermal Anomaly Ingestion Tests
# ===========================================================================

class TestDivinerAnomalyIngestion:
    """Verify spatial query of Diviner thermal anomaly grids."""

    @pytest.fixture
    def data_dir(self) -> Path:
        return get_data_dir()

    def test_diviner_south_pole_max_anomaly(self, data_dir: Path):
        xyz_path = data_dir / "lunar" / "diviner" / "diviner_tbol_max_anom.xyz"
        assert xyz_path.exists(), f"Missing {xyz_path}"
        val, lon, lat = query_diviner_anomaly(xyz_path, target_lon=-0.25, target_lat=-89.75)

        assert val is not None
        assert abs(val - 28.267) < 0.05
        assert lon == -0.25
        assert lat == -89.75

    def test_diviner_south_pole_min_anomaly(self, data_dir: Path):
        xyz_path = data_dir / "lunar" / "diviner" / "diviner_tbol_min_anom.xyz"
        assert xyz_path.exists(), f"Missing {xyz_path}"
        val, lon, lat = query_diviner_anomaly(xyz_path, target_lon=-0.25, target_lat=-89.75)

        assert val is not None
        assert abs(val - 2.905) < 0.05
        assert lon == -0.25
        assert lat == -89.75

    def test_diviner_anomaly_out_of_bounds_returns_none(self, data_dir: Path):
        xyz_path = data_dir / "lunar" / "diviner" / "diviner_tbol_max_anom.xyz"
        val, _, _ = query_diviner_anomaly(xyz_path, target_lon=45.0, target_lat=0.0, max_dist_deg=0.1)
        assert val is None


# ===========================================================================
# 3. Real Profiles and Scientific Integrity Tests
# ===========================================================================

class TestRealScientificProfiles:
    """Verify properties and provenance of the 4 real candidates and 4 targets."""

    def test_earth_candidate_count_and_provenance(self):
        cands = get_real_earth_candidates()
        assert len(cands) == 4

        site_ids = {c["site_id"] for c in cands}
        assert site_ids == {
            "real-analog-hawaii",
            "real-analog-svalbard",
            "real-analog-atacama",
            "real-analog-antarctica",
        }

        for c in cands:
            assert c["data_source"] == "copernicus_glo90_nasa_power"
            # NDVI is None because aligned Red/NIR reflectance is not available
            assert c["ndvi"] is None
            # Mineral composition is empty because calibrated spectral cubes are not available
            assert c["spectral_signature"] == {}
            # Slope and elevation are valid numbers
            assert c["slope_deg"] >= 0.0
            assert -500.0 < c["elevation_m"] < 9000.0
            # Temperatures are valid physical values
            assert c["temp_min_c"] <= c["temp_max_c"]

    def test_planetary_targets_count_and_provenance(self):
        targets = get_real_planetary_targets()
        assert len(targets) == 4

        target_ids = {t["site_id"] for t in targets}
        assert target_ids == {
            "moon-shackleton-real",
            "moon-marius-hills-real",
            "mars-jezero-real",
            "mars-pavonis-tubes-real",
        }

        jezero = next(t for t in targets if t["site_id"] == "mars-jezero-real")
        assert jezero["planet"] == "mars"
        assert jezero["elevation_m"] == -2500.0
        assert jezero["avg_slope_deg"] == 6.0
        assert jezero["temp_range_c"] == [-85, 10]
        assert "crism_product" in jezero["scientific_metadata"]

        shackleton = next(t for t in targets if t["site_id"] == "moon-shackleton-real")
        assert shackleton["planet"] == "moon"
        assert shackleton["elevation_m"] == -4000.0
        assert shackleton["avg_slope_deg"] == 12.5
        assert shackleton["temp_range_c"] == [-248, 100]
        assert "diviner_tbol_max_anom_k" in shackleton["scientific_metadata"]


# ===========================================================================
# 4. Scientific Constraints and Guardrails Tests
# ===========================================================================

class TestScientificGuardrails:
    """Verify critical scientific constraints are strictly enforced."""

    def test_datum_mismatch_warning_emitted_for_cross_planetary(self):
        """Cross-planetary comparisons emit a geodetic datum mismatch notice."""
        targets = get_real_planetary_targets()
        candidates = get_real_earth_candidates()

        jezero = next(t for t in targets if t["site_id"] == "mars-jezero-real")
        hawaii = next(c for c in candidates if c["site_id"] == "real-analog-hawaii")

        scored = score_analog(jezero, hawaii, {"topography": 0.4, "climate": 0.3, "geochemistry": 0.3})
        warnings = scored["ml_engine_metadata"]["warnings"]

        assert any("distinct planetary datums" in w for w in warnings)
        assert any("Absolute elevation is excluded from cross-planetary scoring" in w for w in warnings)

    def test_slope_only_topography_insensitivity_to_absolute_elevation(self):
        """Slope similarity is completely independent of raw elevation differences."""
        target = {
            "planet": "mars",
            "site_id": "test-target",
            "site_name": "Test Target",
            "avg_slope_deg": 10.0,
            "elevation_m": -2000.0,
        }
        cand_low_elev = {
            "site_id": "cand-low",
            "site_name": "Low Elevation",
            "slope_deg": 10.0,
            "elevation_m": 50.0,
        }
        cand_high_elev = {
            "site_id": "cand-high",
            "site_name": "High Elevation",
            "slope_deg": 10.0,
            "elevation_m": 4500.0,
        }

        weights = {"topography": 1.0, "geochemistry": 0.0, "climate": 0.0}
        score_low = score_analog(target, cand_low_elev, weights)["similarity_score"]
        score_high = score_analog(target, cand_high_elev, weights)["similarity_score"]

        assert score_low == 100.0
        assert score_high == 100.0
        assert score_low == score_high

    def test_missing_slope_marks_topography_unavailable(self):
        """Missing slope is never treated as slope 0.0 or replaced with elevation fallback."""
        target = {
            "planet": "mars",
            "site_id": "test-target",
            "site_name": "Test Target",
            "elevation_m": -2000.0,
            # avg_slope_deg missing
        }
        cand = {
            "site_id": "cand-1",
            "site_name": "Candidate 1",
            "slope_deg": 10.0,
            "elevation_m": 50.0,
        }
        weights = {"topography": 1.0, "geochemistry": 0.0, "climate": 0.0}
        scored = score_analog(target, cand, weights)

        assert scored["breakdown"]["topography_match"] == 0.0
        assert "topography" in scored["ml_engine_metadata"]["unavailable_dimensions"]
        assert scored["ml_engine_metadata"]["insufficient_data"] is True

    def test_ndvi_cannot_be_used_as_mineralogy(self):
        """NDVI spectral signature triggers explicit warning and leaves mineral dimension unavailable."""
        target = {
            "planet": "moon",
            "site_id": "target-moon",
            "site_name": "Target Moon",
            "primary_rock": "basalt",
            "regolith_composition": {"anorthite": 60.0},
        }
        cand_ndvi_only = {
            "site_id": "cand-ndvi",
            "site_name": "Candidate NDVI",
            "primary_rock": "basalt",
            "spectral_signature": {"mean_ndvi": 0.15},
        }
        scored = score_analog(target, cand_ndvi_only, {"topography": 0.4, "climate": 0.3, "geochemistry": 0.3})
        warnings = scored["ml_engine_metadata"]["warnings"]

        assert any("NDVI (vegetation index)" in w for w in warnings)
        assert any("NDVI cannot be used for mineralogical comparison" in w for w in warnings)

    def test_diviner_anomaly_not_confused_with_absolute_temperature(self):
        """Diviner bolometric brightness-temperature anomaly in Kelvin is not treated as degC surface temp."""
        targets = get_real_planetary_targets()
        shackleton = next(t for t in targets if t["site_id"] == "moon-shackleton-real")

        # The scientific metadata has the anomaly values in Kelvin
        meta = shackleton["scientific_metadata"]
        assert "diviner_tbol_max_anom_k" in meta
        assert meta["diviner_tbol_max_anom_k"] > 0
        assert "not absolute temperatures" in meta["diviner_note"]

        # The temperature range is the physical cryogenic PSR to illuminated rim in degC
        assert shackleton["temp_range_c"] == [-248, 100]


# ===========================================================================
# 5. Database-to-ML Ingestion and Schema Mapping
# ===========================================================================

class TestDatabaseToMLMapping:
    """Verify that records structured like PostgreSQL/PostGIS rows map cleanly into ML profiles."""

    def test_sql_target_row_maps_to_target_profile(self):
        sql_target_row = {
            "planet": "mars",
            "site_id": "mars-jezero-real",
            "site_name": "Jezero Crater Delta",
            "lat": 18.38,
            "lng": 77.58,
            "elevation_m": -2500.0,
            "avg_slope_deg": 6.0,
            "temp_range_c": [-85.0, 10.0],
            "primary_rock": "basaltic sediment",
            "regolith_composition": {},
            "data_source": "nasa_mgs_mola_meda_pds",
        }
        profile, reports = validate_target_features(sql_target_row, strict=False)

        assert profile.planet == Planet.MARS
        assert profile.site_id == "mars-jezero-real"
        assert profile.avg_slope_deg == 6.0
        assert profile.elevation_m == -2500.0
        assert profile.temp_range_c == (-85.0, 10.0)
        assert profile.primary_rock == "basaltic sediment"
        assert profile.regolith_composition == {}

    def test_sql_candidate_row_maps_to_candidate_profile(self):
        sql_candidate_row = {
            "site_id": "real-analog-hawaii",
            "site_name": "Hawaii Volcanic Field",
            "country": "United States",
            "lat": 19.5,
            "lng": -155.5,
            "elevation_m": 3210.327,
            "slope_deg": 8.365,
            "temp_min_c": 10.34,
            "temp_max_c": 27.28,
            "primary_rock": "basalt",
            "ndvi": None,
            "spectral_signature": {},
            "accessibility_score": 85.0,
            "is_subterranean": False,
            "data_source": "copernicus_glo90_nasa_power",
        }
        profile, reports = validate_candidate_features(sql_candidate_row, strict=False)

        assert profile.site_id == "real-analog-hawaii"
        assert profile.elevation_m == 3210.327
        assert profile.slope_deg == 8.365
        assert profile.temp_min_c == 10.34
        assert profile.temp_max_c == 27.28
        assert profile.primary_rock == "basalt"
        assert profile.accessibility_score == 85.0
        assert profile.is_subterranean is False

    def test_out_of_range_sensor_values_handled_properly(self):
        """Invalid physical values are rejected in strict mode and sanitised in lenient mode."""
        bad_candidate = {
            "site_id": "bad-sensor",
            "site_name": "Bad Sensor Site",
            "lat": 0.0,
            "lng": 0.0,
            "elevation_m": 50000.0,  # >30,000m on Earth
            "slope_deg": 120.0,       # >90 deg
            "temp_min_c": 150.0,      # >70 degC on Earth
            "temp_max_c": 200.0,
        }

        # Strict mode raises ValueError
        with pytest.raises(ValueError, match="out_of_range"):
            validate_candidate_features(bad_candidate, strict=True)

        # Lenient mode strips the invalid features to None
        profile, reports = validate_candidate_features(bad_candidate, strict=False)
        assert profile.elevation_m is None
        assert profile.slope_deg is None
        assert profile.temp_min_c is None
        assert profile.temp_max_c is None
        assert len(reports) >= 3


# ===========================================================================
# 6. Backend Route Integration Simulation and Response Contract
# ===========================================================================

class TestBackendRouteIntegrationSimulation:
    """Simulate the exact /api/v1/analogs/search flow using backend schemas and ML adapter."""

    def test_end_to_end_search_simulation_with_real_records(self):
        targets = get_real_planetary_targets()
        candidates = get_real_earth_candidates()

        target = next(t for t in targets if t["site_id"] == "mars-jezero-real")

        request = AnalogSearchRequest(
            target_planet="mars",
            target_site_id="mars-jezero-real",
            weights=SearchWeights(topography=0.4, geochemistry=0.3, climate=0.3),
            constraints=SearchConstraints(min_similarity=20.0, limit=10),
        )

        ranked: list[AnalogResult] = []
        for cand in candidates:
            scored = score_analog(target, cand, request.weights.model_dump())
            if scored["similarity_score"] < request.constraints.min_similarity:
                continue

            ml_meta = scored.get("ml_engine_metadata") or {}
            result = AnalogResult(
                site_id=cand["site_id"],
                name=cand["site_name"],
                country=cand.get("country") or "Unknown",
                coordinates=Coordinates(lat=cand["lat"], lng=cand["lng"]),
                similarity_score=scored["similarity_score"],
                breakdown=SimilarityBreakdown(**scored["breakdown"]),
                metadata=AnalogMetadata(
                    elevation_m=cand.get("elevation_m"),
                    primary_rock=cand.get("primary_rock"),
                    accessibility_rating=accessibility_rating(cand.get("accessibility_score")),
                    data_source=cand.get("data_source"),
                    unavailable_dimensions=ml_meta.get("unavailable_dimensions", []),
                    warnings=ml_meta.get("warnings", []),
                    is_complete=ml_meta.get("is_complete", True),
                ),
                ml_engine_metadata=ml_meta if ml_meta else None,
            )
            ranked.append(result)

        # Deterministic sorting
        ranked.sort(key=lambda item: (-item.similarity_score, item.site_id))
        results = ranked[: request.constraints.limit]
        response = AnalogSearchResponse(
            target_site_name=target["site_name"],
            results_count=len(results),
            analogs=results,
        )

        # Verify contract compatibility
        assert response.target_site_name == target["site_name"]
        assert response.results_count == 4
        assert len(response.analogs) == 4

        # Top ranked should be Hawaii or Antarctica
        top = response.analogs[0]
        assert top.similarity_score > 50.0
        assert top.breakdown.topography_match > 70.0
        assert top.metadata.data_source == "copernicus_glo90_nasa_power"
        assert top.metadata.is_complete is False  # Incomplete because climate has physical measurement type mismatch
        assert "climate" in top.metadata.unavailable_dimensions
        assert top.breakdown.climate_match == 0.0
        assert len(top.metadata.warnings) > 0

    def test_deterministic_tie_breaking(self):
        """Candidates with identical scores are sorted alphabetically by site_id."""
        target = {
            "planet": "mars",
            "site_id": "test-target",
            "site_name": "Test Target",
            "avg_slope_deg": 5.0,
        }
        cand_z = {"site_id": "site-z", "site_name": "Site Z", "slope_deg": 5.0}
        cand_a = {"site_id": "site-a", "site_name": "Site A", "slope_deg": 5.0}
        cand_m = {"site_id": "site-m", "site_name": "Site M", "slope_deg": 5.0}

        ranked: list[AnalogResult] = []
        for cand in [cand_z, cand_a, cand_m]:
            scored = score_analog(target, cand, {"topography": 1.0, "geochemistry": 0.0, "climate": 0.0})
            ml_meta = scored.get("ml_engine_metadata") or {}
            ranked.append(
                AnalogResult(
                    site_id=cand["site_id"],
                    name=cand["site_name"],
                    country="Test",
                    coordinates=Coordinates(lat=0.0, lng=0.0),
                    similarity_score=scored["similarity_score"],
                    breakdown=SimilarityBreakdown(**scored["breakdown"]),
                    metadata=AnalogMetadata(accessibility_rating="Good"),
                    ml_engine_metadata=ml_meta,
                )
            )

        ranked.sort(key=lambda item: (-item.similarity_score, item.site_id))
        assert [r.site_id for r in ranked] == ["site-a", "site-m", "site-z"]

"""Tests for the preprocessing pipeline."""
from __future__ import annotations

import math
import pytest

from ml_engine.models.schemas import DataQuality
from ml_engine.preprocessing.feature_validation import (
    validate_target_features,
    validate_candidate_features,
    _is_finite_number,
)
from ml_engine.preprocessing.normalization import (
    normalize_elevation,
    normalize_slope,
    normalize_temperature,
    normalize_to_unit_range,
)
from ml_engine.preprocessing.missing_values import (
    check_missing_features,
    imputation_not_supported,
    summarize_data_quality,
)


# ===================================================================
# Synthetic fixtures — clearly labelled, for software testing only.
# ===================================================================

VALID_TARGET_RAW: dict = {
    "planet": "moon",
    "site_id": "test-target-01",
    "site_name": "Test Crater (SYNTHETIC)",
    "lat": -89.9,
    "lng": 0.0,
    "avg_slope_deg": 12.5,
    "elevation_m": -4000.0,
    "regolith_composition": {"basalt_pct": 35, "silica_pct": 28},
    "primary_rock": "basalt",
    "temp_range_c": [-80, 20],
    "data_source": "synthetic_test",
}

VALID_CANDIDATE_RAW: dict = {
    "site_id": "test-cand-01",
    "site_name": "Test Tile A (SYNTHETIC)",
    "country": "DEMO",
    "lat": -23.5,
    "lng": -68.2,
    "elevation_m": 2300.0,
    "slope_deg": 11.0,
    "ndvi": 0.12,
    "spectral_signature": {"mean_ndvi": 0.12, "min_ndvi": 0.05},
    "primary_rock": "basalt",
    "temp_min_c": -15.0,
    "temp_max_c": 35.0,
    "accessibility_score": 68.0,
    "is_subterranean": False,
    "data_source": "synthetic_test",
}


# ===================================================================
# Feature validation
# ===================================================================

class TestIsFiniteNumber:
    def test_int(self):
        assert _is_finite_number(42) is True

    def test_float(self):
        assert _is_finite_number(3.14) is True

    def test_none(self):
        assert _is_finite_number(None) is False

    def test_bool(self):
        assert _is_finite_number(True) is False

    def test_nan(self):
        assert _is_finite_number(float("nan")) is False

    def test_inf(self):
        assert _is_finite_number(float("inf")) is False

    def test_string(self):
        assert _is_finite_number("42") is False


class TestValidateTargetFeatures:
    def test_valid_target(self):
        target, reports = validate_target_features(VALID_TARGET_RAW)
        assert target.planet.value == "moon"
        assert target.site_id == "test-target-01"
        assert target.elevation_m == -4000.0
        assert target.avg_slope_deg == 12.5
        assert target.temp_range_c == (-80.0, 20.0)
        assert target.primary_rock == "basalt"

    def test_missing_planet_raises(self):
        with pytest.raises(ValueError, match="planet"):
            validate_target_features({"site_id": "x", "site_name": "X"})

    def test_invalid_planet_raises(self):
        with pytest.raises(ValueError, match="planet"):
            validate_target_features({
                "planet": "venus", "site_id": "x", "site_name": "X",
            })

    def test_missing_site_id_raises(self):
        with pytest.raises(ValueError, match="site_id"):
            validate_target_features({"planet": "moon", "site_name": "X"})

    def test_missing_elevation_reported(self):
        raw = {**VALID_TARGET_RAW, "elevation_m": None}
        target, reports = validate_target_features(raw)
        assert target.elevation_m is None
        elev_report = [r for r in reports if r.feature_name == "elevation_m"]
        assert elev_report[0].quality == DataQuality.MISSING

    def test_invalid_slope_reported(self):
        raw = {**VALID_TARGET_RAW, "avg_slope_deg": "not_a_number"}
        target, reports = validate_target_features(raw)
        assert target.avg_slope_deg is None
        slope_report = [r for r in reports if r.feature_name == "avg_slope_deg"]
        assert slope_report[0].quality == DataQuality.INVALID

    def test_out_of_range_slope(self):
        raw = {**VALID_TARGET_RAW, "avg_slope_deg": 95.0}
        target, reports = validate_target_features(raw)
        slope_r = [r for r in reports if r.feature_name == "avg_slope_deg"]
        assert slope_r[0].quality == DataQuality.OUT_OF_RANGE

    def test_temp_range_swapped(self):
        raw = {**VALID_TARGET_RAW, "temp_range_c": [20, -80]}
        target, _ = validate_target_features(raw)
        assert target.temp_range_c == (-80.0, 20.0)

    def test_temp_range_invalid_format(self):
        raw = {**VALID_TARGET_RAW, "temp_range_c": "cold"}
        target, reports = validate_target_features(raw)
        assert target.temp_range_c is None
        t_rep = [r for r in reports if r.feature_name == "temp_range_c"]
        assert t_rep[0].quality == DataQuality.INVALID

    def test_mars_target(self):
        raw = {**VALID_TARGET_RAW, "planet": "mars", "site_id": "jezero-01"}
        target, _ = validate_target_features(raw)
        assert target.planet.value == "mars"


class TestValidateCandidateFeatures:
    def test_valid_candidate(self):
        cand, reports = validate_candidate_features(VALID_CANDIDATE_RAW)
        assert cand.site_id == "test-cand-01"
        assert cand.elevation_m == 2300.0
        assert cand.slope_deg == 11.0
        assert cand.ndvi == 0.12
        assert cand.temp_min_c == -15.0
        assert cand.temp_max_c == 35.0

    def test_missing_site_id_raises(self):
        with pytest.raises(ValueError, match="site_id"):
            validate_candidate_features({"site_name": "X"})

    def test_missing_features_reported(self):
        raw = {"site_id": "x", "site_name": "X"}
        cand, reports = validate_candidate_features(raw)
        missing = [r for r in reports if r.quality == DataQuality.MISSING]
        assert len(missing) > 0

    def test_swapped_temps(self):
        raw = {**VALID_CANDIDATE_RAW, "temp_min_c": 35.0, "temp_max_c": -15.0}
        cand, _ = validate_candidate_features(raw)
        assert cand.temp_min_c == -15.0
        assert cand.temp_max_c == 35.0

    def test_nan_elevation(self):
        raw = {**VALID_CANDIDATE_RAW, "elevation_m": float("nan")}
        cand, reports = validate_candidate_features(raw)
        assert cand.elevation_m is None
        elev = [r for r in reports if r.feature_name == "elevation_m"]
        assert elev[0].quality == DataQuality.INVALID


# ===================================================================
# Normalization
# ===================================================================

class TestNormalization:
    def test_elevation_mid(self):
        result = normalize_elevation(0.0)
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_elevation_min(self):
        assert normalize_elevation(-12_000.0) == 0.0

    def test_elevation_max(self):
        assert normalize_elevation(30_000.0) == 1.0

    def test_elevation_none(self):
        assert normalize_elevation(None) is None

    def test_elevation_nan(self):
        assert normalize_elevation(float("nan")) is None

    def test_slope_zero(self):
        assert normalize_slope(0.0) == 0.0

    def test_slope_max(self):
        assert normalize_slope(90.0) == 1.0

    def test_slope_none(self):
        assert normalize_slope(None) is None

    def test_temperature(self):
        result = normalize_temperature(0.0)
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_unit_range_ndvi(self):
        result = normalize_to_unit_range(0.5, min_bound=-1.0, max_bound=1.0)
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_unit_range_accessibility(self):
        result = normalize_to_unit_range(50.0, min_bound=0.0, max_bound=100.0)
        assert result == pytest.approx(0.5)


# ===================================================================
# Missing values
# ===================================================================

class TestMissingValues:
    def test_check_missing(self):
        from ml_engine.models.schemas import FeatureReport
        reports = [
            FeatureReport(feature_name="a", quality=DataQuality.VALID),
            FeatureReport(feature_name="b", quality=DataQuality.MISSING),
        ]
        issues = check_missing_features(reports, ["a", "b", "c"])
        assert "a" not in issues
        assert issues["b"] == DataQuality.MISSING
        assert issues["c"] == DataQuality.MISSING

    def test_imputation_warning(self):
        msg = imputation_not_supported("elevation_m")
        assert "elevation_m" in msg
        assert "impute" in msg.lower() or "imput" in msg.lower()

    def test_summarize(self):
        from ml_engine.models.schemas import FeatureReport
        reports = [
            FeatureReport(feature_name="a", quality=DataQuality.VALID),
            FeatureReport(feature_name="b", quality=DataQuality.MISSING),
            FeatureReport(feature_name="c", quality=DataQuality.INVALID),
        ]
        s = summarize_data_quality(reports)
        assert "a" in s["valid"]
        assert "b" in s["missing"]
        assert "c" in s["invalid"]


# ===================================================================
# Planet-aware elevation and temperature normalization tests
# ===================================================================

class TestPlanetAwareElevationNormalization:
    def test_earth_default_bounds(self):
        # Earth bounds: [-12,000m, 30,000m], span = 42,000m
        assert normalize_elevation(0.0) == pytest.approx(12000.0 / 42000.0, abs=1e-5)
        assert normalize_elevation(-12_000.0) == 0.0
        assert normalize_elevation(30_000.0) == 1.0

    def test_earth_explicit_planet(self):
        from ml_engine.models.schemas import Planet
        assert normalize_elevation(0.0, planet=Planet.EARTH) == normalize_elevation(0.0, planet="earth")
        assert normalize_elevation(-12_000.0, planet="earth") == 0.0

    def test_moon_elevation_bounds(self):
        # Moon LOLA bounds: [-12,000m, 15,000m], span = 27,000m
        from ml_engine.models.schemas import Planet
        # Datum zero (1,737.4 km sphere)
        assert normalize_elevation(0.0, planet=Planet.MOON) == pytest.approx(12000.0 / 27000.0, abs=1e-5)
        assert normalize_elevation(-12_000.0, planet="moon") == 0.0
        assert normalize_elevation(15_000.0, planet="moon") == 1.0
        # Deepest lunar crater basin floor (Antoniadi in SPA basin ~ -9,150m)
        norm_spa = normalize_elevation(-9_150.0, planet="moon")
        assert norm_spa is not None
        assert 0.0 < norm_spa < 0.20  # ~0.1055, NOT clipped to 0
        # Highest lunar mountain summit (Engel'gardt rim peak ~ +10,786m)
        norm_peak = normalize_elevation(10_786.0, planet="moon")
        assert norm_peak is not None
        assert 0.80 < norm_peak < 1.0  # ~0.8439, NOT clipped to 1

    def test_mars_elevation_bounds(self):
        # Mars MOLA bounds: [-10,000m, 25,000m], span = 35,000m
        from ml_engine.models.schemas import Planet
        # MOLA aeroid zero
        assert normalize_elevation(0.0, planet=Planet.MARS) == pytest.approx(10000.0 / 35000.0, abs=1e-5)
        assert normalize_elevation(-10_000.0, planet="mars") == 0.0
        assert normalize_elevation(25_000.0, planet="mars") == 1.0
        # Deepest Martian basin (Hellas Planitia floor ~ -8,200m)
        norm_hellas = normalize_elevation(-8_200.0, planet="mars")
        assert norm_hellas is not None
        assert 0.0 < norm_hellas < 0.10  # ~0.0514, NOT clipped
        # Highest volcanic caldera peak (Olympus Mons ~ +21,229m)
        norm_olympus = normalize_elevation(21_229.0, planet="mars")
        assert norm_olympus is not None
        assert 0.85 < norm_olympus < 0.95  # ~0.8923, NOT clipped

    def test_elevation_clipping_behavior(self):
        # Moon with extreme unphysical value outside envelope
        clipped = normalize_elevation(20_000.0, planet="moon", clip=True)
        unclipped = normalize_elevation(20_000.0, planet="moon", clip=False)
        assert clipped == 1.0
        assert unclipped is not None and unclipped > 1.0  # (20000 - (-12000)) / 27000 = 1.185

    def test_elevation_backward_compat_positional(self):
        # Legacy positional min_bound, max_bound: normalize_elevation(500.0, 0.0, 1000.0)
        assert normalize_elevation(500.0, 0.0, 1000.0) == 0.5

    def test_elevation_unsupported_planet_raises(self):
        with pytest.raises(ValueError, match="Unsupported planet"):
            normalize_elevation(100.0, planet="jupiter")

    def test_elevation_invalid_inputs(self):
        assert normalize_elevation(None, planet="moon") is None
        assert normalize_elevation(float("nan"), planet="mars") is None
        assert normalize_elevation(100.0, min_bound=500.0, max_bound=100.0) is None  # inverted


class TestPlanetAwareTemperatureNormalization:
    def test_earth_default_bounds(self):
        # Earth bounds: [-100 deg C, 70 deg C], span = 170 deg C
        assert normalize_temperature(-100.0) == 0.0
        assert normalize_temperature(70.0) == 1.0
        assert normalize_temperature(0.0) == pytest.approx(100.0 / 170.0, abs=1e-5)

    def test_moon_temperature_bounds(self):
        # Moon thermal vacuum bounds: [-250 deg C, 150 deg C], span = 400 deg C
        from ml_engine.models.schemas import Planet
        assert normalize_temperature(-250.0, planet=Planet.MOON) == 0.0
        assert normalize_temperature(150.0, planet="moon") == 1.0
        assert normalize_temperature(0.0, planet="moon") == pytest.approx(250.0 / 400.0, abs=1e-5)
        # Cryogenic permanently shadowed cold trap (e.g. Shackleton floor ~ -240 deg C)
        norm_psr = normalize_temperature(-240.0, planet="moon")
        assert norm_psr is not None
        assert 0.0 < norm_psr < 0.05  # ~0.025, NOT clipped to 0!
        # Equatorial solar noon surface (+120 deg C)
        norm_noon = normalize_temperature(120.0, planet="moon")
        assert norm_noon is not None
        assert 0.90 < norm_noon < 0.95  # ~0.925, NOT clipped to 1!

    def test_mars_temperature_bounds(self):
        # Mars bounds: [-150 deg C, 40 deg C], span = 190 deg C
        from ml_engine.models.schemas import Planet
        assert normalize_temperature(-150.0, planet=Planet.MARS) == 0.0
        assert normalize_temperature(40.0, planet="mars") == 1.0
        assert normalize_temperature(0.0, planet="mars") == pytest.approx(150.0 / 190.0, abs=1e-5)
        # Polar night CO2 frost freezing (~ -130 deg C)
        norm_polar = normalize_temperature(-130.0, planet="mars")
        assert norm_polar is not None
        assert 0.05 < norm_polar < 0.15  # ~0.1053, NOT clipped to 0!
        # Summer afternoon in Jezero Crater (~ +10 deg C)
        norm_jezero = normalize_temperature(10.0, planet="mars")
        assert norm_jezero is not None
        assert 0.80 < norm_jezero < 0.90  # ~0.8421

    def test_temperature_range_normalization(self):
        from ml_engine.preprocessing.normalization import normalize_temperature_range
        # Moon Shackleton range [-240 deg C, -180 deg C]
        res_moon = normalize_temperature_range([-240.0, -180.0], planet="moon")
        assert res_moon is not None
        lo, hi = res_moon
        assert 0.0 < lo < 0.05
        assert 0.15 < hi < 0.20
        # Swapped order handling [hi, lo]
        res_swapped = normalize_temperature_range([-180.0, -240.0], planet="moon")
        assert res_swapped == res_moon
        # None / invalid
        assert normalize_temperature_range(None) is None
        assert normalize_temperature_range([10.0]) is None

    def test_temperature_clipping_behavior(self):
        # Mars with -180 deg C (below Mars envelope)
        clipped = normalize_temperature(-180.0, planet="mars", clip=True)
        unclipped = normalize_temperature(-180.0, planet="mars", clip=False)
        assert clipped == 0.0
        assert unclipped is not None and unclipped < 0.0  # -30/190 = -0.1578

    def test_temperature_backward_compat_positional(self):
        assert normalize_temperature(10.0, 0.0, 20.0) == 0.5

    def test_temperature_unsupported_planet_raises(self):
        with pytest.raises(ValueError, match="Unsupported planet"):
            normalize_temperature(0.0, planet="venus")


class TestValidationNormalizationConsistency:
    def test_target_feature_reports_contain_normalized_values(self):
        from ml_engine.preprocessing.feature_validation import validate_target_features
        raw = {
            "planet": "moon",
            "site_id": "test-norm-t",
            "site_name": "Test Norm Target",
            "elevation_m": -4000.0,
            "avg_slope_deg": 15.0,
            "temp_range_c": [-100.0, 20.0],
        }
        target, reports = validate_target_features(raw)
        elev_report = next(r for r in reports if r.feature_name == "elevation_m")
        assert elev_report.quality == DataQuality.VALID
        assert elev_report.raw_value == -4000.0
        # Moon elevation [-12000, 15000]: (-4000 - (-12000)) / 27000 = 8000/27000 ~= 0.296296
        assert elev_report.normalized_value == pytest.approx(8000.0 / 27000.0, abs=1e-5)

        temp_report = next(r for r in reports if r.feature_name == "temp_range_c")
        assert temp_report.quality == DataQuality.VALID
        # Midpoint of [-100, 20] is -40 deg C. Moon temp [-250, 150]: (-40 - (-250)) / 400 = 210/400 = 0.525
        assert temp_report.normalized_value == pytest.approx(210.0 / 400.0, abs=1e-5)

    def test_candidate_feature_reports_contain_normalized_values(self):
        from ml_engine.preprocessing.feature_validation import validate_candidate_features
        raw = {
            "site_id": "test-norm-c",
            "site_name": "Test Norm Candidate",
            "elevation_m": 2300.0,
            "slope_deg": 11.0,
            "temp_min_c": -15.0,
            "temp_max_c": 35.0,
        }
        cand, reports = validate_candidate_features(raw)
        elev_report = next(r for r in reports if r.feature_name == "elevation_m")
        assert elev_report.quality == DataQuality.VALID
        assert elev_report.raw_value == 2300.0
        # Earth elevation [-12000, 30000]: (2300 - (-12000)) / 42000 = 14300/42000 ~= 0.340476
        assert elev_report.normalized_value == pytest.approx(14300.0 / 42000.0, abs=1e-5)

        tmin_report = next(r for r in reports if r.feature_name == "temp_min_c")
        # Earth temp [-100, 70]: (-15 - (-100)) / 170 = 85/170 = 0.5
        assert tmin_report.normalized_value == pytest.approx(0.5, abs=1e-5)

    def test_out_of_range_has_none_normalized_value(self):
        from ml_engine.preprocessing.feature_validation import validate_target_features
        raw = {
            "planet": "moon",
            "site_id": "test-oor",
            "site_name": "Test OOR",
            "elevation_m": 50000.0,  # Far above lunar peak
        }
        target, reports = validate_target_features(raw)
        elev_report = next(r for r in reports if r.feature_name == "elevation_m")
        assert elev_report.quality == DataQuality.OUT_OF_RANGE
        assert elev_report.normalized_value is None
        assert target.elevation_m is None

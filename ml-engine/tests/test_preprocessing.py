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

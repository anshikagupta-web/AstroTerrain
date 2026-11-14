"""Tests for the backend integration adapter."""
from __future__ import annotations

import pytest

from ml_engine.adapter import score_analog


# ===================================================================
# Synthetic fixtures — matches the backend's dict format.
# ===================================================================

SYNTHETIC_TARGET = {
    "planet": "moon",
    "site_id": "test-crater",
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

SYNTHETIC_ANALOG = {
    "site_id": "test-tile-a",
    "site_name": "Test Tile A (SYNTHETIC)",
    "country": "DEMO",
    "lat": -23.5,
    "lng": -68.2,
    "elevation_m": 2300.0,
    "slope_deg": 11.0,
    "ndvi": 0.12,
    "spectral_signature": {"mean_ndvi": 0.12},
    "primary_rock": "basalt",
    "temp_min_c": -15.0,
    "temp_max_c": 35.0,
    "accessibility_score": 68.0,
    "is_subterranean": False,
    "data_source": "synthetic_test",
}

DEFAULT_WEIGHTS = {"topography": 0.4, "geochemistry": 0.35, "climate": 0.25}


class TestAdapterContract:
    """Verify the adapter returns the backend's expected structure."""

    def test_has_similarity_score(self):
        result = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert "similarity_score" in result
        assert isinstance(result["similarity_score"], float)

    def test_score_between_0_and_100(self):
        result = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert 0 <= result["similarity_score"] <= 100

    def test_has_breakdown(self):
        result = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert "breakdown" in result
        bd = result["breakdown"]
        assert "topography_match" in bd
        assert "geochemistry_match" in bd
        assert "climate_match" in bd

    def test_breakdown_values_are_floats(self):
        result = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        bd = result["breakdown"]
        for key in ("topography_match", "geochemistry_match", "climate_match"):
            assert isinstance(bd[key], float)
            assert 0 <= bd[key] <= 100

    def test_has_metadata(self):
        result = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert "ml_engine_metadata" in result
        meta = result["ml_engine_metadata"]
        assert "is_complete" in meta
        assert "dimensions_computed" in meta
        assert "warnings" in meta
        assert "explanation" in meta


class TestAdapterWeights:
    def test_zero_weights_raises(self):
        with pytest.raises(ValueError, match="weight"):
            score_analog(
                SYNTHETIC_TARGET, SYNTHETIC_ANALOG,
                {"topography": 0, "geochemistry": 0, "climate": 0},
            )

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError):
            score_analog(
                SYNTHETIC_TARGET, SYNTHETIC_ANALOG,
                {"topography": -1, "geochemistry": 0.5, "climate": 0.5},
            )

    def test_single_weight(self):
        result = score_analog(
            SYNTHETIC_TARGET, SYNTHETIC_ANALOG,
            {"topography": 1.0, "geochemistry": 0, "climate": 0},
        )
        assert 0 <= result["similarity_score"] <= 100


class TestAdapterMissingData:
    def test_missing_target_features(self):
        target = {
            "planet": "moon",
            "site_id": "empty-target",
            "site_name": "Empty Target (SYNTHETIC)",
        }
        result = score_analog(target, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert "similarity_score" in result
        assert isinstance(result["similarity_score"], float)
        # Should have warnings about missing data
        meta = result["ml_engine_metadata"]
        assert len(meta["warnings"]) > 0

    def test_missing_candidate_features(self):
        analog = {
            "site_id": "empty-cand",
            "site_name": "Empty Candidate (SYNTHETIC)",
        }
        result = score_analog(SYNTHETIC_TARGET, analog, DEFAULT_WEIGHTS)
        assert "similarity_score" in result

    def test_no_computable_dimensions_returns_zero_and_insufficient_data(self):
        target = {
            "planet": "moon",
            "site_id": "empty-target",
            "site_name": "Empty Target (SYNTHETIC)",
        }
        analog = {
            "site_id": "empty-cand",
            "site_name": "Empty Candidate (SYNTHETIC)",
        }
        result = score_analog(target, analog, DEFAULT_WEIGHTS)
        assert result["similarity_score"] == 0.0
        assert result["breakdown"]["topography_match"] == 0.0
        assert result["breakdown"]["geochemistry_match"] == 0.0
        assert result["breakdown"]["climate_match"] == 0.0
        assert result["ml_engine_metadata"]["insufficient_data"] is True

    def test_mars_target(self):
        mars_target = {**SYNTHETIC_TARGET, "planet": "mars", "site_id": "mars-t"}
        result = score_analog(mars_target, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert 0 <= result["similarity_score"] <= 100


class TestAdapterRepeatability:
    def test_same_inputs_same_outputs(self):
        r1 = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        r2 = score_analog(SYNTHETIC_TARGET, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)
        assert r1["similarity_score"] == r2["similarity_score"]
        assert r1["breakdown"] == r2["breakdown"]


class TestAdapterInvalidInputs:
    def test_invalid_planet_raises(self):
        target = {**SYNTHETIC_TARGET, "planet": "venus"}
        with pytest.raises(ValueError, match="planet"):
            score_analog(target, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)

    def test_missing_site_id_raises(self):
        target = {"planet": "moon", "site_name": "X"}
        with pytest.raises(ValueError, match="site_id"):
            score_analog(target, SYNTHETIC_ANALOG, DEFAULT_WEIGHTS)

    def test_inf_weight_raises(self):
        with pytest.raises(ValueError):
            score_analog(
                SYNTHETIC_TARGET, SYNTHETIC_ANALOG,
                {"topography": float("inf"), "geochemistry": 0, "climate": 0},
            )

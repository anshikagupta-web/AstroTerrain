"""Tests for the similarity comparison engines."""
from __future__ import annotations

import math
import pytest

from ml_engine.models.schemas import (
    ComparisonWeights,
    DimensionStatus,
    EarthCandidate,
    PlanetaryTarget,
    Planet,
)
from ml_engine.comparison.topography import compare_topography, _gaussian_similarity
from ml_engine.comparison.geochemistry import compare_geochemistry, _is_ndvi_data
from ml_engine.comparison.climate import compare_climate, _interval_similarity
from ml_engine.comparison.similarity import calculate_weighted_similarity


# ===================================================================
# Synthetic fixtures — CLEARLY LABELLED, for software testing only.
# ===================================================================

def _make_target(**overrides) -> PlanetaryTarget:
    defaults = dict(
        planet=Planet.MOON,
        site_id="syn-target",
        site_name="Synthetic Target",
        elevation_m=-4000.0,
        avg_slope_deg=12.5,
        regolith_composition={"basalt_pct": 35, "silica_pct": 28},
        primary_rock="basalt",
        temp_range_c=(-80.0, 20.0),
        data_source="synthetic_test",
    )
    defaults.update(overrides)
    return PlanetaryTarget(**defaults)


def _make_candidate(**overrides) -> EarthCandidate:
    defaults = dict(
        site_id="syn-cand",
        site_name="Synthetic Candidate",
        elevation_m=2300.0,
        slope_deg=11.0,
        ndvi=0.12,
        spectral_signature={"mean_ndvi": 0.12},
        primary_rock="basalt",
        temp_min_c=-15.0,
        temp_max_c=35.0,
        data_source="synthetic_test",
    )
    defaults.update(overrides)
    return EarthCandidate(**defaults)


# ===================================================================
# Topography
# ===================================================================

class TestGaussianSimilarity:
    def test_identical(self):
        assert _gaussian_similarity(100, 100, 10) == 100.0

    def test_at_sigma(self):
        result = _gaussian_similarity(0, 10, 10)
        assert pytest.approx(result, abs=0.1) == 60.65

    def test_large_diff(self):
        result = _gaussian_similarity(0, 100, 10)
        assert result < 1.0

    def test_zero_sigma(self):
        assert _gaussian_similarity(5, 5, 0) == 100.0
        assert _gaussian_similarity(5, 6, 0) == 0.0


class TestTopography:
    def test_exact_match(self):
        t = _make_target(elevation_m=1000, avg_slope_deg=10)
        c = _make_candidate(elevation_m=1000, slope_deg=10)
        result = compare_topography(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert result.score == 100.0

    def test_moderate_difference(self):
        t = _make_target(elevation_m=1000, avg_slope_deg=10)
        c = _make_candidate(elevation_m=3000, slope_deg=15)
        result = compare_topography(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert 0 < result.score < 100

    def test_missing_target_elevation(self):
        t = _make_target(elevation_m=None)
        c = _make_candidate()
        result = compare_topography(t, c)
        # Slope is still available
        assert result.status == DimensionStatus.COMPUTED
        assert "elevation_m" in result.features_missing

    def test_all_missing(self):
        t = _make_target(elevation_m=None, avg_slope_deg=None)
        c = _make_candidate(elevation_m=None, slope_deg=None)
        result = compare_topography(t, c)
        assert result.status == DimensionStatus.UNAVAILABLE
        assert result.score is None

    def test_score_range(self):
        t = _make_target()
        c = _make_candidate()
        result = compare_topography(t, c)
        if result.score is not None:
            assert 0 <= result.score <= 100


# ===================================================================
# Geochemistry
# ===================================================================

class TestNdviDetection:
    def test_ndvi_only(self):
        assert _is_ndvi_data({"mean_ndvi": 0.5, "valid_pixels": 100}) is True

    def test_mineral_data(self):
        assert _is_ndvi_data({"basalt_pct": 35, "silica_pct": 28}) is False

    def test_empty(self):
        assert _is_ndvi_data({}) is True


class TestGeochemistry:
    def test_ndvi_spectral_is_unavailable(self):
        """NDVI data must NOT be used for geochemistry comparison."""
        t = _make_target()
        c = _make_candidate(
            spectral_signature={"mean_ndvi": 0.5, "valid_pixels": 100},
        )
        result = compare_geochemistry(t, c)
        # With NDVI only and matching rock type, we get rock-type only
        assert result.status == DimensionStatus.COMPUTED
        # But a warning about NDVI must be present
        ndvi_warnings = [
            w for w in result.warnings if "NDVI" in w or "ndvi" in w.lower()
        ]
        assert len(ndvi_warnings) > 0

    def test_mineral_composition_match(self):
        t = _make_target(
            regolith_composition={"basalt_pct": 40, "silica_pct": 25},
        )
        c = _make_candidate(
            spectral_signature={"basalt_pct": 40, "silica_pct": 25},
        )
        result = compare_geochemistry(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert result.score is not None
        assert result.score > 80  # Identical vectors -> high cosine sim

    def test_mineral_orthogonal_cosine_mapping_zero(self):
        """Orthogonal non-negative mineral vectors must map directly to 0.0, not 50.0."""
        from ml_engine.comparison.geochemistry import _cosine_similarity
        vec_a = {"olivine": 100.0}
        vec_b = {"quartz": 100.0}
        cos_score = _cosine_similarity(vec_a, vec_b)
        assert cos_score == 0.0

    def test_rock_type_exact_match(self):
        t = _make_target(regolith_composition={}, primary_rock="basalt")
        c = _make_candidate(spectral_signature={}, primary_rock="basalt")
        result = compare_geochemistry(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert result.score == 90.0

    def test_rock_type_family_match(self):
        t = _make_target(regolith_composition={}, primary_rock="basalt")
        c = _make_candidate(
            spectral_signature={}, primary_rock="basaltic sediment",
        )
        result = compare_geochemistry(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert result.score == 60.0

    def test_rock_type_no_match(self):
        t = _make_target(regolith_composition={}, primary_rock="basalt")
        c = _make_candidate(spectral_signature={}, primary_rock="granite")
        result = compare_geochemistry(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert result.score == 20.0

    def test_no_data_at_all(self):
        t = _make_target(
            regolith_composition={}, primary_rock=None,
        )
        c = _make_candidate(
            spectral_signature={}, primary_rock=None,
        )
        result = compare_geochemistry(t, c)
        assert result.status == DimensionStatus.UNAVAILABLE
        assert result.score is None


# ===================================================================
# Climate
# ===================================================================

class TestIntervalSimilarity:
    def test_identical(self):
        assert _interval_similarity(-10, 20, -10, 20) == 100.0

    def test_no_overlap(self):
        score = _interval_similarity(-10, 0, 10, 20)
        assert score < 35.0  # Capped at ~35 for non-overlapping

    def test_partial_overlap(self):
        score = _interval_similarity(-10, 20, 0, 30)
        assert 0 < score < 100

    def test_point_match(self):
        assert _interval_similarity(5, 5, 5, 5) == 100.0

    def test_point_no_match(self):
        assert _interval_similarity(5, 5, 10, 10) < 35.0


class TestClimate:
    def test_exact_range(self):
        t = _make_target(temp_range_c=(-10.0, 20.0))
        c = _make_candidate(temp_min_c=-10.0, temp_max_c=20.0)
        result = compare_climate(t, c)
        assert result.status == DimensionStatus.COMPUTED
        assert result.score == 100.0

    def test_missing_target_temp(self):
        t = _make_target(temp_range_c=None)
        c = _make_candidate()
        result = compare_climate(t, c)
        assert result.status == DimensionStatus.UNAVAILABLE

    def test_missing_candidate_temp(self):
        t = _make_target()
        c = _make_candidate(temp_min_c=None, temp_max_c=None)
        result = compare_climate(t, c)
        assert result.status == DimensionStatus.UNAVAILABLE


# ===================================================================
# Weighted similarity
# ===================================================================

class TestWeightedSimilarity:
    def test_all_dimensions_computed(self):
        t = _make_target(
            elevation_m=1000, avg_slope_deg=10,
            temp_range_c=(-10.0, 20.0),
            regolith_composition={}, primary_rock="basalt",
        )
        c = _make_candidate(
            elevation_m=1000, slope_deg=10,
            temp_min_c=-10.0, temp_max_c=20.0,
            spectral_signature={}, primary_rock="basalt",
        )
        w = ComparisonWeights(topography=0.4, geochemistry=0.35, climate=0.25)
        result = calculate_weighted_similarity(t, c, w)
        assert result.overall_score is not None
        assert 0 <= result.overall_score <= 100
        assert result.dimensions_computed >= 2  # topo + climate at least

    def test_score_between_0_and_100(self):
        t = _make_target()
        c = _make_candidate()
        w = ComparisonWeights()
        result = calculate_weighted_similarity(t, c, w)
        if result.overall_score is not None:
            assert 0 <= result.overall_score <= 100

    def test_zero_weight_excludes(self):
        t = _make_target()
        c = _make_candidate()
        w = ComparisonWeights(topography=1.0, geochemistry=0.0, climate=0.0)
        result = calculate_weighted_similarity(t, c, w)
        if result.overall_score is not None:
            # Only topography should matter
            topo_dim = [
                d for d in result.dimensions if d.dimension == "topography"
            ]
            if topo_dim and topo_dim[0].score is not None:
                assert result.overall_score == pytest.approx(
                    topo_dim[0].score, abs=0.1,
                )

    def test_missing_dimension_renormalises(self):
        t = _make_target(temp_range_c=None)
        c = _make_candidate()
        w = ComparisonWeights(topography=0.4, geochemistry=0.35, climate=0.25)
        result = calculate_weighted_similarity(t, c, w)
        # Climate unavailable — weights renormalised
        climate_dim = [
            d for d in result.dimensions if d.dimension == "climate"
        ]
        assert climate_dim[0].weight_effective == 0.0
        assert result.is_complete is False
        # Warnings should mention incomplete comparison
        assert any("incomplete" in w.lower() or "unavailable" in w.lower()
                    for w in result.warnings)

    def test_no_dimensions_returns_none(self):
        t = _make_target(
            elevation_m=None, avg_slope_deg=None,
            temp_range_c=None, regolith_composition={}, primary_rock=None,
        )
        c = _make_candidate(
            elevation_m=None, slope_deg=None,
            temp_min_c=None, temp_max_c=None,
            spectral_signature={}, primary_rock=None,
        )
        w = ComparisonWeights()
        result = calculate_weighted_similarity(t, c, w)
        assert result.overall_score is None
        assert result.is_complete is False

    def test_repeatability(self):
        t = _make_target()
        c = _make_candidate()
        w = ComparisonWeights()
        r1 = calculate_weighted_similarity(t, c, w)
        r2 = calculate_weighted_similarity(t, c, w)
        assert r1.overall_score == r2.overall_score

    def test_moon_target(self):
        t = _make_target(planet=Planet.MOON)
        c = _make_candidate()
        w = ComparisonWeights()
        result = calculate_weighted_similarity(t, c, w)
        assert result.target_site_id == t.site_id

    def test_mars_target(self):
        t = _make_target(planet=Planet.MARS, site_id="jezero-test")
        c = _make_candidate()
        w = ComparisonWeights()
        result = calculate_weighted_similarity(t, c, w)
        assert result.target_site_id == "jezero-test"

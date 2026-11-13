"""Tests for the explainability module."""
from __future__ import annotations

from ml_engine.models.schemas import (
    ComparisonWeights,
    DimensionResult,
    DimensionStatus,
    EarthCandidate,
    Planet,
    PlanetaryTarget,
    SimilarityResult,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity
from ml_engine.explainability.explanations import generate_explanation


def _make_target(**kw) -> PlanetaryTarget:
    defaults = dict(
        planet=Planet.MOON, site_id="syn-t", site_name="Syn Target",
        elevation_m=-4000.0, avg_slope_deg=12.5,
        primary_rock="basalt", temp_range_c=(-80.0, 20.0),
        data_source="synthetic_test",
    )
    defaults.update(kw)
    return PlanetaryTarget(**defaults)


def _make_candidate(**kw) -> EarthCandidate:
    defaults = dict(
        site_id="syn-c", site_name="Syn Candidate",
        elevation_m=2300.0, slope_deg=11.0,
        primary_rock="basalt", temp_min_c=-15.0, temp_max_c=35.0,
        data_source="synthetic_test",
    )
    defaults.update(kw)
    return EarthCandidate(**defaults)


class TestExplanation:
    def test_has_summary(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert expl.overall_summary
        assert isinstance(expl.overall_summary, str)

    def test_has_dimension_explanations(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert len(expl.dimension_explanations) > 0

    def test_unavailable_dimension_noted(self):
        t = _make_target(temp_range_c=None)
        c = _make_candidate(temp_min_c=None)
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert len(expl.unavailable_dimensions) > 0

    def test_strong_match_categorised(self):
        t = _make_target(elevation_m=1000, avg_slope_deg=10)
        c = _make_candidate(elevation_m=1000, slope_deg=10)
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        # Topography should be a strong match
        assert any("topography" in s.lower() for s in expl.strong_matches)

    def test_weak_match_categorised(self):
        t = _make_target(elevation_m=1000, avg_slope_deg=10)
        c = _make_candidate(elevation_m=20000, slope_deg=80)
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert any("topography" in w.lower() for w in expl.weak_matches)

    def test_effective_weights_populated(self):
        t = _make_target()
        c = _make_candidate()
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert len(expl.effective_weights) > 0

    def test_no_dimensions_explanation(self):
        t = _make_target(
            elevation_m=None, avg_slope_deg=None,
            temp_range_c=None, regolith_composition={}, primary_rock=None,
        )
        c = _make_candidate(
            elevation_m=None, slope_deg=None,
            temp_min_c=None, temp_max_c=None,
            spectral_signature={}, primary_rock=None,
        )
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert expl.overall_score is None
        assert "could not be determined" in expl.overall_summary

    def test_data_quality_warnings_propagated(self):
        t = _make_target()
        c = _make_candidate(
            spectral_signature={"mean_ndvi": 0.5},
        )
        result = calculate_weighted_similarity(t, c, ComparisonWeights())
        expl = generate_explanation(result)
        assert len(expl.data_quality_warnings) > 0

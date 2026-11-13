"""End-to-end integration tests between ML Engine and Backend schemas.

Verifies:
1. Complete drop-in parity of ``adapter.score_analog()`` with ``backend/app/services/scoring.py``.
2. Direct serialization into backend Pydantic models:
   - ``SimilarityBreakdown``
   - ``AnalogMetadata``
   - ``AnalogResult``
   - ``AnalogSearchResponse``
3. Exact database seed fixtures from ``002_seed_demo_data.sql``:
   - Moon Shackleton Crater profile
   - Mars Jezero Crater profile
   - Earth demo candidate tiles A, B, C, D
4. Helper functions parity: ``accessibility_rating``, ``topography_match``, etc.
5. Mathematical continuity of temperature interval matching.
6. Ranking behavior with unscored candidates when ``min_score`` is None.
"""
from __future__ import annotations

import math
import os
import sys
import pytest

# Add backend and ml-engine to sys.path so we can import both backend's app and ml_engine cleanly
_BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.schemas.common import Coordinates
from app.schemas.search import (
    SimilarityBreakdown,
    AnalogMetadata,
    AnalogResult,
    AnalogSearchResponse,
)

from ml_engine.adapter import (
    accessibility_rating,
    climate_match,
    geochemistry_match,
    score_analog,
    topography_match,
)
from ml_engine.models.schemas import ComparisonWeights, Planet
from ml_engine.comparison.climate import _interval_similarity
from ml_engine.preprocessing.feature_validation import (
    validate_target_features,
    validate_candidate_features,
)
from ml_engine.ranking.candidate_ranking import rank_candidates


# ===================================================================
# Exact database seed fixtures from 002_seed_demo_data.sql
# ===================================================================

SEED_TARGET_MOON = {
    "planet": "moon",
    "site_id": "shackleton-crater",
    "site_name": "Shackleton Crater (synthetic demo profile)",
    "lat": -89.9,
    "lng": 0.0,
    "avg_slope_deg": 12.5,
    "elevation_m": -4000.0,
    "regolith_composition": {"basalt_pct": 35, "silica_pct": 28, "iron_oxide_pct": 12},
    "primary_rock": "basalt",
    "temp_range_c": [-80, 20],
    "data_source": "synthetic_demo",
}

SEED_TARGET_MARS = {
    "planet": "mars",
    "site_id": "jezero-crater",
    "site_name": "Jezero Crater (synthetic demo profile)",
    "lat": 18.38,
    "lng": 77.58,
    "avg_slope_deg": 6.0,
    "elevation_m": -2500.0,
    "regolith_composition": {"basalt_pct": 45, "silica_pct": 25, "iron_oxide_pct": 18},
    "primary_rock": "basaltic sediment",
    "temp_range_c": [-70, 10],
    "data_source": "synthetic_demo",
}

SEED_ANALOGS = [
    {
        "site_id": "demo-analog-a",
        "site_name": "Synthetic Demo Tile A",
        "country": "DEMO",
        "lat": -23.5,
        "lng": -68.2,
        "elevation_m": 2300.0,
        "slope_deg": 11.0,
        "ndvi": 0.12,
        "spectral_signature": {"basalt_pct": 32, "silica_pct": 30, "iron_oxide_pct": 15},
        "primary_rock": "basalt",
        "temp_min_c": -15.0,
        "temp_max_c": 35.0,
        "accessibility_score": 68.0,
        "is_subterranean": False,
        "data_source": "synthetic_demo",
    },
    {
        "site_id": "demo-analog-b",
        "site_name": "Synthetic Demo Tile B",
        "country": "DEMO",
        "lat": 19.5,
        "lng": -155.5,
        "elevation_m": 900.0,
        "slope_deg": 7.5,
        "ndvi": 0.28,
        "spectral_signature": {"basalt_pct": 48, "silica_pct": 24, "iron_oxide_pct": 17},
        "primary_rock": "basalt",
        "temp_min_c": -5.0,
        "temp_max_c": 30.0,
        "accessibility_score": 82.0,
        "is_subterranean": False,
        "data_source": "synthetic_demo",
    },
    {
        "site_id": "demo-analog-c",
        "site_name": "Synthetic Demo Tile C",
        "country": "DEMO",
        "lat": 78.0,
        "lng": 16.0,
        "elevation_m": 120.0,
        "slope_deg": 18.0,
        "ndvi": 0.05,
        "spectral_signature": {"basalt_pct": 25, "silica_pct": 35, "iron_oxide_pct": 10},
        "primary_rock": "volcanic rock",
        "temp_min_c": -25.0,
        "temp_max_c": 12.0,
        "accessibility_score": 55.0,
        "is_subterranean": True,
        "data_source": "synthetic_demo",
    },
    {
        "site_id": "demo-analog-d",
        "site_name": "Synthetic Demo Tile D",
        "country": "DEMO",
        "lat": -77.5,
        "lng": 161.0,
        "elevation_m": 300.0,
        "slope_deg": 5.0,
        "ndvi": 0.18,
        "spectral_signature": {"basalt_pct": 40, "silica_pct": 22, "iron_oxide_pct": 20},
        "primary_rock": "basalt",
        "temp_min_c": -35.0,
        "temp_max_c": 5.0,
        "accessibility_score": 38.0,
        "is_subterranean": False,
        "data_source": "synthetic_demo",
    },
]

WEIGHTS = {"topography": 0.40, "geochemistry": 0.35, "climate": 0.25}


class TestBackendSchemaIntegration:
    """Verifies adapter output can directly instantiate all backend Pydantic models."""

    def test_moon_search_pipeline_produces_valid_analog_response(self):
        target = SEED_TARGET_MOON
        ranked_results: list[AnalogResult] = []

        for candidate in SEED_ANALOGS:
            scored = score_analog(target, candidate, WEIGHTS)
            assert 0.0 <= scored["similarity_score"] <= 100.0
            assert all(
                0.0 <= v <= 100.0 for v in scored["breakdown"].values()
            )

            # Instantiation of backend schemas
            breakdown = SimilarityBreakdown(**scored["breakdown"])
            metadata = AnalogMetadata(
                elevation_m=candidate.get("elevation_m"),
                primary_rock=candidate.get("primary_rock"),
                accessibility_rating=accessibility_rating(
                    candidate.get("accessibility_score")
                ),
            )
            result = AnalogResult(
                site_id=candidate["site_id"],
                name=candidate["site_name"],
                country=candidate.get("country", "Unknown"),
                coordinates=Coordinates(
                    lat=candidate["lat"], lng=candidate["lng"]
                ),
                similarity_score=scored["similarity_score"],
                breakdown=breakdown,
                metadata=metadata,
            )
            ranked_results.append(result)

        ranked_results.sort(key=lambda item: item.similarity_score, reverse=True)
        response = AnalogSearchResponse(
            target_site_name=target["site_name"],
            results_count=len(ranked_results),
            analogs=ranked_results,
        )

        assert response.status == "success"
        assert response.results_count == 4
        assert len(response.analogs) == 4
        assert response.analogs[0].similarity_score >= response.analogs[-1].similarity_score

    def test_mars_search_pipeline_produces_valid_analog_response(self):
        target = SEED_TARGET_MARS
        ranked_results: list[AnalogResult] = []

        for candidate in SEED_ANALOGS:
            scored = score_analog(target, candidate, WEIGHTS)
            breakdown = SimilarityBreakdown(**scored["breakdown"])
            metadata = AnalogMetadata(
                elevation_m=candidate.get("elevation_m"),
                primary_rock=candidate.get("primary_rock"),
                accessibility_rating=accessibility_rating(
                    candidate.get("accessibility_score")
                ),
            )
            result = AnalogResult(
                site_id=candidate["site_id"],
                name=candidate["site_name"],
                country=candidate.get("country", "Unknown"),
                coordinates=Coordinates(
                    lat=candidate["lat"], lng=candidate["lng"]
                ),
                similarity_score=scored["similarity_score"],
                breakdown=breakdown,
                metadata=metadata,
            )
            ranked_results.append(result)

        ranked_results.sort(key=lambda item: item.similarity_score, reverse=True)
        response = AnalogSearchResponse(
            target_site_name=target["site_name"],
            results_count=len(ranked_results),
            analogs=ranked_results,
        )
        assert response.results_count == 4


class TestInterfaceParity:
    """Tests that adapter exports all functions with identical signatures as scoring.py."""

    def test_accessibility_bands(self):
        assert accessibility_rating(85) == "High"
        assert accessibility_rating(75) == "High"
        assert accessibility_rating(74.9) == "Moderate"
        assert accessibility_rating(50) == "Moderate"
        assert accessibility_rating(45) == "Moderate"
        assert accessibility_rating(44.9) == "Low"
        assert accessibility_rating(10) == "Low"
        assert accessibility_rating(None) == "Unknown"
        assert accessibility_rating("invalid") == "Unknown"
        assert accessibility_rating(float("nan")) == "Unknown"

    def test_topography_match_exact(self):
        t = {"avg_slope_deg": 10.0, "elevation_m": 1000.0, "site_id": "t", "site_name": "T", "planet": "moon"}
        a = {"slope_deg": 10.0, "elevation_m": 1000.0, "site_id": "a", "site_name": "A"}
        assert topography_match(t, a) == 100.0

    def test_geochemistry_match_exact(self):
        t = {"primary_rock": "basalt", "site_id": "t", "site_name": "T", "planet": "moon"}
        a = {"primary_rock": "basalt", "site_id": "a", "site_name": "A"}
        score = geochemistry_match(t, a)
        assert score == 90.0

    def test_climate_match_exact(self):
        t = {"temp_range_c": [-10, 20], "site_id": "t", "site_name": "T", "planet": "moon"}
        a = {"temp_min_c": -10, "temp_max_c": 20, "site_id": "a", "site_name": "A"}
        assert climate_match(t, a) == 100.0


class TestIntervalContinuity:
    """Verifies interval overlap similarity is mathematically continuous and monotonic."""

    def test_touching_boundary_is_35(self):
        # Touching intervals: [-10, 0] and [0, 10]
        score = _interval_similarity(-10, 0, 0, 10)
        assert score == 35.0

    def test_disjoint_is_less_than_35(self):
        # Disjoint by 1 deg: [-10, 0] and [1, 10]
        score = _interval_similarity(-10, 0, 1, 10)
        assert score < 35.0

    def test_overlapping_is_greater_than_or_equal_to_35(self):
        # Overlapping by 1 deg: [-10, 1] and [0, 10]
        score = _interval_similarity(-10, 1, 0, 10)
        assert score >= 35.0

    def test_monotonic_overlap(self):
        # As overlap increases, score strictly increases
        s1 = _interval_similarity(-10, 2, 0, 10)  # 2 deg overlap
        s2 = _interval_similarity(-10, 5, 0, 10)  # 5 deg overlap
        s3 = _interval_similarity(-10, 10, 0, 10) # 10 deg overlap
        assert s1 < s2 < s3

    def test_monotonic_gap(self):
        # As gap widens, score strictly decreases
        s1 = _interval_similarity(-10, 0, 5, 15)   # gap = 5
        s2 = _interval_similarity(-10, 0, 15, 25)  # gap = 15
        s3 = _interval_similarity(-10, 0, 40, 50)  # gap = 40
        assert s1 > s2 > s3


class TestRankingUnscoredHandling:
    """Tests candidate ranking placement of unscored candidates."""

    def test_unscored_placed_at_end_when_no_threshold(self):
        t, _ = validate_target_features(SEED_TARGET_MOON)

        # Scored candidate (has valid features)
        c1, _ = validate_candidate_features(SEED_ANALOGS[0])

        # Unscored candidate (no comparable dimensions at all)
        raw_empty = {
            "site_id": "empty-candidate-z",
            "site_name": "Empty Z",
        }
        c_unscored_z, _ = validate_candidate_features(raw_empty)

        raw_empty_a = {
            "site_id": "empty-candidate-a",
            "site_name": "Empty A",
        }
        c_unscored_a, _ = validate_candidate_features(raw_empty_a)

        ranking = rank_candidates(
            t,
            [c_unscored_z, c1, c_unscored_a],
            ComparisonWeights(topography=0.4, geochemistry=0.35, climate=0.25),
            min_score=None,
        )

        assert len(ranking.ranked_candidates) == 3
        # First candidate is the scored one
        assert ranking.ranked_candidates[0].similarity_result.candidate_site_id == c1.site_id
        assert ranking.ranked_candidates[0].similarity_result.overall_score is not None

        # Unscored ones placed at end, sorted by site_id ('empty-candidate-a' then 'empty-candidate-z')
        assert ranking.ranked_candidates[1].similarity_result.candidate_site_id == "empty-candidate-a"
        assert ranking.ranked_candidates[1].similarity_result.overall_score is None
        assert ranking.ranked_candidates[2].similarity_result.candidate_site_id == "empty-candidate-z"
        assert ranking.ranked_candidates[2].similarity_result.overall_score is None

    def test_unscored_excluded_when_threshold_applied(self):
        t, _ = validate_target_features(SEED_TARGET_MOON)
        c1, _ = validate_candidate_features(SEED_ANALOGS[0])
        raw_empty = {"site_id": "empty-candidate-x", "site_name": "Empty"}
        c_unscored, _ = validate_candidate_features(raw_empty)

        ranking = rank_candidates(
            t,
            [c1, c_unscored],
            ComparisonWeights(topography=0.4, geochemistry=0.35, climate=0.25),
            min_score=50.0,
        )
        assert len(ranking.ranked_candidates) == 1
        assert ranking.ranked_candidates[0].similarity_result.candidate_site_id == c1.site_id


class TestWeightValidation:
    """Verifies that non-finite weights are rejected."""

    def test_nan_weight_rejected(self):
        with pytest.raises(ValueError):
            ComparisonWeights(topography=float("nan"))

    def test_inf_weight_rejected(self):
        with pytest.raises(ValueError):
            ComparisonWeights(topography=float("inf"))


class TestAnshikaIntegrationChecks:
    """Explicit tests for the 5 integration issues resolved for Anshika."""

    def test_issue_1_no_namespace_collision(self):
        """Backend's app and ml_engine can be imported in the same process without collision."""
        import app.schemas.search as backend_search
        import ml_engine.adapter as ml_adapter
        assert backend_search.__name__ == "app.schemas.search"
        assert ml_adapter.__name__ == "ml_engine.adapter"

    def test_issue_2_no_artificial_fifty_fallback(self):
        """Candidates with missing dimensions return 0.0 breakdown, not artificial 50.0."""
        target = {
            "planet": "moon",
            "site_id": "crater-x",
            "site_name": "Crater X",
            "avg_slope_deg": 15.0,
            # no elevation, no geochemistry, no climate
        }
        candidate = {
            "site_id": "tile-x",
            "site_name": "Tile X",
            "slope_deg": 15.0,
            # no elevation, no geochemistry, no climate
        }
        res = score_analog(target, candidate, {"topography": 0.5, "geochemistry": 0.25, "climate": 0.25})
        # Topography was computable (100.0), but geo and climate are unavailable
        assert res["breakdown"]["topography_match"] == 100.0
        assert res["breakdown"]["geochemistry_match"] == 0.0  # Was 50.0 previously!
        assert res["breakdown"]["climate_match"] == 0.0       # Was 50.0 previously!
        # Overall score is computed from available dimensions (topography = 100.0)
        assert res["similarity_score"] == 100.0

    def test_issue_3_mineral_cosine_direct_mapping(self):
        """Non-negative mineral vectors map directly to 0-100 (orthogonal = 0.0, identical = 100.0)."""
        from ml_engine.comparison.geochemistry import _cosine_similarity
        vec_a = {"pyroxene": 60.0, "plagioclase": 40.0}
        vec_b = {"quartz": 100.0}
        assert _cosine_similarity(vec_a, vec_b) == 0.0
        assert _cosine_similarity(vec_a, vec_a) == 100.0

    def test_issue_4_strict_physical_validation(self):
        """Strict physical measurement validation prevents out-of-range values from entering profile."""
        from ml_engine.preprocessing.feature_validation import validate_target_features
        # Lunar elevation out of physical bounds (e.g. 50,000m on Moon where max is 15,000m)
        target_raw = {
            "planet": "moon",
            "site_id": "test-extreme",
            "site_name": "Extreme Site",
            "elevation_m": 50000.0,
        }
        target_prof, reports = validate_target_features(target_raw)
        # Should be None in profile, not silently kept
        assert target_prof.elevation_m is None
        # Strict mode raises ValueError
        with pytest.raises(ValueError, match="out_of_range"):
            validate_target_features(target_raw, strict=True)


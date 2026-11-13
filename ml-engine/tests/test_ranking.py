"""Tests for the candidate ranking system."""
from __future__ import annotations

import pytest

from ml_engine.models.schemas import (
    ComparisonWeights,
    EarthCandidate,
    Planet,
    PlanetaryTarget,
)
from ml_engine.ranking.candidate_ranking import rank_candidates


def _make_target(**kw) -> PlanetaryTarget:
    defaults = dict(
        planet=Planet.MOON, site_id="syn-t", site_name="Syn Target",
        elevation_m=-4000.0, avg_slope_deg=12.5,
        primary_rock="basalt", temp_range_c=(-80.0, 20.0),
        data_source="synthetic_test",
    )
    defaults.update(kw)
    return PlanetaryTarget(**defaults)


def _make_cand(site_id: str, elev: float, slope: float, rock: str = "basalt",
               tmin: float = -15.0, tmax: float = 35.0) -> EarthCandidate:
    return EarthCandidate(
        site_id=site_id, site_name=f"Cand {site_id}",
        elevation_m=elev, slope_deg=slope, primary_rock=rock,
        temp_min_c=tmin, temp_max_c=tmax,
        data_source="synthetic_test",
    )


class TestRanking:
    def test_empty_candidates(self):
        t = _make_target()
        result = rank_candidates(t, [], ComparisonWeights())
        assert result.total_candidates_evaluated == 0
        assert len(result.ranked_candidates) == 0

    def test_single_candidate(self):
        t = _make_target()
        c = [_make_cand("c1", 2300, 11)]
        result = rank_candidates(t, c, ComparisonWeights())
        assert result.total_candidates_evaluated == 1
        assert len(result.ranked_candidates) == 1
        assert result.ranked_candidates[0].rank == 1

    def test_multiple_candidates_sorted(self):
        t = _make_target(elevation_m=1000, avg_slope_deg=10)
        # c1 is closer to target than c2
        c1 = _make_cand("c1", 1000, 10)
        c2 = _make_cand("c2", 5000, 30)
        result = rank_candidates(t, [c2, c1], ComparisonWeights())
        assert result.ranked_candidates[0].similarity_result.candidate_site_id == "c1"

    def test_threshold_filters(self):
        t = _make_target()
        cands = [_make_cand(f"c{i}", i * 1000, i * 5) for i in range(5)]
        result = rank_candidates(
            t, cands, ComparisonWeights(), min_score=90.0,
        )
        for rc in result.ranked_candidates:
            assert rc.similarity_result.overall_score is not None
            assert rc.similarity_result.overall_score >= 90.0

    def test_limit(self):
        t = _make_target()
        cands = [_make_cand(f"c{i}", i * 100, 10) for i in range(10)]
        result = rank_candidates(t, cands, ComparisonWeights(), limit=3)
        assert len(result.ranked_candidates) <= 3

    def test_deterministic_tie_breaking(self):
        """Equal scores should be ordered by site_id (ascending)."""
        t = _make_target(elevation_m=1000, avg_slope_deg=10)
        c1 = _make_cand("aaa", 1000, 10, tmin=-15, tmax=35)
        c2 = _make_cand("bbb", 1000, 10, tmin=-15, tmax=35)
        r1 = rank_candidates(t, [c1, c2], ComparisonWeights())
        r2 = rank_candidates(t, [c2, c1], ComparisonWeights())
        ids_1 = [r.similarity_result.candidate_site_id
                 for r in r1.ranked_candidates]
        ids_2 = [r.similarity_result.candidate_site_id
                 for r in r2.ranked_candidates]
        assert ids_1 == ids_2

    def test_ranks_are_sequential(self):
        t = _make_target()
        cands = [_make_cand(f"c{i}", i * 100, 10) for i in range(5)]
        result = rank_candidates(t, cands, ComparisonWeights())
        ranks = [rc.rank for rc in result.ranked_candidates]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_weight_sensitivity(self):
        """Changing weights should affect ranking order."""
        t = _make_target(
            elevation_m=1000, avg_slope_deg=10,
            temp_range_c=(-10.0, 5.0),
        )
        # c1: close elevation, far temperature
        c1 = _make_cand("c1", 1000, 10, tmin=-50, tmax=-30)
        # c2: far elevation, close temperature
        c2 = _make_cand("c2", 8000, 40, tmin=-10, tmax=5)

        w_topo = ComparisonWeights(topography=1.0, geochemistry=0, climate=0)
        w_clim = ComparisonWeights(topography=0, geochemistry=0, climate=1.0)

        r_topo = rank_candidates(t, [c1, c2], w_topo)
        r_clim = rank_candidates(t, [c1, c2], w_clim)

        # With topography-only weights, c1 should rank higher
        if len(r_topo.ranked_candidates) >= 2:
            assert (
                r_topo.ranked_candidates[0]
                .similarity_result.candidate_site_id == "c1"
            )

        # With climate-only weights, c2 should rank higher
        if len(r_clim.ranked_candidates) >= 2:
            assert (
                r_clim.ranked_candidates[0]
                .similarity_result.candidate_site_id == "c2"
            )

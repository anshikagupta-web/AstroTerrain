"""Synthetic demo — shows how the ML Engine processes a comparison.

IMPORTANT: This uses SYNTHETIC test data only. These are NOT real
scientific measurements. They are used to demonstrate the software
pipeline and verify that the code runs correctly.
"""
from __future__ import annotations

import json
import sys
import os

# Add ml-engine root to path so we can import ml_engine.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_engine.adapter import score_analog
from ml_engine.preprocessing.feature_validation import (
    validate_target_features,
    validate_candidate_features,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity
from ml_engine.explainability.explanations import generate_explanation
from ml_engine.ranking.candidate_ranking import rank_candidates
from ml_engine.reporting.site_reports import generate_site_report, render_report_text
from ml_engine.models.schemas import ComparisonWeights


# --- SYNTHETIC TEST DATA (clearly labelled) ---

SYNTHETIC_TARGET = {
    "planet": "moon",
    "site_id": "shackleton-demo",
    "site_name": "Shackleton Crater (SYNTHETIC DEMO)",
    "lat": -89.9,
    "lng": 0.0,
    "avg_slope_deg": 12.5,
    "elevation_m": -4000.0,
    "regolith_composition": {
        "basalt_pct": 35,
        "silica_pct": 28,
        "iron_oxide_pct": 12,
    },
    "primary_rock": "basalt",
    "temp_range_c": [-80, 20],
    "data_source": "synthetic_demo",
}

SYNTHETIC_CANDIDATES = [
    {
        "site_id": "demo-atacama",
        "site_name": "Atacama-like (SYNTHETIC)",
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
        "data_source": "synthetic_demo",
    },
    {
        "site_id": "demo-hawaii",
        "site_name": "Hawaii-like (SYNTHETIC)",
        "country": "DEMO",
        "lat": 19.5,
        "lng": -155.5,
        "elevation_m": 900.0,
        "slope_deg": 7.5,
        "ndvi": 0.28,
        "spectral_signature": {"mean_ndvi": 0.28},
        "primary_rock": "basalt",
        "temp_min_c": -5.0,
        "temp_max_c": 30.0,
        "accessibility_score": 82.0,
        "data_source": "synthetic_demo",
    },
    {
        "site_id": "demo-svalbard",
        "site_name": "Svalbard-like (SYNTHETIC)",
        "country": "DEMO",
        "lat": 78.0,
        "lng": 16.0,
        "elevation_m": 120.0,
        "slope_deg": 18.0,
        "ndvi": 0.05,
        "spectral_signature": {"mean_ndvi": 0.05},
        "primary_rock": "volcanic rock",
        "temp_min_c": -25.0,
        "temp_max_c": 12.0,
        "accessibility_score": 55.0,
        "is_subterranean": True,
        "data_source": "synthetic_demo",
    },
    {
        "site_id": "demo-mcmurdo",
        "site_name": "McMurdo-like (SYNTHETIC)",
        "country": "DEMO",
        "lat": -77.5,
        "lng": 161.0,
        "elevation_m": 300.0,
        "slope_deg": 5.0,
        "ndvi": 0.18,
        "spectral_signature": {"mean_ndvi": 0.18},
        "primary_rock": "basalt",
        "temp_min_c": -35.0,
        "temp_max_c": 5.0,
        "accessibility_score": 38.0,
        "data_source": "synthetic_demo",
    },
]


def main() -> None:
    print("=" * 72)
    print("  AstroTerrain ML Engine -- Synthetic Demo")
    print("  NOTE: All data is SYNTHETIC. Not real measurements.")
    print("=" * 72)
    print()

    # ---------------------------------------------------------------
    # 1. Backend adapter demo (drop-in replacement)
    # ---------------------------------------------------------------
    print("--- 1. Backend Adapter (score_analog) ---")
    weights = {"topography": 0.4, "geochemistry": 0.35, "climate": 0.25}
    for cand in SYNTHETIC_CANDIDATES:
        result = score_analog(SYNTHETIC_TARGET, cand, weights)
        print(f"  {cand['site_name']}: {result['similarity_score']:.1f}")
        print(f"    Breakdown: {json.dumps(result['breakdown'], indent=6)}")
        meta = result["ml_engine_metadata"]
        if meta["unavailable_dimensions"]:
            print(f"    Unavailable: {meta['unavailable_dimensions']}")
        print()

    # ---------------------------------------------------------------
    # 2. Full ML pipeline demo
    # ---------------------------------------------------------------
    print("--- 2. Full Pipeline: Validate -> Compare -> Rank -> Explain ---")

    target, t_reports = validate_target_features(SYNTHETIC_TARGET)
    print(f"  Target: {target.site_name} ({target.planet.value})")

    candidates = []
    for raw in SYNTHETIC_CANDIDATES:
        cand, _ = validate_candidate_features(raw)
        candidates.append(cand)

    comp_weights = ComparisonWeights(
        topography=0.4, geochemistry=0.35, climate=0.25,
    )
    ranking = rank_candidates(
        target, candidates, comp_weights, min_score=0, limit=10,
    )

    print(f"  Candidates evaluated: {ranking.total_candidates_evaluated}")
    print(f"  Candidates ranked:    {len(ranking.ranked_candidates)}")
    print()

    for rc in ranking.ranked_candidates:
        sr = rc.similarity_result
        print(f"  Rank {rc.rank}: {sr.candidate_site_name}")
        print(f"    Overall: {sr.overall_score}")
        print(f"    Complete: {sr.is_complete}")
        for d in sr.dimensions:
            print(
                f"    {d.dimension}: {d.score} "
                f"(status={d.status.value}, w_eff={d.weight_effective:.3f})"
            )
        print()

    # ---------------------------------------------------------------
    # 3. Report demo
    # ---------------------------------------------------------------
    print("--- 3. Site Report ---")
    if ranking.ranked_candidates:
        best = ranking.ranked_candidates[0]
        best_cand = next(
            c for c in candidates
            if c.site_id == best.similarity_result.candidate_site_id
        )
        report = generate_site_report(
            target, best_cand, best.similarity_result,
        )
        text = render_report_text(report)
        print(text)

    print("\n--- Demo complete ---")


if __name__ == "__main__":
    main()

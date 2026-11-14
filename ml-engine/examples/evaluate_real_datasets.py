"""Evaluate Real Scientific Datasets with AstroTerrain Module 4 ML Engine.

Processes real scientific observations:
- Earth Candidates: Hawaii, Svalbard, Atacama, and Antarctica (Copernicus GLO-90 DEM extractions + NASA POWER daily climate data).
- Planetary Targets:
  * Mars: Jezero Crater Delta (MOLA + MEDA), Pavonis Mons Pit (MOLA + HiRISE)
  * Moon: Shackleton Crater (LOLA + Diviner anomalies), Marius Hills Pit (LOLA + Kaguya)

Evaluates:
- Dimension-level similarity scores (slope-only Gaussian topography, continuous climate interval overlap, rock-type geochemistry).
- Effective weight redistribution when dimensions are unavailable.
- Deterministic candidate ranking (-similarity_score, site_id).
- Complete data provenance, warnings, and scientific limitations.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# Ensure ml_engine is on path
_ML_ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(_ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ENGINE_ROOT))

from ml_engine.adapter import score_analog
from ml_engine.data_loader import (
    get_real_earth_candidates,
    get_real_planetary_targets,
)


def evaluate_target_against_real_candidates(
    target: dict[str, Any],
    candidates: list[dict[str, Any]],
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Score all real candidates against a planetary target and return deterministically ranked results."""
    weights = weights or {"topography": 0.35, "climate": 0.35, "geochemistry": 0.30}

    scored_candidates: list[dict[str, Any]] = []
    for cand in candidates:
        scored = score_analog(target, cand, weights)
        ml_meta = scored.get("ml_engine_metadata") or {}

        # Capture feature availability
        available_features: list[str] = []
        missing_features: list[str] = []

        if cand.get("slope_deg") is not None and target.get("avg_slope_deg") is not None:
            available_features.append(f"Topography / Slope (target={target['avg_slope_deg']}°, cand={cand['slope_deg']:.2f}°) [Derived from DEM]")
        else:
            missing_features.append("Topography / Slope (Missing DEM slope)")

        if cand.get("primary_rock") and target.get("primary_rock"):
            available_features.append(f"Geochemistry / Rock (target='{target['primary_rock']}', cand='{cand['primary_rock']}') [Literature-derived classification]")
        else:
            missing_features.append("Geochemistry / Rock (Missing classification)")

        target_temp_type = target.get("temp_measurement_type", "unknown")
        cand_temp_type = cand.get("temp_measurement_type", "unknown")
        if "climate" in ml_meta.get("unavailable_dimensions", []):
            missing_features.append(
                f"Climate / Temperature [EXCLUDED]: Incompatible measurement types — "
                f"Target uses '{target_temp_type}' ({target.get('temp_range_c')}°C), "
                f"Candidate uses '{cand_temp_type}' ([{cand.get('temp_min_c')}, {cand.get('temp_max_c')}]°C). "
                f"Direct comparison without boundary layer model is unphysical."
            )
        elif cand.get("temp_min_c") is not None and cand.get("temp_max_c") is not None and target.get("temp_range_c") is not None:
            available_features.append(
                f"Climate / Temperature (target=[{target['temp_range_c'][0]}, {target['temp_range_c'][1]}]°C [{target_temp_type}], "
                f"cand=[{cand['temp_min_c']}, {cand['temp_max_c']}]°C [{cand_temp_type}])"
            )
        else:
            missing_features.append("Climate / Temperature (Data missing)")

        missing_features.append("Mineral Abundance [UNAVAILABLE]: Calibrated hyperspectral cubes not available")
        missing_features.append("NDVI [UNAVAILABLE]: Aligned Red/NIR reflectance not available")

        result = {
            "site_id": cand["site_id"],
            "site_name": cand["site_name"],
            "country": cand.get("country", "Unknown"),
            "similarity_score": scored["similarity_score"],
            "breakdown": scored["breakdown"],
            "weights_used": ml_meta.get("effective_weights", scored.get("weights_used", {})),
            "available_features": available_features,
            "missing_features": missing_features,
            "unavailable_dimensions": ml_meta.get("unavailable_dimensions", []),
            "warnings": ml_meta.get("warnings", []),
            "is_complete": ml_meta.get("is_complete", True),
            "data_source": cand.get("data_source"),
            "target_id": target["site_id"],
            "target_planet": target.get("planet"),
            "target_data_source": target.get("data_source"),
        }
        scored_candidates.append(result)

    # Deterministic ranking: descending score, then site_id tie-breaker
    scored_candidates.sort(key=lambda x: (-x["similarity_score"], x["site_id"]))
    return scored_candidates


def print_evaluation_summary(target: dict[str, Any], ranked_results: list[dict[str, Any]]) -> None:
    """Print formatted evaluation summary to stdout."""
    print("=" * 80)
    print(f"PLANETARY TARGET: {target['site_name']} ({target.get('planet', '').upper()})")
    print(f"  Target ID: {target['site_id']}")
    print(f"  Coordinates: {target.get('lat')}° N, {target.get('lng')}° E")
    print(f"  Slope: {target.get('avg_slope_deg')}° | Elevation: {target.get('elevation_m')} m (Datum-excluded)")
    print(f"  Temperature Range: {target.get('temp_range_c')} °C")
    print(f"  Primary Rock: {target.get('primary_rock')}")
    print(f"  Data Source: {target.get('data_source')}")
    if "scientific_metadata" in target:
        for k, v in target["scientific_metadata"].items():
            print(f"  * {k}: {v}")
    print("-" * 80)

    for rank, res in enumerate(ranked_results, start=1):
        print(f"\n#{rank} [Score: {res['similarity_score']:.2f}/100] — {res['site_name']} ({res['country']})")
        print(f"   Site ID: {res['site_id']} | Source: {res['data_source']}")
        print(f"   Breakdown: Topography={res['breakdown']['topography_match']:.2f} | "
              f"Geochemistry={res['breakdown']['geochemistry_match']:.2f} | "
              f"Climate={res['breakdown']['climate_match']:.2f}")
        print(f"   Effective Weights: {res['weights_used']}")

        print("   Available Features:")
        for feat in res["available_features"]:
            print(f"     + {feat}")

        print("   Unavailable / Missing Features:")
        for feat in res["missing_features"]:
            print(f"     - {feat}")

        if res["warnings"]:
            print("   Scientific Warnings & Constraints:")
            for w in res["warnings"]:
                print(f"     ! {w}")
    print("=" * 80 + "\n")


def main() -> None:
    print("ASTROTERRAIN MODULE 4 — REAL SCIENTIFIC DATASET EVALUATION")
    print("Connecting NASA POWER, Copernicus GLO-90 DEM, LOLA, MOLA, and Diviner Data\n")

    candidates = get_real_earth_candidates()
    targets = get_real_planetary_targets()

    print(f"Loaded {len(candidates)} Real Earth Candidates:")
    for c in candidates:
        print(f" - {c['site_id']}: {c['site_name']} (elev={c['elevation_m']}m, slope={c['slope_deg']:.2f}°, "
              f"T=[{c['temp_min_c']}, {c['temp_max_c']}]°C)")

    print(f"\nLoaded {len(targets)} Real Planetary Targets:")
    for t in targets:
        print(f" - {t['site_id']} ({t['planet']}): {t['site_name']} (elev={t['elevation_m']}m, slope={t['avg_slope_deg']}°, "
              f"T={t['temp_range_c']}°C)")
    print()

    # Evaluate each target
    for target in targets:
        ranked = evaluate_target_against_real_candidates(target, candidates)
        print_evaluation_summary(target, ranked)


if __name__ == "__main__":
    main()

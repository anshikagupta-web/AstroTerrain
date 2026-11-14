"""Geochemical / spectral similarity comparison.

.. important::

   The current backend stores **NDVI** (Normalised Difference Vegetation
   Index) in ``spectral_signature``.  NDVI measures vegetation density --
   it has **no relationship** to mineral composition.

   This module will **not** produce a score from NDVI data.  It explicitly
   reports the dimension as ``UNAVAILABLE`` when compatible mineralogical
   measurements are absent.

Methodology (when real mineral data is available)
-------------------------------------------------
1. If both sides have mineral-composition vectors (e.g. ``basalt_pct``,
   ``silica_pct``), compare them using **direct cosine similarity**
   across the full mineral vector space.
   Because mineral percentage vectors are non-negative (u_k >= 0, v_k >= 0),
   cos(theta) lies strictly in [0.0, 1.0]. The similarity is directly:
   sim = cos(theta) * 100.0.
   Orthogonal composition vectors (zero shared minerals) yield 0.0%.
   Identical composition vectors yield 100.0%.
2. If only ``primary_rock`` is available, perform a categorical match.
3. Otherwise -> ``UNAVAILABLE``.
"""
from __future__ import annotations

import math
from typing import Any

from ml_engine.models.schemas import (
    DimensionResult,
    DimensionStatus,
    EarthCandidate,
    PlanetaryTarget,
)

# Keys that are NDVI / vegetation-related -- must NOT be treated as mineralogy
_NDVI_KEYS = frozenset({
    "mean_ndvi", "min_ndvi", "max_ndvi", "ndvi",
    "valid_pixels", "ndvi_std",
})

# Keys that indicate genuine mineralogical composition data
_MINERAL_KEYS = frozenset({
    "basalt_pct", "silica_pct", "iron_oxide_pct", "olivine_pct",
    "pyroxene_pct", "feldspar_pct", "calcium_pct", "magnesium_pct",
    "aluminum_pct", "titanium_pct", "sulfur_pct",
})

# Rock-type geological families for categorical comparison
_ROCK_FAMILIES: dict[str, str] = {
    "basalt": "igneous_mafic",
    "basaltic sediment": "igneous_mafic",
    "gabbro": "igneous_mafic",
    "andesite": "igneous_intermediate",
    "diorite": "igneous_intermediate",
    "granite": "igneous_felsic",
    "rhyolite": "igneous_felsic",
    "volcanic rock": "igneous_general",
    "sandstone": "sedimentary_clastic",
    "shale": "sedimentary_clastic",
    "limestone": "sedimentary_carbonate",
    "marble": "metamorphic",
    "gneiss": "metamorphic",
    "schist": "metamorphic",
    "quartzite": "metamorphic",
}

ROCK_EXACT_MATCH_SCORE = 90.0
ROCK_FAMILY_MATCH_SCORE = 60.0
ROCK_NO_MATCH_SCORE = 20.0


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _is_ndvi_data(spectral_dict: dict[str, Any]) -> bool:
    """True if *all* keys are known NDVI-related -> no mineral info."""
    if not spectral_dict:
        return True
    return all(k.lower() in _NDVI_KEYS for k in spectral_dict)


def _extract_minerals(data: dict[str, Any]) -> dict[str, float]:
    """Extract mineral-percentage values from a composition dict."""
    minerals: dict[str, float] = {}
    for key, value in data.items():
        if key.lower() in _MINERAL_KEYS:
            try:
                fval = float(value)
                if math.isfinite(fval) and fval >= 0.0:
                    minerals[key.lower()] = fval
            except (TypeError, ValueError):
                continue
    return minerals


def _cosine_similarity(
    vec_a: dict[str, float], vec_b: dict[str, float],
) -> float | None:
    """Direct cosine similarity over the combined mineral space, in [0, 100].

    For non-negative vectors, cos(theta) in [0.0, 1.0].
    Direct mapping: score = cos(theta) * 100.0.
    Orthogonal vectors (zero shared minerals) yield 0.0%.
    """
    all_keys = set(vec_a) | set(vec_b)
    if not all_keys:
        return None

    dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in all_keys)
    mag_a = math.sqrt(sum(vec_a.get(k, 0.0) ** 2 for k in all_keys))
    mag_b = math.sqrt(sum(vec_b.get(k, 0.0) ** 2 for k in all_keys))

    if mag_a <= 0 or mag_b <= 0:
        return None

    cos = max(0.0, min(1.0, dot / (mag_a * mag_b)))
    return round(cos * 100.0, 2)


def _compare_rocks(
    a: str | None, b: str | None,
) -> tuple[float | None, str]:
    if not a or not b:
        return None, "One or both rock types unavailable."
    a_l, b_l = a.strip().lower(), b.strip().lower()
    if a_l == b_l:
        return ROCK_EXACT_MATCH_SCORE, f"Exact rock-type match: '{a_l}'."
    fa = _ROCK_FAMILIES.get(a_l)
    fb = _ROCK_FAMILIES.get(b_l)
    if fa and fb and fa == fb:
        return (
            ROCK_FAMILY_MATCH_SCORE,
            f"Same geological family ({fa}): target='{a_l}', candidate='{b_l}'.",
        )
    return (
        ROCK_NO_MATCH_SCORE,
        f"Different rock types: target='{a_l}', candidate='{b_l}'.",
    )


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def compare_geochemistry(
    target: PlanetaryTarget,
    candidate: EarthCandidate,
) -> DimensionResult:
    """Compare geochemical / mineralogical features.

    This function performs a **rigorous data-compatibility check** before
    attempting any comparison.  It will **not** produce a score from NDVI.

    Priority:
        1. Mineral composition vectors -> direct cosine similarity.
        2. ``primary_rock`` categorical match (fallback).
        3. ``UNAVAILABLE`` when neither can be performed.
    """
    features_compared: list[str] = []
    features_missing: list[str] = []
    warnings: list[str] = []

    target_minerals = _extract_minerals(target.regolith_composition)

    candidate_spectral = candidate.spectral_signature
    if _is_ndvi_data(candidate_spectral):
        warnings.append(
            "Candidate 'spectral_signature' contains only NDVI (vegetation "
            "index) data.  NDVI cannot be used for mineralogical comparison. "
            "Mineral composition data is required for this dimension."
        )
        candidate_minerals: dict[str, float] = {}
    else:
        candidate_minerals = _extract_minerals(candidate_spectral)

    mineral_score: float | None = None
    mineral_method = ""

    if target_minerals and candidate_minerals:
        shared = set(target_minerals) & set(candidate_minerals)
        mineral_score = _cosine_similarity(target_minerals, candidate_minerals)
        if mineral_score is not None:
            features_compared.append("mineral_composition")
            mineral_method = (
                f"Direct cosine similarity on non-negative mineral vectors: "
                f"{mineral_score:.2f}% across {len(set(target_minerals) | set(candidate_minerals))} "
                f"components ({len(shared)} shared)."
            )
            if not shared:
                warnings.append(
                    "Target and candidate have mineral measurements but zero shared phases (orthogonal mineral composition, 0.0% similarity)."
                )
    else:
        if not target_minerals:
            features_missing.append("target_mineral_composition")
        if not candidate_minerals:
            features_missing.append("candidate_mineral_composition")

    rock_score, rock_method = _compare_rocks(
        target.primary_rock, candidate.primary_rock,
    )
    if rock_score is not None:
        features_compared.append("primary_rock")
    else:
        features_missing.append("primary_rock")

    # --- Aggregate ---
    if mineral_score is not None:
        if rock_score is not None:
            final = round(0.7 * mineral_score + 0.3 * rock_score, 2)
            method = (
                f"Weighted: 70% mineral ({mineral_method}), "
                f"30% rock ({rock_method})"
            )
        else:
            final = mineral_score
            method = mineral_method
    elif rock_score is not None:
        final = rock_score
        method = f"Literature-derived categorical rock classification (no quantitative mineral data): {rock_method}"
        warnings.append(
            "Geochemistry score is based solely on literature-derived categorical "
            "rock classification, not quantitative mineralogical observations. "
            "Calibrated mineral reflectance spectra are required for quantitative mineral comparison."
        )
    else:
        return DimensionResult(
            dimension="geochemistry",
            status=DimensionStatus.UNAVAILABLE,
            features_compared=features_compared,
            features_missing=features_missing,
            methodology=(
                "No compatible geochemical measurements available. "
                "Requires mineral composition data or matching rock-type "
                "information on both target and candidate."
            ),
            warnings=warnings,
        )

    return DimensionResult(
        dimension="geochemistry",
        score=final,
        status=DimensionStatus.COMPUTED,
        features_compared=features_compared,
        features_missing=features_missing,
        methodology=method,
        warnings=warnings,
    )

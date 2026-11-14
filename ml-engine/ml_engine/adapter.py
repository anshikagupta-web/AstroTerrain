"""Backend integration adapter for the AstroTerrain ML Engine.

Provides a **drop-in replacement** for the backend's ``score_analog()``
function while routing computation through the full ML Engine pipeline.

Integration contract
--------------------
The backend calls::

    score_analog(target, analog, weights) -> dict

And expects::

    {
        "similarity_score": float,       # 0-100
        "breakdown": {
            "topography_match": float,   # 0-100
            "geochemistry_match": float, # 0-100
            "climate_match": float,      # 0-100
        }
    }

Policy for unavailable dimensions
---------------------------------
The backend ``SimilarityBreakdown`` requires all three breakdown fields
as plain floats.  When a dimension is **UNAVAILABLE** due to missing or
insufficient data, this adapter assigns **0.0** for that dimension in the
breakdown (strictly removing the artificial 50.0 fallback).

If no positively-weighted dimensions can be computed, ``similarity_score``
is set to 0.0 and ``insufficient_data`` is flagged in ``ml_engine_metadata``.
Candidates with insufficient available data will not receive artificial
scores or falsely rank in search results.

Interface Parity
----------------
This adapter also provides:
* ``accessibility_rating(score) -> str``
* ``topography_match(target, analog) -> float``
* ``geochemistry_match(target, analog) -> float``
* ``climate_match(target, analog) -> float``
making it a 100% complete replacement for ``backend/app/services/scoring.py``.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from ml_engine.models.schemas import ComparisonWeights, DimensionStatus
from ml_engine.preprocessing.feature_validation import (
    validate_target_features,
    validate_candidate_features,
)
from ml_engine.comparison.similarity import calculate_weighted_similarity
from ml_engine.explainability.explanations import generate_explanation


def accessibility_rating(score: Any) -> str:
    """Categorise an accessibility score into Low / Moderate / High / Unknown.

    Direct drop-in replacement for ``app.services.scoring.accessibility_rating``.
    """
    if score is None:
        return "Unknown"
    try:
        val = float(score)
    except (TypeError, ValueError):
        return "Unknown"
    if not math.isfinite(val):
        return "Unknown"
    if val >= 75.0:
        return "High"
    if val >= 45.0:
        return "Moderate"
    return "Low"


def score_analog(
    target: Mapping[str, Any],
    analog: Mapping[str, Any],
    weights: Mapping[str, float],
) -> dict[str, Any]:
    """Score an Earth analogue against a planetary target.

    Drop-in replacement for the backend's ``score_analog()``.

    Returns:
        Dict matching the backend contract, plus an optional
        ``ml_engine_metadata`` key with full explainability data.

    Raises:
        ValueError: If all weights are zero or negative, or weights non-finite.
    """
    # --- Parse weights ---
    w_topo = float(weights.get("topography", 0))
    w_geo = float(weights.get("geochemistry", 0))
    w_clim = float(weights.get("climate", 0))

    for w in (w_topo, w_geo, w_clim):
        if not math.isfinite(w):
            raise ValueError("Weights must be finite numbers.")
        if w < 0:
            raise ValueError("Weights must be non-negative.")

    if w_topo + w_geo + w_clim <= 0:
        raise ValueError(
            "At least one similarity weight must be greater than zero."
        )

    comp_weights = ComparisonWeights(
        topography=w_topo, geochemistry=w_geo, climate=w_clim,
    )

    # --- Validate and build profiles ---
    target_profile, _ = validate_target_features(dict(target))
    candidate_profile, _ = validate_candidate_features(dict(analog))

    # --- Run similarity calculation ---
    result = calculate_weighted_similarity(
        target_profile, candidate_profile, comp_weights,
    )

    # --- Map dimension scores to backend contract ---
    dim_scores: dict[str, float | None] = {}
    unavailable_dims: list[str] = []

    for d in result.dimensions:
        if d.status == DimensionStatus.COMPUTED and d.score is not None:
            dim_scores[d.dimension] = d.score
        else:
            dim_scores[d.dimension] = None
            if d.weight_requested > 0:
                unavailable_dims.append(d.dimension)

    breakdown = {
        "topography_match": round(
            dim_scores["topography"]
            if dim_scores.get("topography") is not None
            else 0.0,
            2,
        ),
        "geochemistry_match": round(
            dim_scores["geochemistry"]
            if dim_scores.get("geochemistry") is not None
            else 0.0,
            2,
        ),
        "climate_match": round(
            dim_scores["climate"]
            if dim_scores.get("climate") is not None
            else 0.0,
            2,
        ),
    }

    # --- Overall score ---
    # When no positively-weighted dimensions can be computed (result.overall_score is None),
    # return 0.0 rather than an artificial fallback score.
    if result.overall_score is not None:
        final = round(result.overall_score, 2)
    else:
        final = 0.0

    final = max(0.0, min(100.0, final))

    explanation = generate_explanation(result)

    return {
        "similarity_score": final,
        "breakdown": breakdown,
        "ml_engine_metadata": {
            "insufficient_data": result.overall_score is None,
            "is_complete": result.is_complete,
            "dimensions_computed": result.dimensions_computed,
            "dimensions_unavailable": result.dimensions_unavailable,
            "unavailable_dimensions": unavailable_dims,
            "warnings": result.warnings,
            "explanation": explanation.model_dump(),
        },
    }


def topography_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float:
    """Convenience helper for topography similarity, returning 0.0-100.0."""
    res = score_analog(target, analog, {"topography": 1.0, "geochemistry": 0.0, "climate": 0.0})
    return res["breakdown"]["topography_match"]


def geochemistry_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float:
    """Convenience helper for geochemistry similarity, returning 0.0-100.0."""
    res = score_analog(target, analog, {"topography": 0.0, "geochemistry": 1.0, "climate": 0.0})
    return res["breakdown"]["geochemistry_match"]


def climate_match(target: Mapping[str, Any], analog: Mapping[str, Any]) -> float:
    """Convenience helper for climate similarity, returning 0.0-100.0."""
    res = score_analog(target, analog, {"topography": 0.0, "geochemistry": 0.0, "climate": 1.0})
    return res["breakdown"]["climate_match"]
